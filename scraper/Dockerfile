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
# v2: optimized version with concurrency, rate limiting, dedup
COPY ./run_task_scraping_olx_vehicle_v2.py /app/run_task_scraping_olx_vehicle_v2.py
COPY ./brands_models.json /app/brands_models.json
# Shared utilities
COPY ./scraper_utils.py /app/scraper_utils.py
# New category scrapers (apartments + electronics) and their configs
COPY ./scrape_apartments.py /app/scrape_apartments.py
COPY ./scrape_apartments_config.json /app/scrape_apartments_config.json
COPY ./scrape_electronics.py /app/scrape_electronics.py
COPY ./scrape_electronics_config.json /app/scrape_electronics_config.json

CMD sh -c "\
  echo '🕒 Waiting for Django...'; \
  until curl -s http://django:8000/ > /dev/null; do \
    sleep 2; \
  done; \
  echo '✅ Django is up'; \
  while true; do \
    python /app/run_task_scraping_olx_vehicle_v2.py; \
    sleep 3600; \
  done"