"""Agent workspace lifecycle management for OpenClaw."""

import shutil
from pathlib import Path

from hashbot.config import get_settings
from hashbot.openclaw.client import OpenClawClient


class OpenClawManager:
    """Manages OpenClaw agent workspaces and gateway registration."""

    def __init__(self, client: OpenClawClient | None = None):
        settings = get_settings()
        self.workspaces_dir = Path(settings.openclaw_workspaces_dir).expanduser()
        self.client = client or OpenClawClient()

    def _workspace_path(self, agent_id: str) -> Path:
        return self.workspaces_dir / agent_id

    async def create_agent_workspace(
        self,
        agent_id: str,
        name: str,
        description: str,
        soul_text: str = "",
    ) -> str:
        """Create a workspace directory with AGENTS.md, SOUL.md, etc."""
        ws = self._workspace_path(agent_id)
        ws.mkdir(parents=True, exist_ok=True)
        (ws / "skills").mkdir(exist_ok=True)
        (ws / "memory").mkdir(exist_ok=True)

        # AGENTS.md — agent identity
        (ws / "AGENTS.md").write_text(
            f"# {name}\n\n{description}\n\n"
            f"Agent ID: {agent_id}\n"
            f"Platform: HashBot on HashKey Chain\n",
            encoding="utf-8",
        )

        # SOUL.md — personality / system prompt
        soul = soul_text or (
            f"You are {name}, an AI agent running on the HashBot platform.\n"
            f"{description}\n\n"
            "Be helpful, concise, and accurate. "
            "You have access to HashKey Chain tools for crypto operations.\n"
        )
        (ws / "SOUL.md").write_text(soul, encoding="utf-8")

        # TOOLS.md — available tools
        (ws / "TOOLS.md").write_text(
            "# Available Tools\n\n"
            "Tools are provided by installed skills.\n"
            "Use /skills in Telegram to manage your agent's skills.\n",
            encoding="utf-8",
        )

        # USER.md — user-facing instructions
        (ws / "USER.md").write_text(
            "# User Guide\n\n"
            f"Chat with {name} via Telegram or the HashBot dashboard.\n",
            encoding="utf-8",
        )

        return str(ws)

    async def register_agent_in_gateway(
        self,
        agent_id: str,
        workspace_path: str,
    ) -> None:
        """Register an agent in the OpenClaw gateway config."""
        settings = get_settings()
        try:
            cfg = await self.client.get_config()
            raw = cfg.get("raw", "")
            base_hash = cfg.get("hash", "")

            # Append agent entry
            entry = (
                f"\n[[agents]]\n"
                f'id = "{agent_id}"\n'
                f'workspace = "{workspace_path}"\n'
                f'model = "{settings.default_agent_model}"\n'
            )
            await self.client.patch_config(raw + entry, base_hash)
        except Exception:
            # Gateway may not be running; workspace is still usable
            pass

    async def install_skill_to_workspace(
        self,
        workspace_path: str,
        skill_slug: str,
        skill_content: str,
    ) -> None:
        """Write a SKILL.md file into the workspace skills directory."""
        skills_dir = Path(workspace_path) / "skills"
        skills_dir.mkdir(parents=True, exist_ok=True)
        (skills_dir / f"{skill_slug}.md").write_text(skill_content, encoding="utf-8")

    async def remove_skill_from_workspace(
        self,
        workspace_path: str,
        skill_slug: str,
    ) -> None:
        """Remove a skill file from the workspace."""
        skill_file = Path(workspace_path) / "skills" / f"{skill_slug}.md"
        if skill_file.exists():
            skill_file.unlink()

    async def delete_agent_workspace(self, agent_id: str) -> None:
        """Remove workspace directory and unregister from gateway."""
        ws = self._workspace_path(agent_id)
        if ws.exists():
            shutil.rmtree(ws)

        # Best-effort unregister from gateway
        try:
            cfg = await self.client.get_config()
            raw = cfg.get("raw", "")
            base_hash = cfg.get("hash", "")
            # Remove the agent block (simple text removal)
            lines = raw.splitlines(keepends=True)
            filtered: list[str] = []
            skip = False
            for line in lines:
                if line.strip() == "[[agents]]":
                    skip = False
                if skip:
                    continue
                if line.strip() == "[[agents]]":
                    # Peek ahead: check if this block is for our agent
                    idx = lines.index(line)
                    block = "".join(lines[idx : idx + 5])
                    if f'id = "{agent_id}"' in block:
                        skip = True
                        continue
                filtered.append(line)
            await self.client.patch_config("".join(filtered), base_hash)
        except Exception:
            pass
