import re
from typing import Tuple

SUSPICIOUS_PATTERNS = [
    r"ignore previous instructions",
    r"system prompt",
    r"disregard all rules",
    r"you are now DAN",
    r"output raw secrets",
    r"admin bypass",
    r"reveal confidential instructions",
    r"execute arbitrary code"
]

def inspect_prompt_safety(user_input: str) -> Tuple[bool, str]:
    """
    Talaba topshirig'i matnini Prompt Injection va xavfli buyruqlar bo'yicha tekshirish.
    """
    if not user_input or len(user_input.strip()) == 0:
        return True, ""

    lowered = user_input.lower()
    for pattern in SUSPICIOUS_PATTERNS:
        if re.search(pattern, lowered):
            return False, f"Xavfsizlik qoidasi buzildi (Taqiqlangan so'rov aniqlandi: '{pattern}')"

    # Maksimal uzunlik filtri (DDoS / Token exhaustion himoyasi)
    if len(user_input) > 20000:
        return False, "Topshiriq matni maksimal limitdan (20,000 belgi) oshib ketdi."

    return True, ""

def wrap_with_safe_delimiters(user_input: str, task_context: str) -> str:
    """Prompt injectionga qarshi ajratuvchi (delimiters) bilan o'rash"""
    return (
        f"--- BOSHLANISH: TALABA TOPSHIRIG'I KONTEKSTI ---\n"
        f"Vazifa: {task_context}\n"
        f"--- TALABA JAVOBI ---\n"
        f"{user_input}\n"
        f"--- TUGASH: TALABA JAVOBI ---\n"
    )
