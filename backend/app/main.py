from __future__ import annotations

import io
import json
import shutil
import zipfile
from contextlib import asynccontextmanager
from pathlib import Path

import fitz
from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, StreamingResponse
from PIL import Image

from .config import API_TOKEN, APP_NAME
from .models import (
    AddTextRequest, BlankPageRequest, CompressRequest, CropPageRequest, DeletePagesRequest, EncryptRequest,
    InkRequest, LinkRequest, MetadataRequest, MoveImageRequest, OcrRequest, OfficeSaveRequest, PageDecorationRequest, RedactRequest, ReorderPagesRequest, RotateRequest, ShapeRequest, WatermarkRemoveRequest, WatermarkRequest,
    SearchReplaceRequest, SplitRequest, TextEditRequest, UnlockRequest,
)
from .services.image_service import compress_to_target, convert_image, edit_image
from .services.conversion_service import docx_to_pdf, images_to_pdf, pdf_to_docx, pdf_to_images, pdf_to_pptx, pdf_to_xlsx
from .services.office_service import inspect_office, presentation_to_pdf, save_office, spreadsheet_to_pdf
from .services.ocr_service import ocr_engine_status, ocr_images_to_pdf, ocr_pdf
from .jobs import jobs
from .services.pdf_service import (
    compress_pdf,
    crop_page,
    add_blank_page,
    decorate_pages,
    add_image,
    add_shape,
    add_ink,
    add_link,
    add_watermark,
    add_text,
    delete_pages,
    edit_text,
    encrypt_pdf,
    inspect_pdf,
    image_elements,
    merge_pdfs,
    move_image,
    render_page,
    replace_text,
    redact_areas,
    reorder_pages,
    rotate_pages,
    split_pdf,
    search_text,
    text_blocks,
    unlock_pdf,
    update_metadata,
    remove_watermarks,
)
from .storage import cleanup_stale_workspaces, current_document_path, document_dir, operation_history, record_operation, restore_revision, save_upload, snapshot_revision
from .integrations.whatsapp import router as whatsapp_router
from .services.whatsapp_service import whatsapp_bot


@asynccontextmanager
async def lifespan(_app: FastAPI):
    cleanup_stale_workspaces()
    yield


