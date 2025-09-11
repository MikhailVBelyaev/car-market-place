FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r /app/requirements.txt

RUN apt-get update && apt-get install -y locales && \
    sed -i '/ru_RU.UTF-8/s/^# //g' /etc/locale.gen && \
    locale-gen
ENV LANG=ru_RU.UTF-8
ENV LANGUAGE=ru_RU:ru
ENV LC_ALL=ru_RU.UTF-8

RUN apt-get update && apt-get install -y curl

# Copy scraper files
COPY ./selenium_fetch_phone.py /app/selenium_fetch_phone.py
COPY ./run_task_scraping_olx_vehicle.py /app/run_task_scraping_olx_vehicle.py
COPY ./brands_models.json /app/brands_models.json

CMD sh -c "\
  echo '🕒 Waiting for Django...'; \
  until curl -s http://django:8000/ > /dev/null; do \
    sleep 2; \
  done; \
  echo '✅ Django is up'; \
  while true; do \
    python /app/run_task_scraping_olx_vehicle.py; \
    sleep 3600; \
  done"