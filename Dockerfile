FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y postgresql-client netcat-openbsd && rm -rf /var/lib/apt/lists/*

COPY ./backend /app/backend
COPY ./wait-for-it.sh /app/backend

RUN chmod +x /app/backend/wait-for-it.sh

RUN pip install --no-cache-dir fastapi uvicorn sqlalchemy psycopg2-binary

EXPOSE 8080

CMD ["/app/backend/wait-for-it.sh", "db:5432", "--", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8080", "--reload"]