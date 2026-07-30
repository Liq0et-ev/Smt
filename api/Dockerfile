FROM python:3.12-slim

WORKDIR /app

# System deps needed to build cryptography/cffi (key-pair auth) from source
# on platforms without prebuilt wheels.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libffi-dev libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY common/ ./common/
COPY mongo/ ./mongo/
COPY analytics/ ./analytics/
COPY api/ ./api/

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
