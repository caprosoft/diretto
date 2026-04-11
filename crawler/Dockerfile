FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libxml2 libxslt1.1 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir httpx[http2] beautifulsoup4 lxml \
    apscheduler asyncpg pyyaml python-dateutil

COPY . .

CMD ["python", "-c", "from crawler.main import run_loop; import asyncio; asyncio.run(run_loop())"]
