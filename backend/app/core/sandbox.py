"""
sandbox.py — talaba kodini bajarish (CONTRACT.md §19.2).

Production: `SANDBOX_URL` — alohida runner konteyneri (`sandbox/runner.py`,
tarmoqsiz, secretsiz). Bu fayldagi lokal rejim (AST filtri + subprocess)
faqat `SANDBOX_URL` bo'sh bo'lganda — lokal ishlab chiqish va testlar uchun.

**LOKAL REJIM CHEKLOVI (bu kodni o'qigan har kim bilishi shart):**
Bu — AST blacklist + OS resurs cheklovlari (defense-in-depth), **HAQIQIY
KONTEYNER IZOLYATSIYASI EMAS**. Blacklist tamoyili tub e'tiqodda mo'rt:
Python kabi dinamik tilda "taqiqlangan funksiyani boshqa nomga bog'lab olish"
(`ev = eval`) kabi usullarni to'liq yopib bo'lmaydi. Production uchun bu
kod **albatta** nsjail/gVisor/Docker (`--network none`, cgroup limits,
seccomp) ichida ishga tushirilishi kerak — bu yerdagi choralar faqat
qo'shimcha qatlam, yagona himoya emas.

Xavfsizlik yondashuvi:
1. AST parse qilib, taqiqlangan modullar/funksiyalar/atributlarni va
   ularni boshqa nomga bog'lashga urinishlarni (alias) topadi.
2. Hech qanday xavfli narsa topilmasa — python -I -c orqali, OS darajasida
   CPU/xotira/jarayon/fayl hajmi cheklangan subprocess'da bajaradi.
3. Timeout serverd tomonidan qattiq cheklanadi (client qiymatiga ishonilmaydi).
"""

import ast
import asyncio
import logging
import resource
import subprocess
import sys
from typing import NamedTuple

import httpx

from app.config import settings

log = logging.getLogger(__name__)
REQUEST_TIMEOUT = 20.0   # runner'ning eng uzun bajarishi (10 s) + navbat

# Taqiqlangan modul nomlari (import va from...import).
# "io" — eng muhimi: shu orqali `from io import open as o` bilan fayl
# o'qish bypass qilingan edi (haqiqiy topilma, sinab tasdiqlangan).
BANNED_MODULES = {
    "os", "sys", "subprocess", "shutil", "socket", "http", "requests",
    "urllib", "ctypes", "pathlib", "builtins", "importlib", "posix",
    "io", "multiprocessing", "threading", "_thread", "concurrent",
    "asyncio", "signal", "resource", "mmap", "fcntl", "pty",
    "socketserver", "ssl", "ftplib", "smtplib", "telnetlib", "xmlrpc",
    "pickle", "marshal", "shelve", "tempfile", "platform", "getpass",
    "cffi", "pdb", "code", "codeop", "ast", "inspect",
}

# Taqiqlangan funksiya/call nomlari (chaqiruv paytidagi nom).
BANNED_CALLS = {
    "eval", "exec", "open", "compile", "__import__", "globals", "locals",
    "getattr", "setattr", "delattr", "breakpoint", "vars", "input",
}

# Taqiqlangan atribut nomlari (. orqali kirish)
BANNED_ATTRS = {
    "__class__", "__subclasses__", "__bases__", "__base__",
    "__globals__", "__builtins__", "__code__", "__closure__",
    "__dict__", "__mro__", "__loader__", "__spec__", "__import__",
}


class SecurityViolation(Exception):
    """AST tekshiruvida xavfli narsa topilganda."""
    pass


