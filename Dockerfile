FROM python:3.9-slim

WORKDIR /app

# Install system dependencies for librosa and soundfile
RUN apt-get update && apt-get install -y \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all files, including static directory
COPY . .

# Ensure static directory exists
RUN mkdir -p /app/static /app/audio
COPY static/index.html /app/static/

# Expose port dynamically or default to 8000
EXPOSE ${PORT:-8000}

# Use environment variable for port
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]