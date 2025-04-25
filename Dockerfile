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

# Create necessary directories and symbolic links
RUN mkdir -p /app/config /app/data && \
    ln -s /app/config /config && \
    ln -s /app/data /data

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Define volumes
VOLUME ["/data", "/config"]

# Run the application
CMD ["python", "main.py"] 