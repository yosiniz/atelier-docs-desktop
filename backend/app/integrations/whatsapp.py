from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from .. import config
from ..services.whatsapp_service import verify_webhook_signature, whatsapp_bot

router = APIRouter(prefix="/api/integrations/whatsapp", tags=["WhatsApp"])


@router.get("/webhook", response_class=PlainTextResponse)
def verify_webhook(
    mode: str | None = Query(None, alias="hub.mode"),
    verify_token: str | None = Query(None, alias="hub.verify_token"),
    challenge: str | None = Query(None, alias="hub.challenge"),
) -> str:
    if not config.WHATSAPP_VERIFY_TOKEN:
        raise HTTPException(status_code=503, detail="WhatsApp entegrasyonu yapılandırılmadı")
    if mode != "subscribe" or not verify_token or not __import__("hmac").compare_digest(
        verify_token, config.WHATSAPP_VERIFY_TOKEN
    ):
        raise HTTPException(status_code=403, detail="Webhook doğrulaması başarısız")
    return challenge or ""


@router.post("/webhook")
async def receive_webhook(request: Request) -> dict:
    body = await request.body()
    if not verify_webhook_signature(body, request.headers.get("X-Hub-Signature-256"), config.WHATSAPP_APP_SECRET):
        raise HTTPException(status_code=401, detail="Geçersiz webhook imzası")
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Geçersiz webhook gövdesi") from exc
    whatsapp_bot.handle_webhook(payload)
    return {"ok": True}


@router.get("/status")
def whatsapp_status() -> dict:
    return {
        "ok": True,
        "data": {
            "configured": whatsapp_bot.configured(),
            "allowed_numbers_restricted": bool(config.WHATSAPP_ALLOWED_NUMBERS),
            "graph_version": config.WHATSAPP_GRAPH_VERSION,
        },
    }
