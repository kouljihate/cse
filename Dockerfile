FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir --retries 5 --timeout 120 -r requirements.txt

# Application code, plus the requests folder used by the request feature
COPY backend ./backend
COPY requests ./requests

WORKDIR /app/backend

# Keep in sync with VERSION in backend/config.py
ARG APP_VERSION=2.0.1
LABEL org.opencontainers.image.title="Document Manager" \
      org.opencontainers.image.version="${APP_VERSION}"

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/api/health', timeout=4)"

CMD ["python", "run.py", "--host", "0.0.0.0"]
