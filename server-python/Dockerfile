# --- Banking Copilot API server ---
# Small, reproducible image for the FastAPI backend.
FROM python:3.12-slim

# Don't buffer stdout/stderr (logs show up immediately in `docker logs`),
# and don't write .pyc files into the image layer.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install deps first, as their own layer. This layer is cached and only
# rebuilds when requirements.txt changes -- code edits stay fast.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Now copy the application code.
COPY app ./app

# Document the port the server listens on (compose maps it to the host).
EXPOSE 8787

# Bind 0.0.0.0 (NOT 127.0.0.1) so the port is reachable from outside the
# container. Inside a container, 127.0.0.1 only means "this container".
CMD ["uvicorn", "app.http_server:app", "--host", "0.0.0.0", "--port", "8787"]
