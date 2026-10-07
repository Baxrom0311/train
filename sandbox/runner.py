"""
Sandbox runner (CONTRACT.md §19.1) — talaba kodini alohida konteynerda bajaradi.

Faqat stdlib. Konteyner tarmoqdan, DB/Redis'dan va secretlardan ajratilgan;
bu yerdagi rlimit va vaqtinchalik papka — har so'rovni bir-biridan ajratish.

    SANDBOX_TOKEN=... python runner.py          # :8100
"""
import ast
import hmac
import json
import os
import resource
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HARNESS = Path(__file__).with_name("harness.py")
PORT = int(os.environ.get("SANDBOX_PORT", "8100"))
TOKEN = os.environ.get("SANDBOX_TOKEN", "")

MAX_BODY = 256 * 1024
SCRIPT_TIMEOUT = 3.0
TEST_TIMEOUT = 10.0
STDOUT_MAX = 4096
STDERR_MAX = 2048
MEMORY = 256 * 1024 * 1024
SLOTS = threading.BoundedSemaphore(2)
MODULE_CHARS = set("abcdefghijklmnopqrstuvwxyz0123456789_")


def _limits(cpu_seconds: int):
    def apply() -> None:
        for limit, value in (
            (resource.RLIMIT_CPU, cpu_seconds),
            (resource.RLIMIT_AS, MEMORY),
            (resource.RLIMIT_FSIZE, 1024 * 1024),
            (resource.RLIMIT_NPROC, 0),
            (resource.RLIMIT_NOFILE, 32),
            (resource.RLIMIT_CORE, 0),
        ):
            resource.setrlimit(limit, (value, value))
    return apply


def test_names(tests: str) -> list[str]:
    return [n.name for n in ast.parse(tests).body if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")]


def execute(code: str, tests: str | None = None, module: str = "solution", timeout: float | None = None) -> dict:
    """Bitta bajarish; har chaqiruv o'z vaqtinchalik papkasida."""
    limit = TEST_TIMEOUT if tests else SCRIPT_TIMEOUT
    timeout = min(float(timeout or limit), limit)
    workdir = tempfile.mkdtemp(prefix="run-")
    nonce = secrets.token_hex(16)
    try:
        if tests:
            names = test_names(tests)
            Path(workdir, f"{module}.py").write_text(code, encoding="utf-8")
            Path(workdir, "hidden_tests.py").write_text(tests, encoding="utf-8")
            argv = [sys.executable, "-I", str(HARNESS), "hidden_tests"]
            stdin = nonce + "\n"
        else:
            names = []
            Path(workdir, "main.py").write_text(code, encoding="utf-8")
            argv = [sys.executable, "-I", "main.py"]
            stdin = ""
        try:
            proc = subprocess.run(
                argv, cwd=workdir, input=stdin, capture_output=True, text=True,
                timeout=timeout, env={"PYTHONIOENCODING": "utf-8", "HOME": workdir},
                preexec_fn=_limits(int(timeout) + 1),
            )
        except subprocess.TimeoutExpired:
            return _result("timeout", "", f"Timeout: {timeout:.0f}s ichida tugamadi", names, [])
        stdout, stderr = proc.stdout, proc.stderr
        if not tests:
            return _result("ok" if proc.returncode == 0 else "error", stdout, stderr, [], [], exit_code=proc.returncode)
        head, sep, tail = stdout.rpartition(f"\n{nonce} ")
        if not sep:
            # harness natija yozmasdan tugadi (os._exit, xotira, signal)
            return _result("error", stdout, stderr or f"Jarayon {proc.returncode} kodi bilan tugadi", names, [])
        try:
            report = json.loads(tail.splitlines()[0])
        except (ValueError, IndexError):
            return _result("error", head, stderr or "Natija o'qilmadi", names, [])
        return _result(report["status"], head, stderr, names, report["tests"])
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def _result(status, stdout, stderr, names, tests, exit_code=None) -> dict:
    by_name = {t["name"]: t for t in tests}
    # e'lon qilingan har test natijada bor — import yiqilsa hammasi "ok: false"
    rows = [by_name.get(n) or {"name": n, "ok": False, "message": "Bajarilmadi"} for n in names]
    out = {
        "status": status,
        "stdout": stdout[:STDOUT_MAX],
        "stderr": stderr[-STDERR_MAX:],
        "passed": sum(1 for r in rows if r["ok"]),
        "total": len(rows),
        "tests": rows,
    }
    if exit_code is not None:
        out["exit_code"] = exit_code
    return out


class Handler(BaseHTTPRequestHandler):
    server_version = "tryjob-sandbox"

    def _send(self, status: int, body: dict) -> None:
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/health":
            return self._send(HTTPStatus.OK, {"ok": True})
        self._send(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def do_POST(self):
        if self.path != "/run":
            return self._send(HTTPStatus.NOT_FOUND, {"error": "not_found"})
        auth = self.headers.get("Authorization", "")
        if not hmac.compare_digest(auth.encode(), f"Bearer {TOKEN}".encode()):
            return self._send(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0 or length > MAX_BODY:
            return self._send(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "body_size"})
        try:
            req = json.loads(self.rfile.read(length))
            code, tests = req["code"], req.get("tests")
            module = req.get("module") or "solution"
            timeout = req.get("timeout")
            if not isinstance(code, str) or (tests is not None and not isinstance(tests, str)):
                raise ValueError
            if not set(module) <= MODULE_CHARS or module[0].isdigit() or module == "hidden_tests":
                raise ValueError
            if tests is not None:
                test_names(tests)
        except (ValueError, KeyError, TypeError, SyntaxError):
            return self._send(HTTPStatus.BAD_REQUEST, {"error": "bad_request"})
        if not SLOTS.acquire(blocking=False):
            return self._send(HTTPStatus.SERVICE_UNAVAILABLE, {"error": "busy"})
        try:
            result = execute(code, tests, module, timeout)
        finally:
            SLOTS.release()
        self._send(HTTPStatus.OK, result)

    def log_message(self, fmt, *args):  # so'rov tanasi (kod) log'ga tushmasin
        sys.stderr.write(f"{self.address_string()} {fmt % args}\n")


def main() -> None:
    if not TOKEN:
        sys.exit("SANDBOX_TOKEN kerak")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