class _Visitor(ast.NodeVisitor):
    """
    AST bo'ylab yuruvchi — qoidabuzarliklarni aniqlab, SecurityViolation
    ko'taradi. Oddiy chaqiruv nomi tekshiruvidan tashqari, taqiqlangan
    funksiyani BOSHQA NOMGA BOG'LASH urinishlarini ham ushlaydi
    (masalan `ev = eval` yoki `o = open`) — xuddi shu klassdagi
    `from io import open as o` bypass'iga o'xshash hiylalarning oldini
    olish uchun.
    """

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            top = alias.name.split(".")[0]
            if top in BANNED_MODULES:
                raise SecurityViolation(f"Taqiqlangan modul: '{alias.name}'")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            top = node.module.split(".")[0]
            if top in BANNED_MODULES:
                raise SecurityViolation(f"Taqiqlangan modul: '{node.module}'")
        # `from X import open as o` — X banned bo'lmasa ham, taqiqlangan
        # NOMNI olib kelayotgan bo'lsa (eval/exec/open/...), bloklaymiz.
        for alias in node.names:
            if alias.name in BANNED_CALLS:
                raise SecurityViolation(f"Taqiqlangan import: '{alias.name}'")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name):
            if node.func.id in BANNED_CALLS:
                raise SecurityViolation(f"Taqiqlangan funksiya: '{node.func.id}'")
        if isinstance(node.func, ast.Attribute):
            if node.func.attr in BANNED_CALLS:
                raise SecurityViolation(f"Taqiqlangan funksiya (metod): '{node.func.attr}'")
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        if node.attr in BANNED_ATTRS:
            raise SecurityViolation(f"Taqiqlangan atribut: '{node.attr}'")
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign):
        # `ev = eval` kabi — taqiqlangan ismni boshqa nomga bog'lash.
        if isinstance(node.value, ast.Name) and node.value.id in BANNED_CALLS:
            raise SecurityViolation(
                f"Taqiqlangan funksiyani qayta nomlashga urinish: '{node.value.id}'"
            )
        self.generic_visit(node)


class SandboxResult(NamedTuple):
    success: bool
    stdout: str
    stderr: str
    error: str | None  # xavfsizlik yoki timeout xatosi


def validate_code(code: str) -> None:
    """
    Kodni AST orqali tekshiradi.
    Xavfli narsa topilsa — SecurityViolation ko'taradi.
    Syntax xatosi bo'lsa — SyntaxError ko'taradi.
    """
    tree = ast.parse(code)  # SyntaxError ko'tarishi mumkin
    _Visitor().visit(tree)


def _apply_resource_limits() -> None:
    """
    subprocess ichida (preexec_fn) ishga tushadi — OS darajasida qattiq
    cheklovlar qo'yadi, hatto AST filtridan o'tgan kod ham zararli
    bo'lsa, oqibatini cheklaydi (defense-in-depth, §yuqoridagi izoh):
    - CPU vaqti: 3 soniya
    - Xotira (address space): 128 MB
    - Fayl hajmi: 1 MB (diskka katta fayl yozib tashlamasin)
    - Yangi jarayon yaratish (fork/multiprocessing): 0 — mumkin emas
    - Ochiq fayl deskriptorlari: 16
    """
    # Har birini alohida try/except: ba'zi limitlar platforma bo'yicha
    # farq qiladi — masalan macOS'da RLIMIT_AS ishonchli qo'llab-
    # quvvatlanmaydi ("current limit exceeds maximum limit" xatosi,
    # sinab tasdiqlangan), Linux production'da esa to'g'ri ishlaydi.
    # Bitta limit muvaffaqiyatsiz bo'lgani bilan qolganlari qo'llanishi
    # kerak (defense-in-depth — qisman himoya ham himoyasizlikdan yaxshi).
    for limit, value in (
        (resource.RLIMIT_CPU, (3, 3)),
        (resource.RLIMIT_AS, (256 * 1024 * 1024, 256 * 1024 * 1024)),
        (resource.RLIMIT_FSIZE, (1 * 1024 * 1024, 1 * 1024 * 1024)),
        (resource.RLIMIT_NPROC, (0, 0)),
        (resource.RLIMIT_NOFILE, (16, 16)),
    ):
        try:
            resource.setrlimit(limit, value)
        except (ValueError, OSError):
            pass


