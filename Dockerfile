FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY run.py config.py ./
COPY scripts/ ./scripts/
COPY docker-entrypoint.sh ./

RUN chmod +x docker-entrypoint.sh && mkdir -p /app/data /app/uploads /app/csv_exports /app/uploads/items

EXPOSE 5000

ENV FLASK_ENV=production

ENTRYPOINT ["./docker-entrypoint.sh"]
