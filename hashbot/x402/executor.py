"""x402 Payment executor for automatic payment flow."""

from decimal import Decimal
from functools import wraps
from typing import Any, Callable, Awaitable, TypeVar

from hashbot.a2a.messages import Task, TaskState
from hashbot.x402.payment import (
    PaymentStatus,
    PaymentRequirements,
    PaymentPayload,
    PaymentConfig,
    X402PaymentRequiredResponse,
)

T = TypeVar("T")


class PaymentRequired(Exception):
    """Exception raised when payment is required."""

    def __init__(self, requirements: list[PaymentRequirements]):
        self.requirements = requirements
        super().__init__("Payment required")


class X402Executor:
    """Executor for x402 payment flow."""

    X402_METADATA_PREFIX = "x402.payment"

    def __init__(
        self,
        default_recipient: str,
        default_network: str = "hashkey-testnet",
        default_chain_id: int = 177,
        default_asset: str = "",
        verify_callback: Callable[[PaymentPayload], Awaitable[bool]] | None = None,
        settle_callback: Callable[
            [PaymentPayload, PaymentRequirements], Awaitable[dict[str, Any]]
        ]
        | None = None,
    ):
        self.default_recipient = default_recipient
        self.default_network = default_network
        self.default_chain_id = default_chain_id
        self.default_asset = default_asset
        self._verify_callback = verify_callback
        self._settle_callback = settle_callback

    def create_payment_config(
        self,
        price: Decimal | float | str,
        currency: str = "HKDC",
        description: str = "",
    ) -> PaymentConfig:
        """Create a payment configuration."""
        return PaymentConfig(
            price=Decimal(str(price)),
            currency=currency,
            description=description,
            network=self.default_network,
            chain_id=self.default_chain_id,
            recipient=self.default_recipient,
            asset_address=self.default_asset,
        )

    def get_payment_status(self, task: Task) -> PaymentStatus | None:
        """Get current payment status from task metadata."""
        status_str = task.metadata.get(f"{self.X402_METADATA_PREFIX}.status")
        if status_str:
            return PaymentStatus(status_str)
        return None

    def set_payment_status(self, task: Task, status: PaymentStatus) -> None:
        """Set payment status in task metadata."""
        task.metadata[f"{self.X402_METADATA_PREFIX}.status"] = status.value

    def get_payment_requirements(self, task: Task) -> PaymentRequirements | None:
        """Get payment requirements from task metadata."""
        req_data = task.metadata.get(f"{self.X402_METADATA_PREFIX}.required")
        if req_data:
            return PaymentRequirements.model_validate(req_data)
        return None

    def set_payment_requirements(
        self, task: Task, requirements: PaymentRequirements
    ) -> None:
        """Set payment requirements in task metadata."""
        task.metadata[f"{self.X402_METADATA_PREFIX}.required"] = requirements.model_dump()

    def get_payment_payload(self, task: Task) -> PaymentPayload | None:
        """Get payment payload from task metadata."""
        payload_data = task.metadata.get(f"{self.X402_METADATA_PREFIX}.payload")
        if payload_data:
            return PaymentPayload.model_validate(payload_data)
        return None

    def has_valid_payment(self, task: Task) -> bool:
        """Check if task has a valid payment."""
        status = self.get_payment_status(task)
        return status in (PaymentStatus.PAYMENT_VERIFIED, PaymentStatus.PAYMENT_COMPLETED)

    def create_payment_required_response(
        self,
        task: Task,
        config: PaymentConfig,
    ) -> dict[str, Any]:
        """Create a payment-required response for A2A."""
        requirements = config.to_requirements()

        # Store in task metadata
        self.set_payment_status(task, PaymentStatus.PAYMENT_REQUIRED)
        self.set_payment_requirements(task, requirements)

        task.status = TaskState.INPUT_REQUIRED

        return {
            "id": task.id,
            "sessionId": task.session_id,
            "status": {
                "state": TaskState.INPUT_REQUIRED.value,
                "message": {
                    "role": "agent",
                    "parts": [
                        {
                            "type": "data",
                            "data": X402PaymentRequiredResponse(
                                accepts=[requirements]
                            ).model_dump(by_alias=True),
                        }
                    ],
                },
            },
            "metadata": task.metadata,
        }

    async def process_payment(
        self,
        task: Task,
        payload: PaymentPayload,
    ) -> bool:
        """Process a submitted payment."""
        self.set_payment_status(task, PaymentStatus.PAYMENT_SUBMITTED)
        task.metadata[f"{self.X402_METADATA_PREFIX}.payload"] = payload.model_dump()

        # Verify signature
        if self._verify_callback:
            is_valid = await self._verify_callback(payload)
            if not is_valid:
                self.set_payment_status(task, PaymentStatus.PAYMENT_REJECTED)
                return False

        self.set_payment_status(task, PaymentStatus.PAYMENT_VERIFIED)

        # Settle on-chain
        if self._settle_callback:
            requirements = self.get_payment_requirements(task)
            if requirements:
                try:
                    receipt = await self._settle_callback(payload, requirements)
                    receipts = task.metadata.get(
                        f"{self.X402_METADATA_PREFIX}.receipts", []
                    )
                    receipts.append(receipt)
                    task.metadata[f"{self.X402_METADATA_PREFIX}.receipts"] = receipts
                    self.set_payment_status(task, PaymentStatus.PAYMENT_COMPLETED)
                except Exception as e:
                    self.set_payment_status(task, PaymentStatus.PAYMENT_FAILED)
                    task.metadata[f"{self.X402_METADATA_PREFIX}.error"] = str(e)
                    return False

        return True


def require_payment(
    price: Decimal | float | str,
    currency: str = "HKDC",
    description: str = "",
) -> Callable:
    """Decorator to require payment for a handler."""

    def decorator(
        func: Callable[[Task], Awaitable[dict[str, Any]]]
    ) -> Callable[[Task], Awaitable[dict[str, Any]]]:
        # Store payment config on function
        func._payment_config = {  # type: ignore
            "price": Decimal(str(price)),
            "currency": currency,
            "description": description,
        }

        @wraps(func)
        async def wrapper(task: Task) -> dict[str, Any]:
            # Check if already paid
            status = task.metadata.get("x402.payment.status")
            if status not in (
                PaymentStatus.PAYMENT_VERIFIED.value,
                PaymentStatus.PAYMENT_COMPLETED.value,
            ):
                # Raise PaymentRequired to signal payment flow
                raise PaymentRequired([])

            return await func(task)

        return wrapper

    return decorator
