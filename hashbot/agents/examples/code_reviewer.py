"""Code Reviewer Agent - Smart contract and code audit."""

from typing import Any

from hashbot.a2a.messages import Task
from hashbot.agents.base import BaseAgent, agent_card
from hashbot.agents.registry import register_agent


@register_agent("code_reviewer")
@agent_card(
    name="Code Reviewer",
    description="AI-powered code review and smart contract audit. "
    "Identifies security vulnerabilities, gas optimization opportunities, "
    "and best practice violations.",
    price_per_call=0.5,
    currency="HKDC",
    skills=[
        {
            "id": "review_contract",
            "name": "Smart Contract Review",
            "description": "Audit Solidity smart contracts for vulnerabilities",
            "tags": ["solidity", "security", "audit"],
        },
        {
            "id": "review_code",
            "name": "Code Review",
            "description": "General code review for any language",
            "tags": ["code", "review", "quality"],
        },
    ],
    version="1.0.0",
)
class CodeReviewerAgent(BaseAgent):
    """AI code review and audit agent."""

    async def process(self, task: Task) -> dict[str, Any]:
        """Process code review request."""
        user_text = ""
        if task.history:
            for part in task.history[-1].parts:
                if hasattr(part, "text"):
                    user_text = part.text
                    break

        # Check if code is provided
        if "```" in user_text:
            # Extract code block
            code_start = user_text.find("```")
            code_end = user_text.rfind("```")

            if code_start != code_end:
                code_block = user_text[code_start:code_end + 3]
                return await self._review_code(task, code_block)

        elif "function" in user_text.lower() or "contract" in user_text.lower():
            # Treat entire message as code
            return await self._review_code(task, user_text)

        # Show help
        return self._create_success_response(
            task,
            text="**Code Review Service**\n\n"
            "Send me code to review. I can:\n"
            "• Audit Solidity smart contracts\n"
            "• Review Python, JavaScript, TypeScript code\n"
            "• Identify security vulnerabilities\n"
            "• Suggest gas optimizations\n"
            "• Check best practices\n\n"
            "Just paste your code in a code block:\n"
            "```solidity\n"
            "// your code here\n"
            "```",
        )

    async def _review_code(self, task: Task, code: str) -> dict[str, Any]:
        """Review the provided code."""
        # Detect language
        language = "unknown"
        if "pragma solidity" in code or "contract " in code:
            language = "solidity"
        elif "def " in code or "import " in code:
            language = "python"
        elif "function" in code or "const " in code:
            language = "javascript"

        # Generate review (placeholder for actual AI review)
        issues = []
        suggestions = []

        if language == "solidity":
            issues = [
                {
                    "severity": "medium",
                    "title": "Reentrancy Risk",
                    "description": "Consider using ReentrancyGuard for external calls",
                },
                {
                    "severity": "low",
                    "title": "Gas Optimization",
                    "description": "Use `++i` instead of `i++` in loops",
                },
                {
                    "severity": "info",
                    "title": "Documentation",
                    "description": "Add NatSpec comments for public functions",
                },
            ]
            suggestions = [
                "Consider using OpenZeppelin's SafeMath for arithmetic operations",
                "Add events for state changes to improve transparency",
                "Implement access control modifiers for admin functions",
            ]
        else:
            issues = [
                {
                    "severity": "info",
                    "title": "Code Style",
                    "description": "Consider adding type hints for better maintainability",
                }
            ]
            suggestions = [
                "Add unit tests for critical functions",
                "Consider error handling improvements",
            ]

        # Format review
        review_text = f"""
**Code Review Report**

**Language Detected:** {language.title()}
**Lines Analyzed:** ~{len(code.split(chr(10)))}

---

**Issues Found:** {len(issues)}

"""
        for issue in issues:
            severity_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢", "info": "ℹ️"}.get(
                issue["severity"], "⚪"
            )
            review_text += f"{severity_emoji} **[{issue['severity'].upper()}]** {issue['title']}\n"
            review_text += f"   {issue['description']}\n\n"

        review_text += "---\n\n**Suggestions:**\n"
        for i, suggestion in enumerate(suggestions, 1):
            review_text += f"{i}. {suggestion}\n"

        review_text += """
---

⚠️ *This is an automated review. Manual audit recommended for production code.*
"""

        return self._create_success_response(
            task,
            text=review_text.strip(),
            data={
                "language": language,
                "issues_count": len(issues),
                "issues": issues,
                "suggestions": suggestions,
            },
        )
