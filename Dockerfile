FROM python:3.9-slim

# Install system dependencies (expanded list)
RUN apt-get update && apt-get install -y \
    fontforge \
    python3-fontforge \
    potrace \
    build-essential \
    python3-dev \
    pkg-config \
    libfreetype6-dev \
    libfontconfig1-dev \
    libjpeg-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

# Set Fontforge environment variables
ENV FONTFORGE_LANGUAGE=py
ENV LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH

# Set working directory
WORKDIR /app

# Install Python packages in stages
COPY requirements.txt .
RUN pip install --no-cache-dir pillow numpy
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Create directories and set permissions
RUN mkdir -p uploads output_fonts && \
    chmod 777 uploads output_fonts && \
    chmod -R 777 /usr/local/lib/python3.9/site-packages/fontforge

# Set environment variables
ENV FLASK_APP=app.py
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
ENV PYTHONPATH=/usr/local/lib/python3.9/site-packages

# Expose port
EXPOSE 8080
