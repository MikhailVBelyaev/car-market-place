FROM python:3.12-slim

WORKDIR /app

# Install pip packages and databricks-cli
RUN pip install --no-cache-dir databricks-cli

# Copy your shell script
COPY run_cron_pipeline.sh .

CMD ["sh", "run_cron_pipeline.sh"]
