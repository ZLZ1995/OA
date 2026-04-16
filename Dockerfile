FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATABASE_URL=sqlite:////data/app.db \
    DB_INIT_REQUIRED=true

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY . /app
RUN chmod +x /app/start && mkdir -p /data

VOLUME ["/data"]

EXPOSE 8080
CMD ["sh", "./start"]
