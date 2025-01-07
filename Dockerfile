FROM python:3.9-slim

# Install system dependencies and fontforge
RUN apt-get update && apt-get install -y \
    fontforge \
    python3-fontforge \
    potrace \
    imagemagick \
    libmagickwand-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install additional Python packages that handwrite might need
RUN pip install --no-cache-dir \
    numpy \
    pillow \
    opencv-python-headless

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Create necessary directories with proper permissions
RUN mkdir -p uploads output_fonts && \
    chmod 777 uploads output_fonts

# Configure ImageMagick policy to allow PDF operations
RUN if [ -f /etc/ImageMagick-6/policy.xml ]; then \
    sed -i 's/rights="none" pattern="PDF"/rights="read|write" pattern="PDF"/' /etc/ImageMagick-6/policy.xml; \
    fi

# Set environment variables
ENV FLASK_APP=app.py
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Expose port
EXPOSE 8080
