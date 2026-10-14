"""
E2E uchun soxta LLM (CONTRACT.md §34.3): OpenAI-mos `POST /v1/chat/completions`.

Backend `LLM_PROVIDERS=openai`, `OPENAI_BASE_URL=http://127.0.0.1:<port>/v1`
bilan shu serverga ulanadi — tarmoqqa chiqmaydi, javoblar deterministik:

- rubrika bo'yicha baholash (`ai/evaluator.py` prompt'idagi "RUBRIC" bo'limi) —
  har mezonga `SCORE` ball va `FEEDBACK` izohi;
- boshqa JSON so'rovlar (hisobot xulosasi, aniqlashtirish va h.k.) — `{}`:
  sxemaga mos emas, chaqiruvchi o'zining AI'siz zaxira yo'liga o'tadi (§9.10);
- oddiy matn (personaj, mentor) — `REPLY`.

Faqat stdlib. Ishga tushirish: `python tools/e2e/fake_llm.py --port 8090`.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SCORE = 82
FEEDBACK = "Reja aniq va tekshirsa bo'ladigan. Keyingi safar to'siqni kimdan va qachon so'rashingizni ham yozing."
REPLY = "Rahmat, xabaringizni oldim. Hozir ko'rib chiqaman."

_RUBRIC = re.compile(r"^RUBRIC \(id .*?\):\n((?:- .+\n?)+)", re.MULTILINE)
_CRITERION = re.compile(r"^- (\S+) — ", re.MULTILINE)


def criterion_ids(messages: list[dict]) -> list[str] | None:
    """Baholash so'rovi bo'lsa — mezon id'lari, aks holda None."""
    for m in messages:
        if m.get("role") != "user":
            continue
        found = _RUBRIC.search(m.get("content") or "")
        if found:
            return _CRITERION.findall(found.group(1))
    return None


def answer(body: dict) -> str:
    messages = body.get("messages") or []
    json_mode = (body.get("response_format") or {}).get("type") == "json_object"
    if not json_mode:
        return REPLY
    ids = criterion_ids(messages)
    if not ids:
        return "{}"
    return json.dumps({
        "criteria": [{"id": i, "score": SCORE, "evidence": "Javobda mezon talabi bajarilgan."} for i in ids],
        "short_feedback": FEEDBACK,
    }, ensure_ascii=False)


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, payload: dict) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._send(200, {"status": "ok"})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path.rstrip("/") != "/v1/chat/completions":
            self._send(404, {"error": "not found"})
            return
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        except ValueError:
            self._send(400, {"error": "invalid json"})
            return
        text = answer(body)
        self._send(200, {
            "id": "fake",
            "object": "chat.completion",
            "model": body.get("model", "fake"),
            "choices": [{"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
        })

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("fake-llm: " + fmt % args + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8090)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"fake-llm: http://{args.host}:{args.port}/v1", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