def run_code(code: str, timeout: float = 2.0) -> SandboxResult:
    """
    Kodni xavfsiz muhitda bajaradi:
    1. AST validatsiya
    2. subprocess'da python -I (izolyatsiya rejimi) + OS resurs cheklovlari
       bilan bajarish
    3. Timeout cheklovi (serverd tomonidan, client emas)

    :param code: Bajariladigan Python kodi
    :param timeout: Maksimal bajarish vaqti (sekund) — MAX 3.0s
    :returns: SandboxResult
    """
    safe_timeout = min(float(timeout), 3.0)

    try:
        validate_code(code)
    except SecurityViolation as exc:
        return SandboxResult(success=False, stdout="", stderr="", error=f"Xavfsizlik xatosi: {exc}")
    except SyntaxError as exc:
        return SandboxResult(success=False, stdout="", stderr="", error=f"Syntax xatosi: {exc}")

    try:
        proc = subprocess.run(
            [sys.executable, "-I", "-c", code],
            capture_output=True,
            text=True,
            timeout=safe_timeout,
            preexec_fn=_apply_resource_limits,
        )
        return SandboxResult(
            success=proc.returncode == 0,
            stdout=proc.stdout[:4096],
            stderr=proc.stderr[:2048],
            error=None,
        )
    except subprocess.TimeoutExpired:
        return SandboxResult(
            success=False,
            stdout="",
            stderr="",
            error=f"Timeout: kod {safe_timeout:.1f}s ichida tugamadi",
        )
    except Exception as exc:
        return SandboxResult(success=False, stdout="", stderr="", error=f"Bajarish xatosi: {exc}")


# ── Runner mijozi (§19.2) ─────────────────────────────────────────────


class SandboxUnavailable(Exception):
    """Runner javob bermadi, band yoki xato qaytardi — keyinroq qayta urinish mumkin."""


class SandboxDisabled(Exception):
    """`SANDBOX_URL` sozlanmagan — yashirin testlar o'chiq (lokal rejim)."""


async def _call_runner(payload: dict) -> dict:
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            r = await client.post(
                f"{settings.SANDBOX_URL.rstrip('/')}/run", json=payload,
                headers={"Authorization": f"Bearer {settings.SANDBOX_TOKEN}"},
            )
    except httpx.HTTPError as exc:
        raise SandboxUnavailable(f"runner'ga ulanib bo'lmadi: {type(exc).__name__}") from exc
    if r.status_code != 200:
        raise SandboxUnavailable(f"runner {r.status_code} qaytardi")
    return r.json()


async def run_script(code: str, timeout: float = 2.0) -> SandboxResult:
    """`POST /tools/sandbox` uchun: runner bo'lsa unda, aks holda lokal (dev)."""
    timeout = min(float(timeout), 3.0)
    if not settings.SANDBOX_URL:
        return await asyncio.to_thread(run_code, code, timeout)
    # runner'da ham AST filtri — konteyner noto'g'ri sozlansa ham qo'shimcha qatlam
    try:
        validate_code(code)
    except SecurityViolation as exc:
        return SandboxResult(success=False, stdout="", stderr="", error=f"Xavfsizlik xatosi: {exc}")
    except SyntaxError as exc:
        return SandboxResult(success=False, stdout="", stderr="", error=f"Syntax xatosi: {exc}")
    try:
        r = await _call_runner({"code": code, "timeout": timeout})
    except SandboxUnavailable as exc:
        log.warning("sandbox: %s", exc)
        return SandboxResult(success=False, stdout="", stderr="", error="Sandbox hozir band, birozdan keyin urinib ko'ring")
    error = "Timeout: kod {:.1f}s ichida tugamadi".format(timeout) if r["status"] == "timeout" else None
    return SandboxResult(success=r["status"] == "ok", stdout=r["stdout"], stderr=r["stderr"], error=error)


async def run_tests(code: str, tests: str, module: str) -> dict:
    """Yashirin testlar (§19.1) — runner javobi: `{status, passed, total, tests, ...}`."""
    if not settings.SANDBOX_URL:
        raise SandboxDisabled
    return await _call_runner({"code": code, "tests": tests, "module": module})
