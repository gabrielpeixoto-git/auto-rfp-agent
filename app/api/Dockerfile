FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for document processing
RUN apt-get update && apt-get install -y \
    poppler-utils \
    libreoffice \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Ensure main.py is the latest version (workaround for caching issues)
COPY src/main.py ./src/main.py

# Install Python dependencies
RUN pip install --no-cache-dir -e ".[dev]"

# Create upload directory
RUN mkdir -p /app/uploads

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
