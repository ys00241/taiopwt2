FROM python:3.11-slim

WORKDIR /app

# ── System deps: git (for clone) + reportlab (for PDF) + CJK font ──
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev \
    fonts-wqy-zenhei \
    && rm -rf /var/lib/apt/lists/*

# ── Clone repo (no git history, no build context needed) ──
RUN git clone --depth 1 https://github.com/ys00241/taiopwt2.git /tmp/repo && \
    cp -r /tmp/repo/app ./app/ && \
    cp /tmp/repo/run.py /tmp/repo/config.py /tmp/repo/requirements.txt \
       /tmp/repo/docker-entrypoint.sh /tmp/repo/.env.example ./ && \
    rm -rf /tmp/repo

# ── Python deps ──
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ── Prepare dirs ──
RUN chmod +x docker-entrypoint.sh && \
    mkdir -p /app/data /app/uploads /app/csv_exports /app/uploads/items

EXPOSE 5000
ENV FLASK_ENV=production
ENTRYPOINT ["./docker-entrypoint.sh"]
