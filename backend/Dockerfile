FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY manage.py .
COPY requirements.txt .
RUN apt-get update && apt-get install -y locales && \
    sed -i '/ru_RU.UTF-8/s/^# //g' /etc/locale.gen && \
    locale-gen
ENV LANG=ru_RU.UTF-8
ENV LANGUAGE=ru_RU:ru
ENV LC_ALL=ru_RU.UTF-8
RUN pip install --no-cache-dir -r requirements.txt
COPY car_marketplace/ car_marketplace/
COPY cars/ cars/
COPY run_task_lacetti_white.py .

# Ensure .env exists at correct path for Django
COPY car_marketplace/.env /app/car_marketplace/.env

# Fallback command (overridden by docker-compose)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]