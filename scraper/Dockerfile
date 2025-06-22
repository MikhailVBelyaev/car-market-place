FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY ./backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

RUN apt-get update && apt-get install -y locales && \
    sed -i '/ru_RU.UTF-8/s/^# //g' /etc/locale.gen && \
    locale-gen
ENV LANG=ru_RU.UTF-8
ENV LANGUAGE=ru_RU:ru
ENV LC_ALL=ru_RU.UTF-8

RUN apt-get update && apt-get install -y curl

# Copy scraper + Django project
COPY ./scraper/run_task_lacetti_white.py /app/run_task_lacetti_white.py
COPY ./backend /app/backend

# Set env for Django
ENV DJANGO_SETTINGS_MODULE=car_marketplace.settings
ENV PYTHONPATH=/app/backend

CMD sh -c "\
  echo '🕒 Waiting for Django...'; \
  until curl -s http://django:8000/ > /dev/null; do \
    sleep 2; \
  done; \
  echo '✅ Django is up'; \
  while true; do \
    python /app/run_task_lacetti_white.py; \
    sleep 3600; \
  done"