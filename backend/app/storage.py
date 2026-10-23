from __future__ import annotations

import hashlib
import json
import re
import shutil
import uuid
import time
from pathlib import Path
from fastapi import UploadFile

from .config import ALLOWED_EXTENSIONS, MAX_UPLOAD_BYTES, WORKSPACE_ROOT

SAFE_NAME = re.compile(r"[^\w.\-() ]+", re.UNICODE)


def safe_filename(name: str) -> str:
    clean = SAFE_NAME.sub("_", Path(name).name).strip(" .")
    return clean[:160] or "dosya"


def document_dir(document_id: str) -> Path:
    if not re.fullmatch(r"[0-9a-f]{32}", document_id):
        raise ValueError("Geçersiz belge kimliği")
    target = (WORKSPACE_ROOT / document_id).resolve()
    if WORKSPACE_ROOT.resolve() not in target.parents:
        raise ValueError("Geçersiz belge yolu")
    return target


def document_path(document_id: str) -> Path:
    folder = document_dir(document_id)
    matches = [item for item in folder.iterdir() if item.name.startswith("source")]
    if not matches:
        raise FileNotFoundError("Belge bulunamadı")
    return matches[0]


def current_document_path(document_id: str) -> Path:
    folder = document_dir(document_id)
    current = sorted(folder.glob("current.*"))
    return current[0] if current else document_path(document_id)


def _stack_dir(document_id: str, stack: str) -> Path:
    if stack not in {"undo", "redo"}:
        raise ValueError("Geçersiz revizyon yığını")
    target = document_dir(document_id) / "history" / stack
    target.mkdir(parents=True, exist_ok=True)
    return target


def snapshot_revision(document_id: str, stack: str = "undo", clear_redo: bool = True) -> Path:
    source = current_document_path(document_id)
    target_dir = _stack_dir(document_id, stack)
    target = target_dir / f"{time.time_ns()}-{uuid.uuid4().hex}.pdf"
    shutil.copy2(source, target)
    if clear_redo and stack == "undo":
        redo_dir = _stack_dir(document_id, "redo")
        for item in redo_dir.glob("*.pdf"):
            item.unlink(missing_ok=True)
    return target


def restore_revision(document_id: str, source_stack: str) -> Path:
    source_dir = _stack_dir(document_id, source_stack)
    revisions = sorted(source_dir.glob("*.pdf"), key=lambda item: item.name)
    if not revisions:
        raise ValueError("Geri alınabilecek revizyon bulunmuyor" if source_stack == "undo" else "İleri alınabilecek revizyon bulunmuyor")
    opposite = "redo" if source_stack == "undo" else "undo"
    snapshot_revision(document_id, opposite, clear_redo=False)
    revision = revisions[-1]
    current = document_dir(document_id) / "current.pdf"
    shutil.copy2(revision, current)
    revision.unlink(missing_ok=True)
    return current


def cleanup_stale_workspaces(max_age_seconds: int = 72 * 60 * 60) -> int:
    """Remove only old, UUID-named Atelier workspaces from the configured temp root."""
    cutoff = time.time() - max_age_seconds
    root = WORKSPACE_ROOT.resolve()
    removed = 0
    for folder in WORKSPACE_ROOT.iterdir():
        if not folder.is_dir() or not re.fullmatch(r"[0-9a-f]{32}", folder.name):
            continue
        target = folder.resolve()
        if root not in target.parents or folder.stat().st_mtime >= cutoff:
            continue
        shutil.rmtree(target, ignore_errors=False)
        removed += 1
    return removed


def record_operation(document_id: str, operation: str, details: dict | None = None) -> None:
    path = document_dir(document_id) / "operations.json"
    try:
        entries = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    except (ValueError, OSError):
        entries = []
    entries.append({"operation": operation, "timestamp": time.time(), "details": details or {}})
    path.write_text(json.dumps(entries[-100:], ensure_ascii=False), encoding="utf-8")


def operation_history(document_id: str) -> list[dict]:
    path = document_dir(document_id) / "operations.json"
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))[-100:]
    except (ValueError, OSError):
        return []


async def save_upload(upload: UploadFile) -> tuple[str, Path, str, int]:
    original_name = safe_filename(upload.filename or "dosya")
    extension = Path(original_name).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Desteklenmeyen dosya türü: {extension or 'bilinmiyor'}")

    document_id = uuid.uuid4().hex
    folder = WORKSPACE_ROOT / document_id
    folder.mkdir(parents=True, exist_ok=False)
    target = folder / f"source{extension}"
    digest = hashlib.sha256()
    total = 0
    try:
        with target.open("wb") as handle:
            while chunk := await upload.read(1024 * 1024):
                total += len(chunk)
                if total > MAX_UPLOAD_BYTES:
                    raise ValueError("Dosya boyutu yapılandırılmış 250 MB sınırını aşıyor")
                digest.update(chunk)
                handle.write(chunk)
    except Exception:
        shutil.rmtree(folder, ignore_errors=True)
        raise
    return document_id, target, original_name, total