app = FastAPI(title=APP_NAME, version="0.3.0", docs_url="/api/docs", lifespan=lifespan)
app.include_router(whatsapp_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173", "null"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.middleware("http")
async def local_api_token(request: Request, call_next):
    public_paths = {"/api/health", "/api/integrations/whatsapp/webhook"}
    if API_TOKEN and request.method != "OPTIONS" and request.url.path not in public_paths:
        supplied = request.headers.get("X-Atelier-Token") or request.query_params.get("api_token")
        if not supplied or not __import__("hmac").compare_digest(supplied, API_TOKEN):
            return Response(content='{"detail":"Yerel API erişimi reddedildi"}', status_code=401,
                            media_type="application/json")
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


def fail(status: int, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail=message)


def verify_file(path: Path) -> str:
    try:
        if path.suffix.lower() == ".pdf":
            with fitz.open(path) as document:
                if not document.is_pdf:
                    raise ValueError("PDF imzası doğrulanamadı")
                if not document.needs_pass and document.page_count < 1:
                    raise ValueError("PDF görüntülenebilir sayfa içermiyor")
            return "pdf"
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff", ".gif"}:
            with Image.open(path) as image:
                image.verify()
            return "image"
        if path.suffix.lower() in {".docx", ".xlsx", ".pptx"}:
            required = {
                ".docx": "word/document.xml",
                ".xlsx": "xl/workbook.xml",
                ".pptx": "ppt/presentation.xml",
            }[path.suffix.lower()]
            if not zipfile.is_zipfile(path):
                raise ValueError("Office Open XML paketi doğrulanamadı")
            with zipfile.ZipFile(path) as package:
                entries = package.infolist()
                if len(entries) > 20_000 or sum(item.file_size for item in entries) > 1024 * 1024 * 1024:
                    raise ValueError("Office paketi güvenli açma sınırlarını aşıyor")
                if required not in package.namelist():
                    raise ValueError("Dosya uzantısı ile Office içeriği eşleşmiyor")
            return "office"
        if path.suffix.lower() in {".txt", ".csv"}:
            path.read_text(encoding="utf-8", errors="strict")
            return "office"
        return "office"
    except Exception as exc:
        raise fail(422, f"Dosya içeriği doğrulanamadı: {exc}") from exc


def get_path(document_id: str) -> Path:
    try:
        return current_document_path(document_id)
    except (ValueError, FileNotFoundError) as exc:
        raise fail(404, str(exc)) from exc


@app.get("/api/health")
def health() -> dict:
    return {
        "ok": True,
        "app": APP_NAME,
        "capabilities": {
            "pdf": True,
            "images": True,
            "ocr": ocr_engine_status(),
            "office_conversion": shutil.which("soffice") is not None,
            "whatsapp": whatsapp_bot.configured(),
        },
    }


@app.head("/api/health")
def health_head() -> Response:
    return Response(status_code=200)


@app.post("/api/files")
async def upload_file(file: UploadFile = File(...)) -> dict:
    try:
        document_id, path, original_name, size = await save_upload(file)
        kind = verify_file(path)
        data = {"id": document_id, "name": original_name, "size": size, "kind": kind}
        if kind == "pdf":
            data["pdf"] = inspect_pdf(path)
        elif kind == "image":
            with Image.open(path) as image:
                data["image"] = {"width": image.width, "height": image.height, "format": image.format}
        return {"ok": True, "data": data}
    except HTTPException:
        raise
    except ValueError as exc:
        raise fail(400, str(exc)) from exc


@app.get("/api/files/{document_id}/download")
def download_file(document_id: str) -> FileResponse:
    path = get_path(document_id)
    media_type = "application/pdf" if path.suffix.lower() == ".pdf" else "application/octet-stream"
    return FileResponse(path, media_type=media_type, filename=f"atelier-output{path.suffix}")


@app.get("/api/files/{document_id}/history")
def file_history(document_id: str) -> dict:
    try:
        get_path(document_id)
        return {"ok": True, "data": operation_history(document_id)}
    except ValueError as exc:
        raise fail(404, str(exc)) from exc


@app.get("/api/pdf/{document_id}")
def pdf_info(document_id: str) -> dict:
    return {"ok": True, "data": inspect_pdf(get_path(document_id))}


@app.get("/api/pdf/{document_id}/pages/{page_index}/render")
def pdf_render(document_id: str, page_index: int, scale: float = Query(1.5, ge=0.5, le=4)) -> Response:
    try:
        return Response(render_page(get_path(document_id), page_index, scale), media_type="image/png")
    except IndexError as exc:
        raise fail(404, str(exc)) from exc


@app.get("/api/pdf/{document_id}/pages/{page_index}/text")
def pdf_text(document_id: str, page_index: int) -> dict:
    try:
        return {"ok": True, "data": text_blocks(get_path(document_id), page_index)}
    except IndexError as exc:
        raise fail(404, "Sayfa bulunamadı") from exc


@app.get("/api/pdf/{document_id}/pages/{page_index}/images")
def pdf_images(document_id: str, page_index: int) -> dict:
    try:
        return {"ok": True, "data": image_elements(get_path(document_id), page_index)}
    except IndexError as exc:
        raise fail(404, "Sayfa bulunamadı") from exc


@app.get("/api/pdf/{document_id}/search")
def pdf_search(document_id: str, query: str = Query(min_length=1, max_length=500),
               case_sensitive: bool = False, whole_word: bool = False) -> dict:
    try:
        matches = search_text(get_path(document_id), query, case_sensitive, whole_word)
        return {"ok": True, "data": {"matches": matches, "count": len(matches)}}
    except ValueError as exc:
        raise fail(400, str(exc)) from exc


@app.post("/api/pdf/{document_id}/replace-text")
def pdf_replace_text(document_id: str, request: SearchReplaceRequest) -> dict:
    source = get_path(document_id)
    folder = document_dir(document_id)
    staged = folder / "replace.next.pdf"
    current = folder / "current.pdf"
    try:
        audit = replace_text(source, staged, request)
        inspect_pdf(staged)
        snapshot_revision(document_id)
        staged.replace(current)
        record_operation(document_id, "Bul ve değiştir", {"count": audit["matches"]})
        return {"ok": True, "data": {"audit": audit, "pdf": inspect_pdf(current)}}
    except (ValueError, IndexError, RuntimeError) as exc:
        staged.unlink(missing_ok=True)
        raise fail(400, str(exc)) from exc


@app.post("/api/pdf/{document_id}/edit-text")
def pdf_edit_text(document_id: str, request: TextEditRequest) -> dict:
    source = get_path(document_id)
    folder = document_dir(document_id)
    staged = folder / "edited.next.pdf"
    current = folder / "current.pdf"
    try:
        audit = edit_text(source, staged, request)
        inspect_pdf(staged)
        snapshot_revision(document_id)
        staged.replace(current)
        record_operation(document_id, "Metin düzenlendi")
        return {"ok": True, "data": {"audit": audit, "pdf": inspect_pdf(current)}}
    except (ValueError, IndexError) as exc:
        staged.unlink(missing_ok=True)
        raise fail(400, str(exc)) from exc


@app.post("/api/pdf/{document_id}/rotate")
def pdf_rotate(document_id: str, request: RotateRequest) -> dict:
    source = get_path(document_id)
    staged = document_dir(document_id) / "rotated.next.pdf"
    current = document_dir(document_id) / "current.pdf"
    try:
        rotate_pages(source, staged, request.pages, request.angle)
        snapshot_revision(document_id)
        staged.replace(current)
        record_operation(document_id, "Sayfa döndürüldü", {"pages": request.pages})
        return {"ok": True, "data": inspect_pdf(current)}
    except (ValueError, IndexError) as exc:
        staged.unlink(missing_ok=True)
        raise fail(400, str(exc)) from exc


@app.post("/api/pdf/{document_id}/compress")
def pdf_compress(document_id: str, request: CompressRequest) -> dict:
    source = get_path(document_id)
    staged = document_dir(document_id) / "compressed.next.pdf"
    current = document_dir(document_id) / "current.pdf"
    try:
        metrics = compress_pdf(source, staged, request.level)
        snapshot_revision(document_id)
        staged.replace(current)
        record_operation(document_id, "PDF sıkıştırıldı", {"level": request.level, "ratio": metrics["ratio"]})
        return {"ok": True, "data": metrics}
    except ValueError as exc:
        staged.unlink(missing_ok=True)
        raise fail(400, str(exc)) from exc


@app.post("/api/jobs/pdf/{document_id}/compress")
def queue_pdf_compress(document_id: str, request: CompressRequest) -> dict:
    source = get_path(document_id)
    folder = document_dir(document_id)
    staged = folder / f"job-{__import__('uuid').uuid4().hex}.pdf"
    current = folder / "current.pdf"

    def work(cancel_event, progress):
        progress(10)
        metrics = compress_pdf(source, staged, request.level)
        progress(85)
        if cancel_event.is_set():
            staged.unlink(missing_ok=True)
            return {}
        inspect_pdf(staged)
        snapshot_revision(document_id)
        staged.replace(current)
        record_operation(document_id, "PDF sıkıştırıldı", {"level": request.level, "ratio": metrics["ratio"]})
        progress(100)
        return metrics

    return {"ok": True, "data": jobs.submit("pdf-compress", document_id, work)}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    try:
        return {"ok": True, "data": jobs.get(job_id)}
    except KeyError as exc:
        raise fail(404, str(exc)) from exc


@app.post("/api/jobs/{job_id}/cancel")
def cancel_job(job_id: str) -> dict:
    try:
        return {"ok": True, "data": jobs.cancel(job_id)}
    except KeyError as exc:
        raise fail(404, str(exc)) from exc


def _commit_pdf_operation(document_id: str, operation, *args) -> dict:
    source = get_path(document_id)
    folder = document_dir(document_id)
    staged = folder / "pages.next.pdf"
    current = folder / "current.pdf"
    try:
        operation(source, staged, *args)
        result = inspect_pdf(staged)
        snapshot_revision(document_id)
        staged.replace(current)
        record_operation(document_id, operation.__name__)
        return {"ok": True, "data": result}
    except (ValueError, IndexError) as exc:
        staged.unlink(missing_ok=True)
        raise fail(400, str(exc)) from exc


@app.post("/api/pdf/{document_id}/pages/delete")
def pdf_delete_pages(document_id: str, request: DeletePagesRequest) -> dict:
    return _commit_pdf_operation(document_id, delete_pages, request.pages)


@app.post("/api/pdf/{document_id}/pages/reorder")
def pdf_reorder_pages(document_id: str, request: ReorderPagesRequest) -> dict:
    return _commit_pdf_operation(document_id, reorder_pages, request.order)


@app.post("/api/pdf/{document_id}/pages/crop")
def pdf_crop_page(document_id: str, request: CropPageRequest) -> dict:
    return _commit_pdf_operation(document_id, crop_page, request.page, request.rect)


@app.post("/api/pdf/{document_id}/pages/blank")
def pdf_add_blank_page(document_id: str, request: BlankPageRequest) -> dict:
    return _commit_pdf_operation(document_id, add_blank_page, request)


@app.post("/api/pdf/{document_id}/pages/decorate")
def pdf_decorate_pages(document_id: str, request: PageDecorationRequest) -> dict:
    return _commit_pdf_operation(document_id, decorate_pages, request)


@app.post("/api/pdf/{document_id}/content/text")
def pdf_add_text(document_id: str, request: AddTextRequest) -> dict:
    return _commit_pdf_operation(document_id, add_text, request)


@app.post("/api/pdf/{document_id}/content/shape")
def pdf_add_shape(document_id: str, request: ShapeRequest) -> dict:
    return _commit_pdf_operation(document_id, add_shape, request)


@app.post("/api/pdf/{document_id}/content/ink")
def pdf_add_ink(document_id: str, request: InkRequest) -> dict:
    return _commit_pdf_operation(document_id, add_ink, request)


@app.post("/api/pdf/{document_id}/content/image/move")
def pdf_move_image(document_id: str, request: MoveImageRequest) -> dict:
    return _commit_pdf_operation(
        document_id, move_image, request.page, request.xref, request.source_rect, request.target_rect,
    )


@app.post("/api/pdf/{document_id}/ocr")
def pdf_ocr(document_id: str, request: OcrRequest) -> dict:
    source = get_path(document_id)
    folder = document_dir(document_id)
    staged = folder / "ocr.next.pdf"
    current = folder / "current.pdf"
    try:
        audit = ocr_pdf(source, staged, request.language, request.dpi, request.force)
        result = inspect_pdf(staged)
        snapshot_revision(document_id)
        staged.replace(current)
        record_operation(document_id, "OCR uygulandı", {"language": audit["language"], "confidence": audit["average_confidence"]})
        return {"ok": True, "data": {"pdf": result, "audit": audit}}
    except RuntimeError as exc:
        staged.unlink(missing_ok=True)
        raise fail(503, str(exc)) from exc
    except (ValueError, IndexError) as exc:
        staged.unlink(missing_ok=True)
        raise fail(400, str(exc)) from exc


@app.post("/api/pdf/{document_id}/content/watermark")
def pdf_add_watermark(document_id: str, request: WatermarkRequest) -> dict:
    return _commit_pdf_operation(document_id, add_watermark, request)


@app.post("/api/pdf/{document_id}/content/watermark/remove")
def pdf_remove_watermark(document_id: str, request: WatermarkRemoveRequest) -> dict:
    return _commit_pdf_operation(document_id, remove_watermarks, request.pages)


@app.post("/api/pdf/{document_id}/content/link")
def pdf_add_link(document_id: str, request: LinkRequest) -> dict:
    return _commit_pdf_operation(document_id, add_link, request)


@app.post("/api/pdf/{document_id}/content/redact")
def pdf_redact(document_id: str, request: RedactRequest) -> dict:
    source = get_path(document_id)
    folder = document_dir(document_id)
    staged = folder / "redacted.next.pdf"
    current = folder / "current.pdf"
    try:
        audit = redact_areas(source, staged, request.page, request.rects)
        result = inspect_pdf(staged)
        snapshot_revision(document_id)
        staged.replace(current)
        record_operation(document_id, "Kalıcı redaksiyon", {"areas": audit["areas"]})
        return {"ok": True, "data": {"pdf": result, "audit": audit}}
    except (ValueError, IndexError) as exc:
        staged.unlink(missing_ok=True)
        raise fail(400, str(exc)) from exc


@app.post("/api/pdf/{document_id}/content/image")
async def pdf_add_image(
    document_id: str,
    page: int = Form(...),
    rect: str = Form(...),
    file: UploadFile = File(...),
) -> dict:
    source = get_path(document_id)
    staged = document_dir(document_id) / "image.next.pdf"
    current = document_dir(document_id) / "current.pdf"
    image_path: Path | None = None
    try:
        _image_id, image_path, _name, _size = await save_upload(file)
        if verify_file(image_path) != "image":
            raise ValueError("Yalnızca desteklenen görsel dosyaları eklenebilir")
        rect_values = tuple(float(value) for value in json.loads(rect))
        if len(rect_values) != 4:
            raise ValueError("Görsel alanı dört koordinat içermelidir")
        add_image(source, staged, page, rect_values, image_path)
        result = inspect_pdf(staged)
        snapshot_revision(document_id)
        staged.replace(current)
        record_operation(document_id, "Görsel eklendi")
        return {"ok": True, "data": result}
    except (ValueError, TypeError, IndexError, json.JSONDecodeError) as exc:
        staged.unlink(missing_ok=True)
        raise fail(400, str(exc)) from exc
    finally:
        if image_path is not None:
            shutil.rmtree(image_path.parent, ignore_errors=True)


@app.post("/api/pdf/{document_id}/undo")
def pdf_undo(document_id: str) -> dict:
    try:
        path = restore_revision(document_id, "undo")
        record_operation(document_id, "Geri al")
        return {"ok": True, "data": inspect_pdf(path)}
    except ValueError as exc:
        raise fail(409, str(exc)) from exc


@app.post("/api/pdf/{document_id}/redo")
def pdf_redo(document_id: str) -> dict:
    try:
        path = restore_revision(document_id, "redo")
        record_operation(document_id, "İleri al")
        return {"ok": True, "data": inspect_pdf(path)}
    except ValueError as exc:
        raise fail(409, str(exc)) from exc


@app.post("/api/pdf/{document_id}/security/encrypt")
def pdf_encrypt(document_id: str, request: EncryptRequest) -> FileResponse:
    source = get_path(document_id)
    output = document_dir(document_id) / "protected.pdf"
    try:
        encrypt_pdf(source, output, request)
        return FileResponse(output, media_type="application/pdf", filename="sifreli.pdf")
    except ValueError as exc:
        output.unlink(missing_ok=True)
        raise fail(400, str(exc)) from exc


@app.post("/api/pdf/{document_id}/security/unlock")
def pdf_unlock(document_id: str, request: UnlockRequest) -> dict:
    source = get_path(document_id)
    staged = document_dir(document_id) / "unlocked.next.pdf"
    current = document_dir(document_id) / "current.pdf"
    try:
        unlock_pdf(source, staged, request.password)
        result = inspect_pdf(staged)
        staged.replace(current)
        return {"ok": True, "data": result}
    except ValueError as exc:
        staged.unlink(missing_ok=True)
        raise fail(400, str(exc)) from exc


@app.post("/api/pdf/{document_id}/metadata")
def pdf_update_metadata(document_id: str, request: MetadataRequest) -> dict:
    return _commit_pdf_operation(document_id, update_metadata, request)


@app.post("/api/pdf/{document_id}/split")
def pdf_split(document_id: str, request: SplitRequest) -> StreamingResponse:
    try:
        parts = split_pdf(get_path(document_id), request.ranges)
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
            for name, content in parts:
                bundle.writestr(name, content)
        archive.seek(0)
        return StreamingResponse(archive, media_type="application/zip", headers={
            "Content-Disposition": 'attachment; filename="atelier-bolunmus.zip"'
        })
    except ValueError as exc:
        raise fail(400, str(exc)) from exc


@app.post("/api/pdf/merge")
async def pdf_merge(files: list[UploadFile] = File(...)) -> StreamingResponse:
    if len(files) < 2:
        raise fail(400, "Birleştirme için en az iki PDF seçin")
    saved: list[Path] = []
    try:
        for upload in files:
            _id, path, _name, _size = await save_upload(upload)
            if verify_file(path) != "pdf":
                raise fail(422, "Birleştirme yalnızca PDF dosyalarını kabul eder")
            saved.append(path)
        output = saved[0].parent / "merged.pdf"
        merge_pdfs(saved, output)
        return StreamingResponse(output.open("rb"), media_type="application/pdf", headers={
            "Content-Disposition": 'attachment; filename="birlestirilmis.pdf"'
        })
    except ValueError as exc:
        raise fail(400, str(exc)) from exc


@app.post("/api/images/{document_id}/convert")
def image_convert(
    document_id: str,
    output_format: str = Form(...),
    quality: int = Form(86),
    background: str = Form("#ffffff"),
    max_width: int | None = Form(None),
    max_height: int | None = Form(None),
) -> Response:
    try:
        content, metadata = convert_image(get_path(document_id), output_format, quality, background, max_width, max_height)
        media = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}[output_format.upper()]
        return Response(content, media_type=media, headers={
            "X-Atelier-Metadata": json.dumps(metadata),
            "Content-Disposition": f'attachment; filename="donusturulen.{output_format.lower().replace("jpeg", "jpg")}"',
        })
    except ValueError as exc:
        raise fail(400, str(exc)) from exc


