FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Avvalgi dependency conflict xatosi chiqmasligi uchun:
RUN pip install --no-cache-dir -r requirements.txt --use-deprecated=legacy-resolver

COPY . .

ENV PYTHONUNBUFFERED=1

# BU YERNI O'ZGARTIRDIK:
CMD sh -c "python manage.py makemigrations apps && python manage.py migrate --noinput && python manage.py collectstatic --noinput && python manage.py runserver 0.0.0.0:8000"