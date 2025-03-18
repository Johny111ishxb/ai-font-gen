FROM python:3.8-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    fontforge \
    potrace \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1

CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:${PORT}"]
