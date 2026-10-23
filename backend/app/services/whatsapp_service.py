from __future__ import annotations

import hashlib
import hmac
import io
import json
import logging
import mimetypes
import re
import shutil
import tempfile
import threading
import time
import unicodedata
import zipfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import pymupdf
from PIL import Image

from .. import config
from ..storage import safe_filename
from .conversion_service import docx_to_pdf, images_to_pdf, pdf_to_docx, pdf_to_images
from .image_service import convert_image
from .office_service import presentation_to_pdf, spreadsheet_to_pdf
from .pdf_service import compress_pdf

logger = logging.getLogger(__name__)
WHATSAPP_TEMP_ROOT = Path(tempfile.gettempdir()) / "atelier-docs-whatsapp"
WHATSAPP_TEMP_ROOT.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class PendingMedia:
    media_id: str
    filename: str
    mime_type: str
    message_id: str
    received_at: float


@dataclass(frozen=True)
class ConversionResult:
    path: Path
    filename: str
    mime_type: str
    message_type: str = "document"


def _plain(value: str) -> str:
    lowered = value.casefold().replace("ı", "i")
    return "".join(character for character in unicodedata.normalize("NFKD", lowered)
                   if not unicodedata.combining(character))


def detect_action(command: str, suffix: str) -> str:
    text = _plain(command)
    suffix = suffix.lower()
    if any(word in text for word in ("sikistir", "compress")):
        if suffix == ".pdf":
            return "compress_pdf"
        raise ValueError("Sıkıştırma komutu şu anda WhatsApp üzerinden PDF dosyalarında kullanılabilir.")
    if any(word in text for word in ("word", "docx")):
        if suffix == ".pdf":
            return "pdf_to_docx"
        raise ValueError("Word dönüşümü için bir PDF gönderin.")
    if "xlsx" in text or "excel" in text:
        raise ValueError("WhatsApp botunda Excel çıktısı henüz etkin değil.")
    if "pptx" in text or "powerpoint" in text:
        raise ValueError("WhatsApp botunda PowerPoint çıktısı henüz etkin değil.")
    if re.search(r"\b(jpg|jpeg)\b", text):
        if suffix == ".pdf":
            return "pdf_to_jpg"
        return "image_to_jpg"
    if re.search(r"\bpng\b", text):
        if suffix == ".pdf":
            return "pdf_to_png"
        return "image_to_png"
    if re.search(r"\bwebp\b", text):
        return "image_to_webp"
    if re.search(r"\bpdf\b", text):
        if suffix in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff", ".gif"}:
            return "image_to_pdf"
        if suffix in {".docx", ".xlsx", ".csv", ".pptx"}:
            return "office_to_pdf"
        raise ValueError("Bu dosya türü PDF'e dönüştürülemiyor.")
    raise ValueError("Komutu anlayamadım. Örnek: “Word yap”, “JPG yap”, “PDF yap” veya “PDF sıkıştır”.")


