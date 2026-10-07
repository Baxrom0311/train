"""Portfolio slug'i (CONTRACT.md §13.2): shakl va ismdan taklif."""
import re
import unicodedata

SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{1,38}[a-z0-9]$")
_APOSTROPHES = "'ʻʼ‘’`"
# O'zbek kirill → lotin (ism uchun yetarli)
_CYRILLIC = dict(zip(
    "абвгдеёжзийклмнопрстуфхцчшщъыьэюяўқғҳ",
    ["a", "b", "v", "g", "d", "e", "yo", "j", "z", "i", "y", "k", "l", "m", "n", "o", "p", "r", "s", "t",
     "u", "f", "x", "ts", "ch", "sh", "sh", "", "i", "", "e", "yu", "ya", "o", "q", "g", "h"],
))


def from_name(full_name: str) -> str:
    """`O'tkir G'ulomov` → `otkir-gulomov`; juda qisqa bo'lsa — `talaba`."""
    text = "".join(_CYRILLIC.get(c, c) for c in full_name.lower())
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c) and c not in _APOSTROPHES).lower()
    slug = re.sub(r"[^a-z0-9]+", "-", text).strip("-")[:40].strip("-")
    return slug if SLUG.match(slug) else "talaba"
