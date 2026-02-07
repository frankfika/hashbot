"""Translator Agent - Multi-language translation service."""

from typing import Any

from hashbot.agents.base import BaseAgent, agent_card
from hashbot.agents.registry import register_agent
from hashbot.a2a.messages import Task


@register_agent("translator")
@agent_card(
    name="AI Translator",
    description="High-quality multi-language translation powered by AI. "
    "Supports 50+ languages with context-aware translations.",
    price_per_call=0.05,
    currency="HKDC",
    skills=[
        {
            "id": "translate",
            "name": "Translate Text",
            "description": "Translate text between languages",
            "tags": ["translation", "language", "ai"],
        },
    ],
    version="1.0.0",
)
class TranslatorAgent(BaseAgent):
    """AI translation agent."""

    SUPPORTED_LANGUAGES = {
        "en": "English",
        "zh": "Chinese",
        "ja": "Japanese",
        "ko": "Korean",
        "es": "Spanish",
        "fr": "French",
        "de": "German",
        "ru": "Russian",
        "ar": "Arabic",
        "hi": "Hindi",
    }

    # Demo translations (in real implementation, use actual translation API)
    DEMO_TRANSLATIONS = {
        ("hello", "zh"): "你好",
        ("hello", "ja"): "こんにちは",
        ("hello", "ko"): "안녕하세요",
        ("good morning", "zh"): "早上好",
        ("thank you", "zh"): "谢谢",
        ("blockchain", "zh"): "区块链",
        ("cryptocurrency", "zh"): "加密货币",
    }

    async def process(self, task: Task) -> dict[str, Any]:
        """Process translation request."""
        user_text = ""
        if task.history:
            for part in task.history[-1].parts:
                if hasattr(part, "text"):
                    user_text = part.text
                    break

        # Parse translation request
        # Format: "translate [text] to [language]"
        user_lower = user_text.lower()

        if "to " in user_lower:
            parts = user_lower.split(" to ")
            if len(parts) >= 2:
                text_part = parts[0].replace("translate ", "").strip()
                target_lang = parts[-1].strip()

                # Find language code
                lang_code = None
                for code, name in self.SUPPORTED_LANGUAGES.items():
                    if (
                        target_lang == code
                        or target_lang == name.lower()
                        or target_lang.startswith(name.lower()[:3])
                    ):
                        lang_code = code
                        break

                if lang_code:
                    return await self._translate(task, text_part, lang_code)

        # Show help
        languages = ", ".join(
            [f"{name} ({code})" for code, name in self.SUPPORTED_LANGUAGES.items()]
        )
        return self._create_success_response(
            task,
            text=f"**Translation Service**\n\n"
            f"Usage: `translate [text] to [language]`\n\n"
            f"Example: `translate hello to Chinese`\n\n"
            f"Supported languages: {languages}",
        )

    async def _translate(
        self, task: Task, text: str, target_lang: str
    ) -> dict[str, Any]:
        """Perform translation."""
        # Check demo translations
        translation = self.DEMO_TRANSLATIONS.get((text.lower(), target_lang))

        if not translation:
            # Placeholder for actual translation
            translation = f"[{text} → {self.SUPPORTED_LANGUAGES[target_lang]}]"

        return self._create_success_response(
            task,
            text=f"**Translation Result**\n\n"
            f"Original: {text}\n"
            f"Language: {self.SUPPORTED_LANGUAGES[target_lang]}\n"
            f"Translation: **{translation}**",
            data={
                "original": text,
                "translation": translation,
                "source_lang": "en",
                "target_lang": target_lang,
            },
        )
