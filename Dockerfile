# Use Python 3.10 as the base image
FROM python:3.10-slim

# Set the working directory inside the container
WORKDIR /app

# Install necessary dependencies for webrtcvad
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt to the working directory
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install whisper
RUN pip install "git+https://github.com/openai/whisper.git" 

# Copy the src folder to the working directory
COPY src .

# Expose the FastAPI port
EXPOSE 8083

# Run the FastAPI server using uvicorn
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8083", "--reload"]
