# ---------- build stage (build wheels once) ----------
    FROM python:3.12-slim AS builder
    WORKDIR /app
    COPY requirements.txt .
    RUN pip install --upgrade pip && \
        pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt
    
    # ---------- runtime stage (scrapyd) ----------
    FROM python:3.12-slim AS runtime
    WORKDIR /app
    
    # OS deps for Chromium + tini (PID 1)
    RUN apt-get update && apt-get install -y --no-install-recommends \
            wget gnupg tini libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
            libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 \
            libxrandr2 libgbm1 libasound2 libpangocairo-1.0-0 libpangoft2-1.0-0 \
            libatspi2.0-0 libgtk-3-0 && \
        rm -rf /var/lib/apt/lists/*
    
    COPY --from=builder /wheels /wheels
    RUN pip install --no-cache /wheels/* && \
        playwright install --with-deps chromium
    
    # Copy project AFTER deps so Docker layer cache works mejor
    COPY . .
    
    # Instala el paquete (no editable) → imports siempre funcionan
    RUN pip install --no-cache-dir .
    
    ENV PYTHONUNBUFFERED=1
    ENTRYPOINT ["/usr/bin/tini", "--"]
    CMD ["scrapyd"]
    
    # ---------- tester stage (pytest/ruff/mypy) ----------
    FROM python:3.12-slim AS tester
    WORKDIR /app
    
    RUN apt-get update && apt-get install -y --no-install-recommends \
            wget gnupg tini libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
            libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 \
            libxrandr2 libgbm1 libasound2 libpangocairo-1.0-0 libpangoft2-1.0-0 \
            libatspi2.0-0 libgtk-3-0 && \
        rm -rf /var/lib/apt/lists/*
    
    COPY --from=builder /wheels /wheels
    RUN pip install --no-cache /wheels/*
    
    # Dev deps
    COPY requirements-dev.txt .
    RUN pip install -r requirements-dev.txt && \
        playwright install --with-deps chromium
    
    # Copiamos el código y lo instalamos en modo editable para iterar rápido
    COPY . .
    RUN pip install -e .
    
    ENV PYTHONUNBUFFERED=1
    # No CMD fijo; docker-compose lo define
    