from __future__ import annotations

import hashlib
import hmac
import json

from PIL import Image

from backend.app import config
from backend.app.integrations import whatsapp as whatsapp_api
from backend.app.services.whatsapp_service import WhatsAppBotService, convert_for_whatsapp, detect_action


def test_whatsapp_command_detection():
    assert detect_action("PDF'yi Word yap", ".pdf") == "pdf_to_docx"
    assert detect_action("jpg yap", ".png") == "image_to_jpg"
    assert detect_action("Bunu PDF yap", ".docx") == "office_to_pdf"
    assert detect_action("pdf sıkıştır", ".pdf") == "compress_pdf"


def test_whatsapp_image_conversion_creates_real_jpeg(tmp_path):
    source = tmp_path / "seffaf.png"
    Image.new("RGBA", (24, 16), (20, 80, 120, 100)).save(source)
    results = convert_for_whatsapp(source, source.name, "JPG yap", tmp_path / "output")
    assert len(results) == 1
    assert results[0].filename == "seffaf.jpg"
    assert results[0].mime_type == "image/jpeg"
    with Image.open(results[0].path) as converted:
        assert converted.format == "JPEG"
        assert converted.size == (24, 16)


def test_whatsapp_pdf_to_word_uses_existing_conversion_engine(tmp_path, sample_pdf):
    results = convert_for_whatsapp(sample_pdf, "ornek.pdf", "word yap", tmp_path / "output")
    assert results[0].path.suffix == ".docx"
    assert results[0].path.read_bytes().startswith(b"PK")


def test_whatsapp_webhook_verification(client, monkeypatch):
    monkeypatch.setattr(config, "WHATSAPP_VERIFY_TOKEN", "dogrulama-tokeni")
    response = client.get("/api/integrations/whatsapp/webhook", params={
        "hub.mode": "subscribe",
        "hub.verify_token": "dogrulama-tokeni",
        "hub.challenge": "123456",
    })
    assert response.status_code == 200
    assert response.text == "123456"

    denied = client.get("/api/integrations/whatsapp/webhook", params={
        "hub.mode": "subscribe", "hub.verify_token": "yanlis", "hub.challenge": "1",
    })
    assert denied.status_code == 403


def test_whatsapp_webhook_requires_valid_meta_signature(client, monkeypatch):
    secret = "uygulama-sirri"
    monkeypatch.setattr(config, "WHATSAPP_APP_SECRET", secret)
    received = []
    monkeypatch.setattr(whatsapp_api.whatsapp_bot, "handle_webhook", received.append)
    payload = {"object": "whatsapp_business_account", "entry": []}
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    signature = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    response = client.post(
        "/api/integrations/whatsapp/webhook", content=body,
        headers={"Content-Type": "application/json", "X-Hub-Signature-256": signature},
    )
    assert response.status_code == 200
    assert received == [payload]

    rejected = client.post(
        "/api/integrations/whatsapp/webhook", content=body,
        headers={"Content-Type": "application/json", "X-Hub-Signature-256": "sha256=bad"},
    )
    assert rejected.status_code == 401


def test_whatsapp_file_then_command_are_joined_in_one_session(monkeypatch):
    class FakeClient:
        pass

    service = WhatsAppBotService(FakeClient())
    scheduled = []
    notifications = []
    monkeypatch.setattr(service, "_schedule", lambda sender, media, command: scheduled.append((sender, media, command)))
    monkeypatch.setattr(service, "_notify", lambda sender, text, reply: notifications.append((sender, text, reply)))

    service._handle_message({
        "from": "905551112233", "id": "wamid.file", "type": "document",
        "document": {"id": "media-1", "filename": "ornek.pdf", "mime_type": "application/pdf"},
    })
    service._handle_message({
        "from": "905551112233", "id": "wamid.command", "type": "text",
        "text": {"body": "Word yap"},
    })

    assert notifications and "Dosyayı aldım" in notifications[0][1]
    assert len(scheduled) == 1
    assert scheduled[0][0] == "905551112233"
    assert scheduled[0][1].filename == "ornek.pdf"
    assert scheduled[0][2] == "Word yap"
    service.executor.shutdown(wait=False)