def convert_for_whatsapp(source: Path, original_name: str, command: str, output_dir: Path) -> list[ConversionResult]:
    validate_source(source)
    action = detect_action(command, source.suffix)
    stem = safe_filename(Path(original_name).stem) or "atelier-belge"
    output_dir.mkdir(parents=True, exist_ok=True)

    if action == "pdf_to_docx":
        output = output_dir / f"{stem}.docx"
        pdf_to_docx(source, output)
        return [ConversionResult(output, output.name,
                                 "application/vnd.openxmlformats-officedocument.wordprocessingml.document")]
    if action == "compress_pdf":
        output = output_dir / f"{stem}-sikistirilmis.pdf"
        compress_pdf(source, output, "balanced")
        return [ConversionResult(output, output.name, "application/pdf")]
    if action in {"pdf_to_png", "pdf_to_jpg"}:
        extension = "png" if action.endswith("png") else "jpg"
        archive = pdf_to_images(source, extension, 144, 88)
        results: list[ConversionResult] = []
        with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
            for index, entry in enumerate(bundle.infolist(), start=1):
                if entry.is_dir():
                    continue
                output = output_dir / f"{stem}-sayfa-{index}.{extension}"
                output.write_bytes(bundle.read(entry))
                mime_type = "image/png" if extension == "png" else "image/jpeg"
                results.append(ConversionResult(output, output.name, mime_type, "image"))
        if not results:
            raise ValueError("PDF içinde dönüştürülebilir sayfa bulunamadı.")
        return results
    if action.startswith("image_to_"):
        target = action.removeprefix("image_to_")
        if target == "pdf":
            output = output_dir / f"{stem}.pdf"
            images_to_pdf([source], output)
            return [ConversionResult(output, output.name, "application/pdf")]
        format_name = {"jpg": "JPEG", "png": "PNG", "webp": "WEBP"}[target]
        extension = "jpg" if target == "jpg" else target
        content, _metadata = convert_image(source, format_name)
        output = output_dir / f"{stem}.{extension}"
        output.write_bytes(content)
        mime_type = {"jpg": "image/jpeg", "png": "image/png", "webp": "image/webp"}[target]
        return [ConversionResult(output, output.name, mime_type, "image")]
    if action == "office_to_pdf":
        output = output_dir / f"{stem}.pdf"
        suffix = source.suffix.lower()
        if suffix == ".docx":
            docx_to_pdf(source, output)
        elif suffix in {".xlsx", ".csv"}:
            spreadsheet_to_pdf(source, output)
        elif suffix == ".pptx":
            presentation_to_pdf(source, output)
        else:
            raise ValueError("Desteklenmeyen Office dosyası.")
        return [ConversionResult(output, output.name, "application/pdf")]
    raise ValueError("Desteklenmeyen dönüşüm komutu.")


def validate_source(path: Path) -> None:
    suffix = path.suffix.lower()
    if suffix not in config.ALLOWED_EXTENSIONS:
        raise ValueError("Bu dosya türü desteklenmiyor.")
    if suffix == ".pdf":
        with pymupdf.open(path) as document:
            if not document.is_pdf or (not document.needs_pass and document.page_count < 1):
                raise ValueError("Geçerli bir PDF bulunamadı.")
        return
    if suffix in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff", ".gif"}:
        with Image.open(path) as image:
            image.verify()
        return
    if suffix in {".docx", ".xlsx", ".pptx"}:
        required = {
            ".docx": "word/document.xml", ".xlsx": "xl/workbook.xml", ".pptx": "ppt/presentation.xml",
        }[suffix]
        if not zipfile.is_zipfile(path):
            raise ValueError("Office dosyası doğrulanamadı.")
        with zipfile.ZipFile(path) as package:
            entries = package.infolist()
            if len(entries) > 20_000 or sum(item.file_size for item in entries) > 1024 * 1024 * 1024:
                raise ValueError("Office dosyası güvenli açma sınırlarını aşıyor.")
            if required not in package.namelist():
                raise ValueError("Dosya uzantısı ile Office içeriği eşleşmiyor.")
        return
    if suffix in {".txt", ".csv"}:
        path.read_text(encoding="utf-8", errors="strict")
        return
    raise ValueError("Bu dosya türü desteklenmiyor.")


def verify_webhook_signature(body: bytes, signature: str | None, app_secret: str) -> bool:
    if not app_secret or not signature or not signature.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature.removeprefix("sha256="), expected)


