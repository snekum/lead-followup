"""Meta WhatsApp webhook: GET verification + POST events (statuses + inbound)."""
from __future__ import annotations

import hashlib
import hmac
import json
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from sqlalchemy.orm import Session

from app.assistant.agent import respond_to_inbound
from app.config import get_settings
from app.db.session import get_db
from app.providers.llm.base import LLMClient
from app.providers.llm.factory import get_llm_client
from app.providers.whatsapp.base import WhatsAppProvider
from app.providers.whatsapp.factory import get_whatsapp_provider
from app.services.inbound import handle_inbound
from app.services.messages import update_message_status

router = APIRouter(prefix="/webhook", tags=["webhook"])


@router.get("/whatsapp")
def verify(request: Request) -> Response:
    params = request.query_params
    settings = get_settings()
    if (
        params.get("hub.mode") == "subscribe"
        and params.get("hub.verify_token") == settings.meta_verify_token
    ):
        return PlainTextResponse(params.get("hub.challenge", ""))
    return PlainTextResponse("verification failed", status_code=403)


def _signature_ok(secret: str, raw: bytes, header: str | None) -> bool:
    if not secret:
        return True  # dev mode: no app secret configured
    if not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header.split("=", 1)[1])


@router.post("/whatsapp")
async def receive(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    whatsapp: Annotated[WhatsAppProvider, Depends(get_whatsapp_provider)],
    llm: Annotated[LLMClient, Depends(get_llm_client)],
) -> Response:
    raw = await request.body()
    settings = get_settings()
    if not _signature_ok(
        settings.meta_app_secret, raw, request.headers.get("X-Hub-Signature-256")
    ):
        return PlainTextResponse("invalid signature", status_code=403)

    payload = json.loads(raw or b"{}")
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for status in value.get("statuses", []):
                update_message_status(
                    db,
                    provider_message_id=status.get("id"),
                    status=status.get("status", ""),
                )
            for message in value.get("messages", []):
                if message.get("type") == "text":
                    body = message.get("text", {}).get("body", "")
                else:
                    body = f"[{message.get('type', 'unknown')}]"
                lead = handle_inbound(
                    db,
                    phone=message.get("from", ""),
                    text=body,
                    provider_message_id=message.get("id"),
                )
                if (
                    lead is not None
                    and not lead.opt_out
                    and get_settings().assistant_enabled
                ):
                    respond_to_inbound(db, lead, whatsapp=whatsapp, llm=llm)
            db.commit()
    return JSONResponse({"status": "received"})