@app.post("/api/images/{document_id}/edit")
def image_edit(
    document_id: str,
    brightness: float = Form(1), contrast: float = Form(1), saturation: float = Form(1),
    grayscale: bool = Form(False), sepia: bool = Form(False), blur: float = Form(0), sharpen: float = Form(0),
    rotate: int = Form(0), flip: str = Form("none"), crop_x: int = Form(0), crop_y: int = Form(0),
    crop_width: int | None = Form(None), crop_height: int | None = Form(None),
) -> Response:
    try:
        content = edit_image(get_path(document_id), brightness=brightness, contrast=contrast,
                             saturation=saturation, grayscale=grayscale, sepia=sepia, blur=blur,
                             sharpen=sharpen, rotate=rotate, flip=flip, crop_x=crop_x, crop_y=crop_y,
                             crop_width=crop_width, crop_height=crop_height)
        return Response(content, media_type="image/png", headers={
            "Content-Disposition": 'attachment; filename="duzenlenen.png"'
        })
    except ValueError as exc:
        raise fail(400, str(exc)) from exc


@app.post("/api/images/{document_id}/compress")
def image_compress(
    document_id: str,
    target_kb: int = Form(...),
    output_format: str = Form("JPEG"),
    max_width: int | None = Form(None),
    max_height: int | None = Form(None),
) -> Response:
    try:
        content, metadata = compress_to_target(get_path(document_id), target_kb, output_format, max_width, max_height)
        extension = "jpg" if output_format.upper() == "JPEG" else "webp"
        return Response(content, media_type=f"image/{extension}", headers={
            "X-Atelier-Metadata": json.dumps(metadata),
            "Content-Disposition": f'attachment; filename="sikistirilan.{extension}"',
        })
    except ValueError as exc:
        raise fail(400, str(exc)) from exc


