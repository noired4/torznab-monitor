# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/data /app/config

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Define volumes
VOLUME ["/app/data", "/app/config"]

# Run the application
CMD ["python", "main.py"] 