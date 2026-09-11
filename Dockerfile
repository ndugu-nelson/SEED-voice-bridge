# Hugging Face Spaces (Docker SDK) expects the app to listen on port 7860.
# This also runs fine on any other Docker host (Render, Fly.io, etc.) — most
# of them set $PORT for you, which gunicorn respects via the CMD below.
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=7860
EXPOSE 7860

CMD ["sh", "-c", "gunicorn -b 0.0.0.0:${PORT:-7860} app:app"]
