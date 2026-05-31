FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir setuptools==65.5.0 wheel==0.38.4
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create memory directory
RUN mkdir -p /app/sid_memory

# Expose port
EXPOSE 8000

# Run the API
CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"]