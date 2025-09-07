# Stage 1: Builder
FROM python:3.12 AS builder

WORKDIR /app

# Install compiler tools and essential build packages
RUN apt-get update && apt-get install -y \
    gcc g++ build-essential curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*
# python3-distutils has been removed from instalation 6/09/2025

# Pin setuptools to avoid pkgutil.ImpImporter error and preinstall numpy
RUN pip install --upgrade pip \
 && pip install --no-cache-dir "setuptools<69" "wheel" "Cython" \
 && pip install --no-build-isolation --no-cache-dir "numpy==1.26.4"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Final stage
FROM python:3.12-slim
WORKDIR /app

RUN apt-get update && apt-get install -y libgomp1 && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local /usr/local
COPY --from=builder /app /app
COPY models/ /app/models/

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8500"]