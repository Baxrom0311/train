# TryJob sandbox runner (CONTRACT.md §19.1) — faqat stdlib, talaba kodini bajaradi.
# Build context — repo root:  docker build -f deploy/sandbox.Dockerfile .
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Talaba kodi ko'pincha `import pytest` qiladi (o'z testlari bilan) — runner'ning o'zi stdlib
RUN pip install --no-cache-dir "pytest==8.*"

WORKDIR /srv/sandbox
COPY sandbox/runner.py sandbox/harness.py ./

# Root emas; uy papkasi yo'q — yozish faqat /tmp (tmpfs) ga
RUN useradd --system --uid 10002 --no-create-home runner
USER runner

EXPOSE 8100
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8100/health', timeout=2)"

CMD ["python", "-I", "runner.py"]
