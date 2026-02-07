"""Base agent class and decorators."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from decimal import Decimal
from typing import Any, TypeVar

from hashbot.a2a.messages import AgentCard, Skill, Task, TaskState
from hashbot.x402.payment import PaymentConfig

T = TypeVar("T", bound="BaseAgent")


def agent_card(
    name: str,
    description: str,
    price_per_call: float | Decimal | None = None,
    currency: str = "HKDC",
    skills: list[dict[str, Any]] | None = None,
    version: str = "1.0.0",
    **metadata: Any,
) -> Callable[[type[T]], type[T]]:
    """
    Decorator to define agent metadata.

    Usage:
        @agent_card(
            name="CryptoAnalyst",
            description="Professional crypto analysis",
            price_per_call=0.1,
            currency="HKDC"
        )
        class CryptoAnalystAgent(BaseAgent):
            ...
    """

    def decorator(cls: type[T]) -> type[T]:
        # Store metadata on class
        cls._agent_name = name
        cls._agent_description = description
        cls._price_per_call = Decimal(str(price_per_call)) if price_per_call else None
        cls._currency = currency
        cls._skills = skills or None
        cls._version = version
        cls._metadata = metadata or None

        return cls

    return decorator


class BaseAgent(ABC):
    """Base class for all HashBot agents."""

    # Class-level metadata (set by @agent_card decorator)
    _agent_name: str = "UnnamedAgent"
    _agent_description: str = ""
    _price_per_call: Decimal | None = None
    _currency: str = "HKDC"
    _skills: list[dict[str, Any]] | None = None
    _version: str = "1.0.0"
    _metadata: dict[str, Any] | None = None

    def __init__(self, base_url: str = ""):
        """Initialize agent."""
        self.base_url = base_url
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize agent resources. Override if needed."""
        self._initialized = True

    async def shutdown(self) -> None:
        """Cleanup agent resources. Override if needed."""
        self._initialized = False

    @property
    def name(self) -> str:
        """Get agent name."""
        return self._agent_name

    @property
    def description(self) -> str:
        """Get agent description."""
        return self._agent_description

    @property
    def price(self) -> Decimal | None:
        """Get price per call."""
        return self._price_per_call

    @property
    def currency(self) -> str:
        """Get payment currency."""
        return self._currency

    @property
    def requires_payment(self) -> bool:
        """Check if agent requires payment."""
        return self._price_per_call is not None and self._price_per_call > 0

    def get_payment_config(self) -> PaymentConfig | None:
        """Get payment configuration if required."""
        if not self.requires_payment:
            return None

        return PaymentConfig(
            price=self._price_per_call,
            currency=self._currency,
            description=f"Payment for {self.name}",
        )

    def get_agent_card(self) -> AgentCard:
        """Build A2A Agent Card."""
        skills = [
            Skill(
                id=s.get("id", "default"),
                name=s.get("name", self.name),
                description=s.get("description", self.description),
                tags=s.get("tags", []),
            )
            for s in (self._skills or [])
        ]

        # Add default skill if none defined
        if not skills:
            skills = [
                Skill(
                    id="default",
                    name=self.name,
                    description=self.description,
                )
            ]

        return AgentCard(
            name=self.name,
            description=self.description,
            url=self.base_url,
            version=self._version,
            skills=skills,
            x402_enabled=self.requires_payment,
            metadata={
                **(self._metadata or {}),
                "price_per_call": str(self._price_per_call) if self._price_per_call else None,
                "currency": self._currency,
            },
        )

    @abstractmethod
    async def process(self, task: Task) -> dict[str, Any]:
        """
        Process an incoming task.

        This is the main entry point for agent logic.
        Override this method to implement agent behavior.

        Args:
            task: The A2A task to process

        Returns:
            A2A response dictionary
        """
        pass

    async def handle_task(self, task: Task) -> dict[str, Any]:
        """
        Handle a task with payment check.

        This wraps process() with payment verification.
        """
        # Check if payment is required and verified
        if self.requires_payment:
            payment_status = task.metadata.get("x402.payment.status")

            if payment_status not in ("payment-verified", "payment-completed"):
                # Return payment required response
                return self._create_payment_required_response(task)

        # Process the task
        try:
            result = await self.process(task)
            return result
        except Exception as e:
            return self._create_error_response(task, str(e))

    def _create_payment_required_response(self, task: Task) -> dict[str, Any]:
        """Create x402 payment required response."""
        config = self.get_payment_config()

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
                            "type": "text",
                            "text": f"Payment required: {config.price} {config.currency}",
                        },
                        {
                            "type": "data",
                            "data": {
                                "x402Version": "0.1",
                                "accepts": [config.to_requirements().model_dump()],
                            },
                        },
                    ],
                },
            },
            "metadata": task.metadata,
        }

    def _create_error_response(self, task: Task, error: str) -> dict[str, Any]:
        """Create error response."""
        task.status = TaskState.FAILED

        return {
            "id": task.id,
            "sessionId": task.session_id,
            "status": {
                "state": TaskState.FAILED.value,
                "message": {
                    "role": "agent",
                    "parts": [{"type": "text", "text": f"Error: {error}"}],
                },
            },
            "metadata": task.metadata,
        }

    def _create_success_response(
        self,
        task: Task,
        text: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create success response."""
        task.status = TaskState.COMPLETED

        parts = []
        if text:
            parts.append({"type": "text", "text": text})
        if data:
            parts.append({"type": "data", "data": data})

        return {
            "id": task.id,
            "sessionId": task.session_id,
            "status": {"state": TaskState.COMPLETED.value},
            "history": [
                {"role": m.role, "parts": [p.model_dump() for p in m.parts]}
                for m in task.history
            ]
            + [{"role": "agent", "parts": parts}],
            "metadata": task.metadata,
        }
