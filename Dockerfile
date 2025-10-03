FROM python:3.9-slim-bullseye

# Установка FFmpeg с поддержкой H.264
RUN apt-get update && apt-get install -y \
    python3-opencv \
    libopencv-dev \
    ffmpeg \
    x264 \
    libx264-dev \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgl1-mesa-glx \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY static/ ./static/

RUN mkdir -p /app/temp_uploads

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]