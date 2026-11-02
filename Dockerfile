# FuelMap Angola: dashboard (Dash) + REST API (FastAPI) in one image.
# The same command the Heroku Procfile runs: gunicorn serves app:server,
# which mounts the FastAPI app inside the Dash WSGI app.
#
# Build:  docker build -t fuelmap-angola .
# Run:    docker run --rm -p 8050:8050 fuelmap-angola
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8050

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8050/health', timeout=4)"

CMD ["gunicorn", "app:server", "--bind", "0.0.0.0:8050", "--workers", "2", "--timeout", "60"]
