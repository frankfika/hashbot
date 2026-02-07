"""A2A Protocol message types based on Google A2A specification."""

from datetime import datetime
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class TaskState(str, Enum):
    """Task lifecycle states."""

    SUBMITTED = "submitted"
    WORKING = "working"
    INPUT_REQUIRED = "input-required"
    COMPLETED = "completed"
    CANCELED = "canceled"
    FAILED = "failed"


class TextPart(BaseModel):
    """Text content part."""

    type: Literal["text"] = "text"
    text: str


class DataPart(BaseModel):
    """Structured data part."""

    type: Literal["data"] = "data"
    data: dict[str, Any]


class FilePart(BaseModel):
    """File content part."""

    type: Literal["file"] = "file"
    file: dict[str, Any]  # Contains name, mimeType, bytes/uri


Part = TextPart | DataPart | FilePart


class Message(BaseModel):
    """A2A Message."""

    role: Literal["user", "agent"]
    parts: list[Part]
    metadata: dict[str, Any] = Field(default_factory=dict)


class Task(BaseModel):
    """A2A Task representing a unit of work."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    status: TaskState = TaskState.SUBMITTED
    history: list[Message] = Field(default_factory=list)
    artifacts: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def add_message(self, role: Literal["user", "agent"], text: str) -> None:
        """Add a text message to history."""
        self.history.append(Message(role=role, parts=[TextPart(text=text)]))
        self.updated_at = datetime.utcnow()

    def add_data(self, role: Literal["user", "agent"], data: dict[str, Any]) -> None:
        """Add structured data to history."""
        self.history.append(Message(role=role, parts=[DataPart(data=data)]))
        self.updated_at = datetime.utcnow()


class Skill(BaseModel):
    """Agent skill definition."""

    id: str
    name: str
    description: str
    tags: list[str] = Field(default_factory=list)
    input_modes: list[str] = Field(default_factory=lambda: ["text"])
    output_modes: list[str] = Field(default_factory=lambda: ["text"])


class AgentCard(BaseModel):
    """A2A Agent Card - describes agent capabilities."""

    name: str
    description: str
    url: str
    version: str = "1.0.0"
    protocol_version: str = "0.1"
    skills: list[Skill] = Field(default_factory=list)
    default_input_modes: list[str] = Field(default_factory=lambda: ["text"])
    default_output_modes: list[str] = Field(default_factory=lambda: ["text"])

    # x402 extension
    x402_enabled: bool = False
    x402_extension_uri: str = "https://github.com/google-a2a/a2a-x402/v0.1"

    # Custom metadata
    metadata: dict[str, Any] = Field(default_factory=dict)


class A2AMessage(BaseModel):
    """Top-level A2A protocol message."""

    jsonrpc: str = "2.0"
    id: str = Field(default_factory=lambda: str(uuid4()))
    method: str
    params: dict[str, Any] = Field(default_factory=dict)


class A2AResponse(BaseModel):
    """A2A protocol response."""

    jsonrpc: str = "2.0"
    id: str
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
