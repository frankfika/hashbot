"""x402 Payment data structures and types."""

from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class PaymentStatus(StrEnum):
    """x402 payment lifecycle states."""

    PAYMENT_REQUIRED = "payment-required"
    PAYMENT_SUBMITTED = "payment-submitted"
    PAYMENT_VERIFIED = "payment-verified"
    PAYMENT_COMPLETED = "payment-completed"
    PAYMENT_REJECTED = "payment-rejected"
    PAYMENT_FAILED = "payment-failed"


class PaymentScheme(StrEnum):
    """Supported payment schemes."""

    EXACT = "exact"  # Exact amount payment
    STREAMING = "streaming"  # Pay-per-use streaming


class PaymentRequirements(BaseModel):
    """x402 payment requirements structure."""

    # Payment scheme
    scheme: PaymentScheme = PaymentScheme.EXACT
    scheme_data: dict[str, Any] = Field(default_factory=dict)

    # Network info
    network: str  # e.g., "hashkey-mainnet", "hashkey-testnet"
    chain_id: int

    # Asset info
    asset: str  # Token contract address
    asset_symbol: str  # e.g., "HKDC"
    asset_decimals: int = 18

    # Payment details
    amount: str  # Amount in base units (wei)
    amount_display: str  # Human readable amount
    recipient: str  # Recipient wallet address

    # Payment metadata
    nonce: str = Field(default_factory=lambda: str(uuid4()))
    expires_at: datetime | None = None
    description: str = ""

    # Extra data
    extra: dict[str, Any] = Field(default_factory=dict)


class PaymentPayload(BaseModel):
    """Signed payment authorization from client."""

    version: str = "1"
    network: str
    scheme: PaymentScheme

    # The signed payload (EIP-712 or similar)
    payload: str  # Hex-encoded signed data

    # Metadata
    nonce: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PaymentReceipt(BaseModel):
    """On-chain settlement receipt."""

    success: bool
    transaction_hash: str | None = None
    network: str
    chain_id: int
    payer: str
    recipient: str
    amount: str
    asset: str
    block_number: int | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    error: str | None = None


class X402PaymentRequiredResponse(BaseModel):
    """x402 Payment Required response structure."""

    x402_version: str = Field(default="0.1", alias="x402Version")
    accepts: list[PaymentRequirements]

    model_config = {"populate_by_name": True}


class X402SettleResponse(BaseModel):
    """x402 Settlement response structure."""

    success: bool
    receipt: PaymentReceipt | None = None
    error: str | None = None


class PaymentConfig(BaseModel):
    """Configuration for payment requirements."""

    price: Decimal
    currency: str = "HKDC"
    description: str = ""
    network: str = "hashkey-testnet"
    chain_id: int = 177
    recipient: str = ""
    asset_address: str = ""
    asset_decimals: int = 18

    def to_requirements(self) -> PaymentRequirements:
        """Convert config to payment requirements."""
        # Convert price to base units
        amount_base = int(self.price * Decimal(10) ** self.asset_decimals)

        return PaymentRequirements(
            network=self.network,
            chain_id=self.chain_id,
            asset=self.asset_address,
            asset_symbol=self.currency,
            asset_decimals=self.asset_decimals,
            amount=str(amount_base),
            amount_display=f"{self.price} {self.currency}",
            recipient=self.recipient,
            description=self.description,
        )
