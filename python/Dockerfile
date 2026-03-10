FROM python:3.10

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy project
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# HuggingFace Spaces runs on port 7860
EXPOSE 7860

# Start server
CMD ["gunicorn", "api_server.app:app", "--bind", "0.0.0.0:7860", "--workers", "1", "--threads", "2"]