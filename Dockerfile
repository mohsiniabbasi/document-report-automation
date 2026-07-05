# Pin to Debian 12 (bookworm): its Chromium is stable for headless PDF.
# (python:3.12-slim tracks Debian 13/trixie, whose newer Chromium crashes headless.)
FROM python:3.12-slim-bookworm

ENV CHROME_PATH=/usr/bin/chromium
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       chromium \
       fonts-liberation \
       libnss3 libatk-bridge2.0-0 libatk1.0-0 libcups2 libxkbcommon0 \
       libxcomposite1 libxdamage1 libxrandr2 libgbm1 libpango-1.0-0 libasound2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
