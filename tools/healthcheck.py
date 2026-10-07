#!/usr/bin/env python3
"""
Docker healthcheck (CONTRACT.md §18.1): backend jonli — DB va Redis ishlaydi.

Worker holati bu yerda hisobga olinmaydi: worker o'lsa sayt ochiq qolsin,
`/api/v1/health` (503) tashqi monitorda ko'rinadi. Faqat stdlib.
"""
import json
import sys
import urllib.error
import urllib.request

URL = "http://127.0.0.1:8000/api/v1/health"


def main() -> int:
    try:
        body = urllib.request.urlopen(URL, timeout=3).read()
    except urllib.error.HTTPError as exc:   # 503 — tanasi baribir bor
        body = exc.read()
    except OSError:
        return 1
    try:
        state = json.loads(body)
    except ValueError:
        return 1
    return 0 if state.get("db") and state.get("redis") else 1


if __name__ == "__main__":
    sys.exit(main())
