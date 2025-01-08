FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    handwrite \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create necessary directories
RUN mkdir -p uploads output_fonts

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV PORT=8080

# Run gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]

# .gitignore
__pycache__/
*.py[cod]
*$py.class
venv/
.env
.env.local
uploads/
output_fonts/
*.log
serviceAccountKey.json
.DS_Store