class WhatsAppCloudClient:
    def __init__(self, transport: httpx.BaseTransport | None = None):
        self._client = httpx.Client(timeout=httpx.Timeout(90.0, connect=15.0), transport=transport)

    @property
    def graph_root(self) -> str:
        return f"https://graph.facebook.com/{config.WHATSAPP_GRAPH_VERSION}"

    @property
    def headers(self) -> dict[str, str]:
        if not config.WHATSAPP_ACCESS_TOKEN:
            raise RuntimeError("WHATSAPP_ACCESS_TOKEN yapılandırılmadı")
        return {"Authorization": f"Bearer {config.WHATSAPP_ACCESS_TOKEN}"}

    def _raise(self, response: httpx.Response) -> None:
        if response.is_success:
            return
        try:
            detail = response.json().get("error", {}).get("message", "Meta API hatası")
        except (ValueError, AttributeError):
            detail = "Meta API hatası"
        raise RuntimeError(f"WhatsApp API isteği başarısız: {detail}")

    def download_media(self, media: PendingMedia, folder: Path) -> Path:
        metadata_response = self._client.get(f"{self.graph_root}/{media.media_id}", headers=self.headers)
        self._raise(metadata_response)
        metadata = metadata_response.json()
        declared_size = int(metadata.get("file_size") or 0)
        if declared_size > config.WHATSAPP_MAX_DOWNLOAD_BYTES:
            raise ValueError("Dosya izin verilen WhatsApp indirme sınırını aşıyor.")
        download_response = self._client.get(metadata["url"], headers=self.headers)
        self._raise(download_response)
        content = download_response.content
        if len(content) > config.WHATSAPP_MAX_DOWNLOAD_BYTES:
            raise ValueError("Dosya izin verilen WhatsApp indirme sınırını aşıyor.")
        expected_hash = metadata.get("sha256")
        if expected_hash and not hmac.compare_digest(hashlib.sha256(content).hexdigest(), expected_hash):
            raise ValueError("WhatsApp dosya bütünlüğü doğrulanamadı.")
        filename = safe_filename(media.filename)
        if not Path(filename).suffix:
            filename += mimetypes.guess_extension(media.mime_type) or ".bin"
        target = folder / filename
        target.write_bytes(content)
        return target

    def send_text(self, recipient: str, text: str, reply_to: str | None = None) -> None:
        payload: dict[str, Any] = {
            "messaging_product": "whatsapp", "to": recipient, "type": "text",
            "text": {"body": text[:4096]},
        }
        if reply_to:
            payload["context"] = {"message_id": reply_to}
        self._send_message(payload)

    def send_file(self, recipient: str, result: ConversionResult, reply_to: str | None = None) -> None:
        if not config.WHATSAPP_PHONE_NUMBER_ID:
            raise RuntimeError("WHATSAPP_PHONE_NUMBER_ID yapılandırılmadı")
        limit = config.WHATSAPP_MAX_IMAGE_BYTES if result.message_type == "image" else config.WHATSAPP_MAX_DOCUMENT_BYTES
        if result.path.stat().st_size > limit:
            raise ValueError("Oluşturulan dosya WhatsApp gönderim boyutu sınırını aşıyor.")
        with result.path.open("rb") as stream:
            upload = self._client.post(
                f"{self.graph_root}/{config.WHATSAPP_PHONE_NUMBER_ID}/media",
                headers=self.headers,
                data={"messaging_product": "whatsapp", "type": result.mime_type},
                files={"file": (result.filename, stream, result.mime_type)},
            )
        self._raise(upload)
        media_id = upload.json()["id"]
        media_payload: dict[str, Any] = {"id": media_id}
        if result.message_type == "document":
            media_payload["filename"] = result.filename
        payload: dict[str, Any] = {
            "messaging_product": "whatsapp", "to": recipient, "type": result.message_type,
            result.message_type: media_payload,
        }
        if reply_to:
            payload["context"] = {"message_id": reply_to}
        self._send_message(payload)

    def _send_message(self, payload: dict[str, Any]) -> None:
        if not config.WHATSAPP_PHONE_NUMBER_ID:
            raise RuntimeError("WHATSAPP_PHONE_NUMBER_ID yapılandırılmadı")
        response = self._client.post(
            f"{self.graph_root}/{config.WHATSAPP_PHONE_NUMBER_ID}/messages",
            headers={**self.headers, "Content-Type": "application/json"}, json=payload,
        )
        self._raise(response)


