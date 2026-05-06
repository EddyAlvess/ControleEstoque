FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY simulator.py .

ENV TERM=xterm-256color
ENV PYTHONUNBUFFERED=1

CMD ["python", "simulator.py"]