@app.post("/api/batch/images/convert")
async def image_batch_convert(
    files: list[UploadFile] = File(...), output_format: str = Form("JPEG"),
    quality: int = Form(86), background: str = Form("#ffffff"),
    max_width: int | None = Form(None), max_height: int | None = Form(None),
) -> Response:
    if not files:
        raise fail(400, "En az bir görsel seçin")
    saved: list[tuple[Path, str]] = []
    try:
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
            for upload in files:
                _id, path, name, _size = await save_upload(upload)
                saved.append((path, name))
                if verify_file(path) != "image":
                    raise ValueError("Toplu işlem yalnızca görsel dosyalarını kabul eder")
                content, _metadata = convert_image(path, output_format, quality, background, max_width, max_height)
                extension = output_format.lower().replace("jpeg", "jpg")
                bundle.writestr(f"{Path(name).stem}.{extension}", content)
        return Response(archive.getvalue(), media_type="application/zip", headers={
            "Content-Disposition": 'attachment; filename="toplu-gorseller.zip"'
        })
    except ValueError as exc:
        raise fail(400, str(exc)) from exc
    finally:
        for path, _name in saved:
            shutil.rmtree(path.parent, ignore_errors=True)


@app.post("/api/batch/images/compress")
async def image_batch_compress(
    files: list[UploadFile] = File(...), target_kb: int = Form(...),
    output_format: str = Form("JPEG"),
) -> Response:
    if not files:
        raise fail(400, "En az bir görsel seçin")
    saved: list[tuple[Path, str]] = []
    try:
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
            for upload in files:
                _id, path, name, _size = await save_upload(upload)
                saved.append((path, name))
                if verify_file(path) != "image":
                    raise ValueError("Toplu işlem yalnızca görsel dosyalarını kabul eder")
                content, _metadata = compress_to_target(path, target_kb, output_format)
                extension = "jpg" if output_format.upper() == "JPEG" else "webp"
                bundle.writestr(f"{Path(name).stem}.{extension}", content)
        return Response(archive.getvalue(), media_type="application/zip", headers={
            "Content-Disposition": 'attachment; filename="toplu-sikistirilmis.zip"'
        })
    except ValueError as exc:
        raise fail(400, str(exc)) from exc
    finally:
        for path, _name in saved:
            shutil.rmtree(path.parent, ignore_errors=True)


