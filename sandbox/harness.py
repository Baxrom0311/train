"""
Test harness (CONTRACT.md §19.1) — runner ichida, talaba kodi bilan bitta jarayonda.

`python -I harness.py <tests_module>`: stdin'dan nonce o'qiladi (talaba kodi
import qilinishidan oldin), keyin testlar moduli import qilinadi va `test_*`
funksiyalari e'lon tartibida chaqiriladi. Natija oxirgi satrda:
`<nonce> {"passed":…}` — oddiy `print` bilan soxtalashtirib bo'lmaydi.
"""
import json
import sys
import traceback

MESSAGE_MAX = 300


def _message(exc: BaseException) -> str:
    text = str(exc) or type(exc).__name__
    if isinstance(exc, AssertionError) and not str(exc):
        # assert qatorining o'zi — qaysi tekshiruv yiqilganini ko'rsatadi
        tb = traceback.extract_tb(exc.__traceback__)
        text = f"AssertionError: {tb[-1].line}" if tb and tb[-1].line else "AssertionError"
    elif not isinstance(exc, AssertionError):
        text = f"{type(exc).__name__}: {text}"
    return text[:MESSAGE_MAX]


def main() -> None:
    nonce = sys.stdin.readline().strip()
    sys.path.insert(0, ".")   # -I ish papkasini sys.path'ga qo'shmaydi
    results = []
    status = "ok"
    try:
        module = __import__(sys.argv[1])
    except BaseException as exc:  # noqa: BLE001 — talaba kodi import paytida yiqildi
        status, module = "error", None
        sys.stderr.write(traceback.format_exc()[-2000:])
        results.append({"name": "import", "ok": False, "message": _message(exc)})
    if module is not None:
        tests = [(n, f) for n, f in vars(module).items() if n.startswith("test_") and callable(f)]
        for name, fn in tests:
            try:
                fn()
                results.append({"name": name, "ok": True, "message": ""})
            except BaseException as exc:  # noqa: BLE001 — SystemExit ham testning yiqilishi
                results.append({"name": name, "ok": False, "message": _message(exc)})
    sys.stdout.flush()
    sys.stdout.write(f"\n{nonce} " + json.dumps({"status": status, "tests": results}) + "\n")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
