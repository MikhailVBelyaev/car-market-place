FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY export_pg_to_parquet.py .

CMD ["python", "export_pg_to_parquet.py"]