@app.post("/api/batch/pdf/compress")
async def pdf_batch_compress(files: list[UploadFile] = File(...), level: str = Form("balanced")) -> Response:
    if not files or level not in {"quality", "balanced", "small"}:
        raise fail(400, "Dosya veya sıkıştırma seviyesi geçersiz")
    saved: list[tuple[Path, str]] = []
    try:
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
            for upload in files:
                _id, path, name, _size = await save_upload(upload)
                saved.append((path, name))
                if verify_file(path) != "pdf":
                    raise ValueError("Toplu işlem yalnızca PDF dosyalarını kabul eder")
                output = path.parent / "batch-output.pdf"
                compress_pdf(path, output, level)
                bundle.writestr(f"{Path(name).stem}-sikistirilmis.pdf", output.read_bytes())
        return Response(archive.getvalue(), media_type="application/zip", headers={
            "Content-Disposition": 'attachment; filename="toplu-pdf.zip"'
        })
    except ValueError as exc:
        raise fail(400, str(exc)) from exc
    finally:
        for path, _name in saved:
            shutil.rmtree(path.parent, ignore_errors=True)


@app.get("/api/convert/pdf/{document_id}/docx")
def convert_pdf_docx(document_id: str) -> FileResponse:
    source = get_path(document_id)
    output = document_dir(document_id) / "converted.docx"
    try:
        metadata = pdf_to_docx(source, output)
        return FileResponse(output, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            filename="donusturulen.docx", headers={"X-Atelier-Mode": metadata["mode"]})
    except ValueError as exc:
        raise fail(400, str(exc)) from exc


