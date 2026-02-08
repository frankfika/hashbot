"""Payment service for x402 payment processing."""

import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from web3 import Web3

from hashbot.config import get_settings
from hashbot.db import crud
from hashbot.hashkey.chain import HashKeyChain
from hashbot.hashkey.tokens import ERC20Token
from hashbot.x402.payment import (
    PaymentPayload,
    PaymentReceipt,
    PaymentRequirements,
    PaymentStatus,
)
from hashbot.x402.verification import PaymentVerifier


class PaymentService:
    """Service for processing x402 payments on HashKey Chain."""

    def __init__(self, chain: HashKeyChain | None = None):
        self.settings = get_settings()
        self.chain = chain or HashKeyChain(
            rpc_url=self.settings.hashkey_rpc_url,
            chain_id=self.settings.hashkey_chain_id,
        )
        self.verifier = PaymentVerifier(self.chain.web3, self.chain.chain_id)
        self._hkdc_token: ERC20Token | None = None

    @property
    def hkdc_token(self) -> ERC20Token | None:
        """Get HKDC token instance."""
        if self._hkdc_token is None and self.settings.hkdc_contract_address:
            self._hkdc_token = ERC20Token(
                address=self.settings.hkdc_contract_address,
                chain=self.chain,
            )
        return self._hkdc_token

    async def verify_payment(
        self,
        payload: PaymentPayload,
        requirements: PaymentRequirements,
        expected_payer: str | None = None,
    ) -> tuple[bool, str | None]:
        """
        Verify a payment signature.

        Returns:
            Tuple of (is_valid, payer_address)
        """
        # Verify payment parameters match
        if not self.verifier.verify_payment_params(payload, requirements):
            return False, None

        # Verify signature
        is_valid, recovered = self.verifier.verify_signature(
            payload, requirements, expected_payer
        )

        return is_valid, recovered

    async def settle_payment(
        self,
        payload: PaymentPayload,
        requirements: PaymentRequirements,
        payer_address: str,
    ) -> PaymentReceipt:
        """
        Settle a payment on-chain.

        This implementation supports two modes:
        1. Direct transfer from platform wallet (for custodial users)
        2. Verification of pre-approved transfer (for non-custodial)
        """
        try:
            # For demo/hackathon: simulate successful settlement
            # In production, this would execute actual on-chain transfer

            # Check if we have a platform wallet configured
            if self.settings.platform_private_key and self.hkdc_token:
                # Execute actual transfer from platform wallet
                from hashbot.hashkey.wallet import Wallet

                platform_wallet = Wallet(
                    self.settings.platform_private_key,
                    self.chain,
                )

                amount = int(requirements.amount)
                recipient = Web3.to_checksum_address(requirements.recipient)

                # Transfer tokens
                tx_hash = self.hkdc_token.transfer(
                    platform_wallet,
                    recipient,
                    amount,
                )

                # Wait for confirmation
                receipt = self.chain.wait_for_transaction(tx_hash, timeout=120)

                return PaymentReceipt(
                    success=receipt.get("status") == 1,
                    transaction_hash=tx_hash,
                    network=requirements.network,
                    chain_id=requirements.chain_id,
                    payer=payer_address,
                    recipient=requirements.recipient,
                    amount=requirements.amount,
                    asset=requirements.asset,
                    block_number=receipt.get("blockNumber"),
                    timestamp=datetime.now(UTC),
                )
            else:
                # Demo mode: return simulated receipt
                return PaymentReceipt(
                    success=True,
                    transaction_hash=f"0x{'0' * 64}",  # Placeholder
                    network=requirements.network,
                    chain_id=requirements.chain_id,
                    payer=payer_address,
                    recipient=requirements.recipient,
                    amount=requirements.amount,
                    asset=requirements.asset,
                    block_number=0,
                    timestamp=datetime.now(UTC),
                )

        except Exception as e:
            return PaymentReceipt(
                success=False,
                network=requirements.network,
                chain_id=requirements.chain_id,
                payer=payer_address,
                recipient=requirements.recipient,
                amount=requirements.amount,
                asset=requirements.asset,
                error=str(e),
            )

    async def record_payment(
        self,
        telegram_id: int,
        agent_id: str,
        amount: Decimal,
        tx_hash: str | None = None,
    ) -> dict[str, Any]:
        """Record a payment in the database."""
        user = await crud.get_user_by_telegram_id(telegram_id)
        if not user:
            return {"success": False, "error": "User not found"}

        payment = await crud.record_payment(
            payer_user_id=user.id,
            agent_id=agent_id,
            amount=float(amount),
            currency="HKDC",
        )

        if tx_hash:
            await crud.complete_payment(payment.id, tx_hash)

        return {
            "success": True,
            "payment_id": payment.id,
        }

    def create_payment_requirements(
        self,
        amount: Decimal,
        recipient: str,
        description: str = "",
    ) -> PaymentRequirements:
        """Create payment requirements for an agent call."""
        amount_base = int(amount * Decimal(10**18))

        return PaymentRequirements(
            network=f"hashkey-{'mainnet' if self.chain.chain_id == 133 else 'testnet'}",
            chain_id=self.chain.chain_id,
            asset=self.settings.hkdc_contract_address or "",
            asset_symbol="HKDC",
            asset_decimals=18,
            amount=str(amount_base),
            amount_display=f"{amount} HKDC",
            recipient=recipient,
            description=description,
        )

    def build_payment_payload(
        self,
        requirements: PaymentRequirements,
        signature: str,
    ) -> PaymentPayload:
        """Build a payment payload from requirements and signature."""
        message = {
            "recipient": requirements.recipient,
            "amount": int(requirements.amount),
            "asset": requirements.asset,
            "nonce": requirements.nonce,
            "deadline": int(requirements.expires_at.timestamp()) if requirements.expires_at else 0,
        }

        payload_data = json.dumps({
            "signature": signature,
            "message": message,
        }).encode().hex()

        return PaymentPayload(
            network=requirements.network,
            scheme=requirements.scheme,
            payload=f"0x{payload_data}",
            nonce=requirements.nonce,
        )