class WhatsAppBotService:
    def __init__(self, client: WhatsAppCloudClient | None = None):
        self.client = client or WhatsAppCloudClient()
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="atelier-whatsapp")
        self._lock = threading.Lock()
        self._pending_media: dict[str, PendingMedia] = {}
        self._pending_commands: dict[str, tuple[str, float, str]] = {}
        self._seen_messages: dict[str, float] = {}
        self.session_seconds = 30 * 60

    def configured(self) -> bool:
        return all((config.WHATSAPP_ACCESS_TOKEN, config.WHATSAPP_PHONE_NUMBER_ID,
                    config.WHATSAPP_VERIFY_TOKEN, config.WHATSAPP_APP_SECRET))

    def _allowed(self, sender: str) -> bool:
        return not config.WHATSAPP_ALLOWED_NUMBERS or sender in config.WHATSAPP_ALLOWED_NUMBERS

    def _remember_once(self, message_id: str) -> bool:
        now = time.time()
        with self._lock:
            self._seen_messages = {key: seen for key, seen in self._seen_messages.items()
                                   if now - seen < self.session_seconds}
            if message_id in self._seen_messages:
                return False
            self._seen_messages[message_id] = now
            return True

    def handle_webhook(self, payload: dict[str, Any]) -> None:
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                for message in value.get("messages", []):
                    self._handle_message(message)

    def _handle_message(self, message: dict[str, Any]) -> None:
        sender = str(message.get("from", ""))
        message_id = str(message.get("id", ""))
        if not sender or not message_id or not self._remember_once(message_id):
            return
        if not self._allowed(sender):
            logger.warning("İzin verilmeyen WhatsApp göndericisi reddedildi")
            return
        message_type = message.get("type")
        now = time.time()
        if message_type in {"document", "image"}:
            data = message.get(message_type, {})
            media_id = str(data.get("id", ""))
            mime_type = str(data.get("mime_type", "application/octet-stream"))
            filename = str(data.get("filename") or f"whatsapp{mimetypes.guess_extension(mime_type) or '.bin'}")
            caption = str(data.get("caption", "")).strip()
            media = PendingMedia(media_id, filename, mime_type, message_id, now)
            with self._lock:
                pending_command = self._pending_commands.pop(sender, None)
                if not caption and not pending_command:
                    self._pending_media[sender] = media
            command = caption or (pending_command[0] if pending_command and now - pending_command[1] < self.session_seconds else "")
            if command:
                self._schedule(sender, media, command)
            else:
                self._notify(sender, "Dosyayı aldım. Şimdi “Word yap”, “JPG yap”, “PDF yap” veya “PDF sıkıştır” yazın.", message_id)
            return
        if message_type == "text":
            command = str(message.get("text", {}).get("body", "")).strip()
            if not command:
                return
            with self._lock:
                media = self._pending_media.pop(sender, None)
                if media and now - media.received_at >= self.session_seconds:
                    media = None
                if media is None:
                    self._pending_commands[sender] = (command, now, message_id)
            if media:
                self._schedule(sender, media, command)
            else:
                self._notify(sender, "Komutu aldım. Şimdi dönüştürülecek dosyayı gönderin.", message_id)

    def _schedule(self, sender: str, media: PendingMedia, command: str) -> None:
        self.executor.submit(self._process, sender, media, command)

    def _notify(self, sender: str, text: str, reply_to: str) -> None:
        self.executor.submit(self._send_text_safely, sender, text, reply_to)

    def _send_text_safely(self, sender: str, text: str, reply_to: str) -> None:
        try:
            self.client.send_text(sender, text, reply_to)
        except Exception:
            logger.exception("WhatsApp durum mesajı gönderilemedi")

    def _process(self, sender: str, media: PendingMedia, command: str) -> None:
        folder = Path(tempfile.mkdtemp(prefix="job-", dir=WHATSAPP_TEMP_ROOT))
        try:
            self.client.send_text(sender, "Dosyanız işleniyor…", media.message_id)
            source = self.client.download_media(media, folder)
            results = convert_for_whatsapp(source, media.filename, command, folder / "output")
            for result in results:
                self.client.send_file(sender, result, media.message_id)
            self.client.send_text(sender, f"Tamamlandı. {len(results)} dosya gönderildi.", media.message_id)
        except Exception as exc:
            logger.exception("WhatsApp belge işlemi başarısız")
            try:
                public_message = str(exc) if isinstance(exc, ValueError) else "Teknik bir hata oluştu. Lütfen tekrar deneyin."
                self.client.send_text(sender, f"İşlem tamamlanamadı: {public_message}", media.message_id)
            except Exception:
                logger.exception("WhatsApp hata bildirimi gönderilemedi")
        finally:
            shutil.rmtree(folder, ignore_errors=True)


whatsapp_bot = WhatsAppBotService()
