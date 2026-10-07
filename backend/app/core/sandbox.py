"""
sandbox.py — AST-asosida Python kodi xavfsizlik filtri + subprocess bajarish.

Xavfsizlik yondashuvi:
1. AST parse qilib, taqiqlangan modullar/funksiyalar/atributlarni topadi.
2. Hech qanday xavfli narsa topilmasa — python -I -c orqali subprocess'da bajaradi.
3. Timeout serverd tomonidan qattiq cheklanadi (client qiymatiga ishonilmaydi).
"""

import ast
import subprocess
import sys
from typing import NamedTuple

# Taqiqlangan modul nomlari (import va from...import)
BANNED_MODULES = {
    "os",
    "sys",
    "subprocess",
    "shutil",
    "socket",
    "http",
    "requests",
    "urllib",
    "ctypes",
    "pathlib",
    "builtins",   # ko'plik — 'builtin' emas!
    "importlib",
    "posix",
}

# Taqiqlangan funksiya/call nomlari
BANNED_CALLS = {
    "eval",
    "exec",
    "open",
    "compile",
    "__import__",
    "globals",
    "locals",
    "getattr",
    "setattr",
    "delattr",
    "breakpoint",
}

# Taqiqlangan atribut nomlari (. orqali kirish)
BANNED_ATTRS = {
    "__class__",
    "__subclasses__",
    "__bases__",
    "__base__",
    "__globals__",
    "__builtins__",
    "__code__",
    "__closure__",
    "__dict__",
    "__mro__",
}


class SecurityViolation(Exception):
    """AST tekshiruvida xavfli narsa topilganda."""
    pass


class _Visitor(ast.NodeVisitor):
    """AST bo'ylab yuruvchi — qoidabuzarliklarni aniqlab, SecurityViolation ko'taradi."""

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
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        # Oddiy funksiya chaqiruvi: eval(...), exec(...)
        if isinstance(node.func, ast.Name):
            if node.func.id in BANNED_CALLS:
                raise SecurityViolation(f"Taqiqlangan funksiya: '{node.func.id}'")
        # Metod chaqiruvi: obj.getattr(...)
        if isinstance(node.func, ast.Attribute):
            if node.func.attr in BANNED_CALLS:
                raise SecurityViolation(f"Taqiqlangan funksiya (metod): '{node.func.attr}'")
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        if node.attr in BANNED_ATTRS:
            raise SecurityViolation(f"Taqiqlangan atribut: '{node.attr}'")
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


def run_code(code: str, timeout: float = 2.0) -> SandboxResult:
    """
    Kodni xavfsiz muhitda bajaradi:
    1. AST validatsiya
    2. subprocess'da python -I (izolyatsiya rejimi) bilan bajarish
    3. Timeout cheklovi (serverd tomonidan, client emas)

    :param code: Bajariladigan Python kodi
    :param timeout: Maksimal bajarish vaqti (sekund) — MAX 3.0s
    :returns: SandboxResult
    """
    # Server tomonidan qattiq cheklov — client timeout_seconds'ga ishonilmaydi
    safe_timeout = min(float(timeout), 3.0)

    # 1-qadam: AST tekshiruvi
    try:
        validate_code(code)
    except SecurityViolation as exc:
        return SandboxResult(success=False, stdout="", stderr="", error=f"Xavfsizlik xatosi: {exc}")
    except SyntaxError as exc:
        return SandboxResult(success=False, stdout="", stderr="", error=f"Syntax xatosi: {exc}")

    # 2-qadam: subprocess bajarish
    # python -I: izolated mode — site-packages, PYTHONPATH, user site yo'q
    try:
        proc = subprocess.run(
            [sys.executable, "-I", "-c", code],
            capture_output=True,
            text=True,
            timeout=safe_timeout,
        )
        return SandboxResult(
            success=proc.returncode == 0,
            stdout=proc.stdout[:4096],   # stdout'ni kesib chiqish
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
