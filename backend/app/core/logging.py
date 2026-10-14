"""
Log sozlamasi (CONTRACT.md §32.1) — API va worker uchun bir xil.

`LOG_FORMAT=json`: bir qator — bitta JSON obyekt (Docker `json-file` va
log yig'uvchilar uchun); `text` — lokal ishlab chiqishda o'qishga qulay.
uvicorn va arq o'z handler'larini qo'yadi — ular olib tashlanib, yozuvlar
root'ga o'tkaziladi, shunda hamma qator bir formatda chiqadi.
"""
from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone

from app.config import settings

# So'rov identifikatori (§32.2) — middleware o'rnatadi, har log qatoriga qo'shiladi
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

# Kutubxonalarning o'z handler'lari olib tashlanadi — yozuv root'ga boradi
_ADOPTED = ("uvicorn", "uvicorn.error", "arq")
# Har AI so'rovi INFO'da yoziladi — log'ni to'ldirmasin
_QUIET = ("httpx", "httpcore")
# `logging.LogRecord`ning standart atributlari — qolgani `extra` sifatida JSON'ga tushadi
_RECORD_ATTRS = frozenset(vars(logging.makeLogRecord({}))) | {"message", "asctime", "taskName", "color_message", "rid"}

_source = "api"


class _ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        record.source = _source
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        out = {
            "ts": datetime.fromtimestamp(record.created, timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "source": getattr(record, "source", _source),
        }
        if getattr(record, "request_id", None):
            out["request_id"] = record.request_id
        for key, value in vars(record).items():
            if key not in _RECORD_ATTRS and key not in out and key not in ("request_id", "source"):
                out[key] = value
        if record.exc_info:
            out["exc"] = self.formatException(record.exc_info)
        elif record.exc_text:
            out["exc"] = record.exc_text
        return json.dumps(out, ensure_ascii=False, default=str)


class TextFormatter(logging.Formatter):
    def __init__(self) -> None:
        super().__init__("%(asctime)s %(levelname)-7s %(name)s%(rid)s: %(message)s")

    def format(self, record: logging.LogRecord) -> str:
        rid = getattr(record, "request_id", None)
        record.rid = f" [{rid[:8]}]" if rid else ""
        return super().format(record)


class _Handler(logging.StreamHandler):
    """Bizning stdout handler'imiz — qayta sozlashda tanib olinadi va almashtiriladi.

    Oqim har yozishda `sys.stdout`dan olinadi: import paytidagi obyekt keyin
    almashtirilsa (pytest capture, uvicorn reload) yopiq faylga yozilmaydi.
    """

    @property
    def stream(self):
        return sys.stdout

    @stream.setter
    def stream(self, _value) -> None:
        pass


def setup_logging(source: str = "api") -> None:
    """Idempotent: qayta chaqirilsa (worker startup, testlar) handler ko'paymaydi."""
    global _source
    _source = source

    handler = _Handler()
    handler.setFormatter(JsonFormatter() if settings.LOG_FORMAT == "json" else TextFormatter())
    handler.addFilter(_ContextFilter())

    root = logging.getLogger()
    for old in [h for h in root.handlers if isinstance(h, _Handler)]:
        root.removeHandler(old)
    root.addHandler(handler)
    root.setLevel(settings.LOG_LEVEL)

    for name in _ADOPTED:
        lib = logging.getLogger(name)
        lib.handlers.clear()
        lib.propagate = True
        lib.setLevel(logging.NOTSET)
    # §32.2: o'rniga `app.access` (query string'siz, request_id bilan)
    logging.getLogger("uvicorn.access").disabled = True
    for name in _QUIET:
        logging.getLogger(name).setLevel(logging.WARNING)
