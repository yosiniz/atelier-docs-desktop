from pathlib import Path
import tempfile
import os

APP_NAME = "Atelier Docs"
MAX_UPLOAD_BYTES = 250 * 1024 * 1024
WORKSPACE_ROOT = Path(tempfile.gettempdir()) / "atelier-docs"
WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
API_TOKEN = os.environ.get("ATELIER_API_TOKEN", "")

ALLOWED_EXTENSIONS = {
    ".pdf", ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff",
    ".gif", ".docx", ".xlsx", ".pptx", ".txt", ".csv",
}