@app.get("/api/convert/pdf/{document_id}/xlsx")
def convert_pdf_xlsx(document_id: str) -> FileResponse:
    output = document_dir(document_id) / "converted.xlsx"
    try:
        metadata = pdf_to_xlsx(get_path(document_id), output)
        return FileResponse(output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            filename="donusturulen.xlsx", headers={"X-Atelier-Mode": metadata["mode"]})
    except ValueError as exc:
        raise fail(400, str(exc)) from exc


@app.get("/api/convert/pdf/{document_id}/pptx")
def convert_pdf_pptx(document_id: str) -> FileResponse:
    output = document_dir(document_id) / "converted.pptx"
    try:
        metadata = pdf_to_pptx(get_path(document_id), output)
        return FileResponse(output, media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                            filename="donusturulen.pptx", headers={"X-Atelier-Mode": metadata["mode"]})
    except ValueError as exc:
        raise fail(400, str(exc)) from exc


@app.get("/api/convert/pdf/{document_id}/images")
def convert_pdf_images(
    document_id: str,
    output_format: str = Query("png"),
    dpi: int = Query(144, ge=72, le=360),
    quality: int = Query(88, ge=30, le=100),
) -> Response:
    try:
        content = pdf_to_images(get_path(document_id), output_format, dpi, quality)
        return Response(content, media_type="application/zip", headers={
            "Content-Disposition": 'attachment; filename="pdf-sayfalari.zip"'
        })
    except ValueError as exc:
        raise fail(400, str(exc)) from exc


