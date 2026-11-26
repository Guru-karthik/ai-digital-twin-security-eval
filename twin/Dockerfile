# Agent HTTP API (server.py). Build context is ./twin. Personal documents are NOT copied in; mount them at runtime.
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get -y upgrade && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements-server.txt .
RUN pip install -r requirements-server.txt
COPY . .
RUN useradd --system --uid 10001 twin
USER twin
EXPOSE 7861
HEALTHCHECK --interval=30s CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:7861/health').status==200 else 1)"
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "7861"]
