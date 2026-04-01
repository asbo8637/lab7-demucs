FROM python:3.10-slim

RUN pip install flask redis jsonpickle minio

WORKDIR /app
COPY rest-server.py /app/rest-server.py

EXPOSE 5000

CMD ["python", "rest-server.py"]