@app.get("/api/convert/docx/{document_id}/pdf")
def convert_docx_pdf(document_id: str) -> FileResponse:
    source = get_path(document_id)
    if source.suffix.lower() != ".docx":
        raise fail(400, "Bu işlem DOCX dosyası gerektirir")
    output = document_dir(document_id) / "converted.pdf"
    try:
        metadata = docx_to_pdf(source, output)
        return FileResponse(output, media_type="application/pdf", filename="donusturulen.pdf",
                            headers={"X-Atelier-Mode": metadata["mode"]})
    except ValueError as exc:
        raise fail(400, str(exc)) from exc


@app.get("/api/office/{document_id}")
def office_info(document_id: str) -> dict:
    try:
        return {"ok": True, "data": inspect_office(get_path(document_id))}
    except (ValueError, IndexError, KeyError) as exc:
        raise fail(400, str(exc)) from exc


@app.post("/api/office/{document_id}")
def office_save(document_id: str, request: OfficeSaveRequest) -> dict:
    source = get_path(document_id)
    suffix = source.suffix.lower()
    if suffix not in {".docx", ".xlsx", ".csv", ".pptx"}:
        raise fail(400, "Desteklenmeyen Office dosyası")
    folder = document_dir(document_id)
    staged = folder / f"office.next{suffix}"
    current = folder / f"current{suffix}"
    try:
        save_office(source, staged, request.updates)
        verify_file(staged)
        staged.replace(current)
        return {"ok": True, "data": inspect_office(current)}
    except (ValueError, IndexError, KeyError, TypeError) as exc:
        staged.unlink(missing_ok=True)
        raise fail(400, str(exc)) from exc


