FROM python:3.12

WORKDIR /app

# Install compiler tools and essential build packages
RUN apt-get update && apt-get install -y \
    gcc g++ build-essential python3-distutils curl
    # gcc g++ build-essential python3-pip python3-setuptools python3-wheel python3-pkg-resources python3-distutils \
 #&& pip install --upgrade pip setuptools wheel

# Pin setuptools to avoid pkgutil.ImpImporter error and preinstall numpy
RUN pip install --upgrade pip \
 && pip install --no-cache-dir "setuptools<69" "wheel" "Cython" \
 && pip install --no-build-isolation --no-cache-dir "numpy==1.26.4"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8500"]