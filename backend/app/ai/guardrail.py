"""
Guardrail: submission kontentini xavfsizlik nuqtai nazaridan tekshiradi.
- Prompt injection urinishlari
- Sistema ko'rsatmalarini o'zgartirish urinishlari
- Boshqa zararli patternlar
"""

import re

# Kamida 10 ta haqiqiy prompt-injection / ko'rsatma almashtirish pattern
_INJECTION_PATTERNS: list[re.Pattern] = [
    # 1. Klassik "avvalgi ko'rsatmalarni e'tiborsiz qoldiring"
    re.compile(r"ignore\s+(previous|above|prior|all)\s+(instructions?|prompts?|directions?|context)", re.IGNORECASE),
    # 2. "System prompt" haqida gap
    re.compile(r"system\s*prompt", re.IGNORECASE),
    # 3. "Forget everything / forget your instructions"
    re.compile(r"forget\s+(everything|your\s+(previous\s+)?(instructions?|training|rules?|guidelines?))", re.IGNORECASE),
    # 4. "You are now / act as / pretend to be" — rol o'zgartirish urinishi
    re.compile(r"(you\s+are\s+now|act\s+as|pretend\s+(to\s+be|you\s+are)|roleplay\s+as)\s+.{0,60}", re.IGNORECASE),
    # 5. "Do not follow / disregard / override instructions"
    re.compile(r"(disregard|override|bypass|circumvent)\s+(your\s+)?(instructions?|guidelines?|rules?|constraints?)", re.IGNORECASE),
    # 6. "New instruction:" / "Updated instruction:" — ko'rsatma o'rnatish simulatsiyasi
    re.compile(r"\b(new|updated|revised|hidden|secret)\s+instructions?\s*[:=]", re.IGNORECASE),
    # 7. DAN / jailbreak prompt'lari
    re.compile(r"\bDAN\b|do\s+anything\s+now|jailbreak", re.IGNORECASE),
    # 8. "Reveal / show / print your prompt / system message"
    re.compile(r"(reveal|show|print|display|repeat|output)\s+(your\s+)?(system\s+)?(prompt|instructions?|initial\s+message)", re.IGNORECASE),
    # 9. "### Instruction" / "<<SYS>>" kabi model-spesifik maxsus tokenlar
    re.compile(r"(#{2,}\s*(instruction|system|human|assistant)|<<\s*SYS\s*>>|\[INST\]|<\|im_start\|>)", re.IGNORECASE),
    # 10. "Respond only in" — javob formatini majburiy o'zgartirish urinishi
    re.compile(r"respond\s+only\s+(in|as|with)\b", re.IGNORECASE),
    # 11. "Your true self / your real purpose / you were trained to"
    re.compile(r"your\s+(true\s+self|real\s+purpose|actual\s+goal|hidden\s+goal|secret\s+instructions?)", re.IGNORECASE),
    # 12. "Base64 decode" yoki encoded buyruqlar
    re.compile(r"base64\s*decode|eval\s*\(|exec\s*\(", re.IGNORECASE),
]

MAX_CONTENT_LENGTH = 10_000


async def validate_submission_content(content: str) -> bool:
    """
    Submission kontent matnini tekshiradi.
    False qaytarsa — submission rad etiladi.
    """
    if not content or not content.strip():
        return False

    if len(content) > MAX_CONTENT_LENGTH:
        return False

    for pattern in _INJECTION_PATTERNS:
        if pattern.search(content):
            return False

    return True


def get_pattern_count() -> int:
    """Testlar uchun: nechta pattern yuklangan."""
    return len(_INJECTION_PATTERNS)
