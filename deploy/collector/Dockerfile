FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 TZ=Asia/Ho_Chi_Minh
WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir httpx websockets pandas numpy python-dotenv jinja2 tzdata \
    && pip install --no-cache-dir --no-deps . \
    && useradd --uid 10001 --create-home collector \
    && mkdir -p /data && chown collector:collector /data
USER 10001:10001
ENV NEOPULSE_MODE=live NEOPULSE_SOURCE=ssi NEOPULSE_DB_PATH=/data/neopulse.sqlite
CMD ["python", "-m", "neopulse.analytics.cloud_recorder"]