@app.get("/api/convert/office/{document_id}/pdf")
def convert_office_pdf(document_id: str) -> FileResponse:
    source = get_path(document_id)
    output = document_dir(document_id) / "office-converted.pdf"
    try:
        if source.suffix.lower() == ".docx":
            metadata = docx_to_pdf(source, output)
        elif source.suffix.lower() in {".xlsx", ".csv"}:
            metadata = spreadsheet_to_pdf(source, output)
        elif source.suffix.lower() == ".pptx":
            metadata = presentation_to_pdf(source, output)
        else:
            raise ValueError("Bu dosya PDF'e dönüştürülemez")
        return FileResponse(output, media_type="application/pdf", filename="office.pdf",
                            headers={"X-Atelier-Mode": metadata["mode"]})
    except ValueError as exc:
        raise fail(400, str(exc)) from exc


@app.post("/api/convert/images/pdf")
async def convert_images_pdf(files: list[UploadFile] = File(...)) -> FileResponse:
    if not files:
        raise fail(400, "En az bir görsel seçin")
    saved: list[Path] = []
    try:
        for upload in files:
            _id, path, _name, _size = await save_upload(upload)
            if verify_file(path) != "image":
                raise fail(422, "Yalnızca desteklenen görseller kabul edilir")
            saved.append(path)
        output = saved[0].parent / "images.pdf"
        images_to_pdf(saved, output)
        return FileResponse(output, media_type="application/pdf", filename="gorseller.pdf")
    except ValueError as exc:
        raise fail(400, str(exc)) from exc


@app.post("/api/ocr/images/pdf")
async def convert_scans_to_searchable_pdf(
    files: list[UploadFile] = File(...),
    language: str = Form(default="tur+eng", pattern=r"^[a-z]{3}(\+[a-z]{3})*$"),
    dpi: int = Form(default=200, ge=120, le=300),
) -> FileResponse:
    """Turn scanner images (including multi-page TIFF) into a searchable local PDF."""
    if not files:
        raise fail(400, "En az bir tarama görseli seçin")
    saved: list[Path] = []
    try:
        for upload in files:
            _id, path, _name, _size = await save_upload(upload)
            if verify_file(path) != "image":
                raise fail(422, "Yalnızca desteklenen tarama görselleri kabul edilir")
            saved.append(path)
        output = saved[0].parent / "ocr-searchable.pdf"
        audit = ocr_images_to_pdf(saved, output, language, dpi)
        return FileResponse(
            output,
            media_type="application/pdf",
            filename="aranabilir-tarama.pdf",
            headers={
                "X-Atelier-OCR-Words": str(audit["word_count"]),
                "X-Atelier-OCR-Confidence": str(audit["average_confidence"]),
            },
        )
    except RuntimeError as exc:
        raise fail(503, str(exc)) from exc
    except ValueError as exc:
        raise fail(400, str(exc)) from exc
