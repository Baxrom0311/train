import io
import sys
import ast
import time
import subprocess
from typing import Dict, Any

# Xavfli modullar va buyruqlarni taqiqlash (Sandbox Security)
BANNED_MODULES = {
    "os", "sys", "subprocess", "shutil", "socket", "http", "requests", 
    "urllib", "ctypes", "pathlib", "builtin", "importlib", "posix"
}
BANNED_CALLS = {
    "eval", "exec", "open", "compile", "__import__", "globals", "locals",
    "getattr", "setattr", "delattr", "breakpoint"
}
BANNED_ATTRS = {
    "__class__", "__subclasses__", "__bases__", "__base__", 
    "__globals__", "__builtins__", "__code__", "__closure__", 
    "__dict__", "__mro__"
}

class SafePythonSandbox:
    """
    Talaba Python kodini xavfsiz, AST orqali tekshirilgan muhitda sinab ko'rish dvigateli.
    """
    @classmethod
    def audit_ast(cls, code_str: str) -> tuple[bool, str]:
        if not code_str or not code_str.strip():
            return False, "Kod kiritilmagan (bo'sh)."

        # Matnli hisobotmi yoki kodmi aniqlash
        is_likely_code = any(k in code_str for k in ["def ", "import ", "print(", "=", "class ", "return ", "if ", "for ", "while "])

        try:
            tree = ast.parse(code_str)
        except SyntaxError as e:
            if not is_likely_code:
                return False, (
                    "ℹ️ Bu maydonga dasturlash kodi emas, balki biznes/moliya hisoboti kiritilgan.\n"
                    "👉 Uni baholash uchun pastdagi 'AI Mentordan Baho Olish' tugmasini bosing!"
                )
            return False, f"Sintaksis xatosi: qator {e.lineno}, {e.msg}"
        except Exception as e:
            return False, f"Kod parse qilinmadi: {str(e)}"

        for node in ast.walk(tree):
            # 1. Importlarni tekshirish
            if isinstance(node, ast.Import):
                for n in node.names:
                    root_mod = n.name.split('.')[0]
                    if root_mod in BANNED_MODULES:
                        return False, f"Xavfsizlik qoidasi: '{root_mod}' kutubxonasini import qilish taqiqlangan!"
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.split('.')[0] in BANNED_MODULES:
                    return False, f"Xavfsizlik qoidasi: '{node.module}' kutubxonasidan foydalanish taqiqlangan!"
            
            # 2. Xavfli funksiya chaqiruvlari
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in BANNED_CALLS:
                    return False, f"Xavfsizlik qoidasi: '{node.func.id}()' funksiyasini chaqirish taqiqlangan!"
                elif isinstance(node.func, ast.Attribute) and node.func.attr in BANNED_CALLS:
                    return False, f"Xavfsizlik qoidasi: '{node.func.attr}()' funksiyasini chaqirish taqiqlangan!"

            # 3. Dunder va xavfli obyekt xususiyatlariga murojaatni bloklash
            elif isinstance(node, ast.Attribute):
                if node.attr in BANNED_ATTRS:
                    return False, f"Xavfsizlik qoidasi: '{node.attr}' xususiyatiga murojaat qilish taqiqlangan!"

        return True, ""

    @classmethod
    def execute_code(cls, code_str: str, timeout_sec: float = 2.0) -> Dict[str, Any]:
        is_safe, error_msg = cls.audit_ast(code_str)
        if not is_safe:
            return {
                "success": False,
                "status": "error",
                "output": "",
                "error": error_msg,
                "execution_time_ms": 0.0
            }

        start_time = time.time()
        try:
            res = subprocess.run(
                [sys.executable, "-I", "-c", code_str],
                capture_output=True,
                text=True,
                timeout=timeout_sec
            )
            elapsed_ms = round((time.time() - start_time) * 1000, 2)
            stdout = res.stdout or ""
            stderr = res.stderr or ""

            if res.returncode != 0:
                # Syntax yoki runtime xatolik
                return {
                    "success": False,
                    "status": "error",
                    "output": stdout,
                    "error": stderr.strip() or f"Jarayon xatolik bilan yakunlandi (kod: {res.returncode})",
                    "execution_time_ms": elapsed_ms
                }

            return {
                "success": True,
                "status": "success",
                "output": stdout or "(Natija muvaffaqiyatli bajarildi, lekin hech narsa chop etilmadi)",
                "error": None,
                "execution_time_ms": elapsed_ms
            }
        except subprocess.TimeoutExpired:
            elapsed_ms = round((time.time() - start_time) * 1000, 2)
            return {
                "success": False,
                "status": "error",
                "output": "",
                "error": f"Vaqt limiti tugadi: Kod {timeout_sec} soniya ichida yakunlanmadi (Timeout).",
                "execution_time_ms": elapsed_ms
            }
        except Exception as e:
            elapsed_ms = round((time.time() - start_time) * 1000, 2)
            return {
                "success": False,
                "status": "error",
                "output": "",
                "error": f"{type(e).__name__}: {str(e)}",
                "execution_time_ms": elapsed_ms
            }
