from pathlib import Path
import tempfile
import os

APP_NAME = "Atelier Docs"
MAX_UPLOAD_BYTES = 250 * 1024 * 1024
WORKSPACE_ROOT = Path(tempfile.gettempdir()) / "atelier-docs"
WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
API_TOKEN = os.environ.get("ATELIER_API_TOKEN", "")

WHATSAPP_ACCESS_TOKEN = os.environ.get("WHATSAPP_ACCESS_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")
WHATSAPP_VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN", "")
WHATSAPP_APP_SECRET = os.environ.get("WHATSAPP_APP_SECRET", "")
WHATSAPP_GRAPH_VERSION = os.environ.get("WHATSAPP_GRAPH_VERSION", "v24.0")
WHATSAPP_ALLOWED_NUMBERS = {
    number.strip() for number in os.environ.get("WHATSAPP_ALLOWED_NUMBERS", "").split(",") if number.strip()
}
WHATSAPP_MAX_DOWNLOAD_BYTES = int(os.environ.get("WHATSAPP_MAX_DOWNLOAD_BYTES", str(100 * 1024 * 1024)))
WHATSAPP_MAX_IMAGE_BYTES = int(os.environ.get("WHATSAPP_MAX_IMAGE_BYTES", str(5 * 1024 * 1024)))
WHATSAPP_MAX_DOCUMENT_BYTES = int(os.environ.get("WHATSAPP_MAX_DOCUMENT_BYTES", str(100 * 1024 * 1024)))

ALLOWED_EXTENSIONS = {
    ".pdf", ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff",
    ".gif", ".docx", ".xlsx", ".pptx", ".txt", ".csv",
}
