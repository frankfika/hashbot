"""HTTP client for OpenClaw Gateway."""

import httpx

from hashbot.config import get_settings


class OpenClawClient:
    """Client for communicating with the OpenClaw Gateway."""

    def __init__(self, base_url: str | None = None, token: str | None = None):
        settings = get_settings()
        self.base_url = (base_url or settings.openclaw_gateway_url).rstrip("/")
        self.token = token or settings.openclaw_gateway_token
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            headers = {}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=120,
            )
        return self._client

    async def send_message(
        self,
        agent_id: str,
        session_key: str,
        text: str,
    ) -> str:
        """Send a chat message to an OpenClaw agent and return the response text."""
        client = await self._get_client()
        resp = await client.post(
            "/v1/chat/completions",
            json={
                "model": f"agent:{agent_id}",
                "messages": [{"role": "user", "content": text}],
                "session_key": session_key,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        # OpenClaw returns OpenAI-compatible format
        choices = data.get("choices", [])
        if choices:
            return choices[0].get("message", {}).get("content", "")
        return ""

    async def invoke_tool(
        self,
        tool_name: str,
        args: dict,
        session_key: str = "",
    ) -> dict:
        """Invoke a tool on the OpenClaw gateway."""
        client = await self._get_client()
        resp = await client.post(
            "/tools/invoke",
            json={
                "tool": tool_name,
                "arguments": args,
                "session_key": session_key,
            },
        )
        resp.raise_for_status()
        return resp.json()

    async def get_config(self) -> dict:
        """Read gateway configuration."""
        client = await self._get_client()
        resp = await client.get("/config")
        resp.raise_for_status()
        return resp.json()

    async def patch_config(self, raw: str, base_hash: str = "") -> dict:
        """Update gateway configuration."""
        client = await self._get_client()
        body: dict = {"raw": raw}
        if base_hash:
            body["base_hash"] = base_hash
        resp = await client.patch("/config", json=body)
        resp.raise_for_status()
        return resp.json()

    async def health_check(self) -> bool:
        """Check if the OpenClaw gateway is reachable."""
        try:
            client = await self._get_client()
            resp = await client.get("/health")
            return resp.status_code == 200
        except Exception:
            return False

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
