# Start from the official Python image
FROM python:3.10-slim

RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

RUN pip install demucs redis jsonpickle minio 'numpy<2'

WORKDIR /app
COPY worker.py /app/worker.py

CMD ["python", "worker.py"]
