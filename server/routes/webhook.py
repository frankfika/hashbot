"""Webhook endpoints for Telegram and other integrations."""

import logging

from fastapi import APIRouter, HTTPException, Request

from hashbot.config import get_settings

router = APIRouter()


@router.post("/telegram")
async def telegram_webhook(request: Request):
    """Handle Telegram webhook updates."""
    settings = get_settings()

    if not settings.telegram_bot_token:
        raise HTTPException(status_code=503, detail="Telegram not configured")

    try:
        await request.json()  # validate JSON body

        # In production, this would be handled by python-telegram-bot
        # For now, just acknowledge receipt
        return {"ok": True}

    except Exception:
        logging.exception("Telegram webhook error")
        raise HTTPException(status_code=400, detail="Invalid request")


@router.post("/x402/payment")
async def x402_payment_webhook(request: Request):
    """Handle x402 payment notifications."""
    try:
        data = await request.json()

        # Extract payment info
        task_id = data.get("taskId")
        payment_payload = data.get("payload")
        _ = data.get("status")  # reserved for future use

        if not task_id or not payment_payload:
            raise HTTPException(status_code=400, detail="Missing required fields")

        # Process payment
        # In production:
        # 1. Verify signature
        # 2. Settle on-chain
        # 3. Update task status

        return {
            "success": True,
            "taskId": task_id,
            "status": "payment-completed",
            "receipt": {
                "transactionHash": "0x...",
                "blockNumber": 12345,
            },
        }

    except HTTPException:
        raise
    except Exception:
        logging.exception("x402 payment webhook error")
        raise HTTPException(status_code=500, detail="Internal server error")
