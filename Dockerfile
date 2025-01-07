# Use Python 3.9 as base image (not slim version)
FROM python:3.9

# Install system dependencies
RUN apt-get update && apt-get install -y \
    fontforge \
    python3-fontforge \
    potrace \
    build-essential \
    python3-dev \
    pkg-config \
    libfreetype6-dev \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Set environment variable for Fontforge
ENV FONTFORGE_LANGUAGE=py
ENV PYTHONPATH=/usr/local/lib/python3/dist-packages

# Set working directory
WORKDIR /app

# Install Python packages individually to ensure proper installation
RUN pip install --no-cache-dir Pillow==9.5.0 \
    && pip install --no-cache-dir fontforge \
    && pip install --no-cache-dir numpy \
    && pip install --no-cache-dir handwrite==0.3.0

# Copy requirements and install remaining Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Create necessary directories with proper permissions
RUN mkdir -p uploads output_fonts && \
    chmod 777 uploads output_fonts

# Set environment variables
ENV FLASK_APP=app.py
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Expose port
EXPOSE 8080
