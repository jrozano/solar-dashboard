FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config/        config/
COPY domain/        domain/
COPY infrastructure/ infrastructure/
COPY backend/       backend/
COPY frontend/      frontend/
COPY tests/         tests/
COPY app.py         .

# Run security tests as part of build
RUN PYTHONPATH=. python -m pytest tests/ -v --tb=short

EXPOSE 5000

CMD ["python", "app.py"]
