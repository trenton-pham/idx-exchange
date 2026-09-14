FROM python:3.13-slim
WORKDIR /app
COPY requirements-production.lock.txt .
RUN pip install --no-cache-dir -r requirements-production.lock.txt
COPY backend backend
COPY clean.py extract_crmls.py feature_engineer.py outlier.py mortgage_fetch.py ./
ENV PYTHONUNBUFFERED=1 DB_SSLROOTCERT=/app/backend/rds-ca.pem
USER 65534:65534
ENTRYPOINT ["python", "-m"]
CMD ["backend.ingest"]
