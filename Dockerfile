FROM python:3.9-slim

# Install system dependencies and Python development tools
RUN apt-get update && apt-get install -y \
    fontforge \
    python3-fontforge \
    potrace \
    build-essential \
    python3-dev \
    pkg-config \
    libgl1-mesa-glx \
    libglib2.0-0 \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set environment variable for Fontforge
ENV FONTFORGE_LANGUAGE=py

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install handwrite package directly from GitHub
RUN pip install git+https://github.com/cod-ed/handwrite.git

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

# Command to run the application
CMD gunicorn --bind 0.0.0.0:8080 app:app
