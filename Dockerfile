# Use Python 3.9 slim image
FROM python:3.9-slim

# Install system dependencies for handwrite
RUN apt-get update && apt-get install -y \
    fontforge \
    python3-fontforge \
    potrace \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Create necessary directories
RUN mkdir -p uploads output_fonts

# Set environment variables
ENV FLASK_APP=app.py
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Expose port
EXPOSE 8080

# Set the command to run the application
CMD gunicorn --bind 0.0.0.0:$PORT app:app
