FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    fontforge \
    python3-fontforge \
    potrace \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create necessary directories
RUN mkdir -p uploads output_fonts

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Run gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]
