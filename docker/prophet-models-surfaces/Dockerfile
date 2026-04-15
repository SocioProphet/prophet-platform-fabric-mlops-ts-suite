FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy the Prophet Time Series SDK into the image
COPY sdk/prophet_ts /app/prophet_ts
ENV PYTHONPATH=/app

COPY train /app/train
ENV PYTHONUNBUFFERED=1

# Usage:
#   python -m train.main --spec /path/to/spec.yaml --out /app/out
CMD ["python", "-m", "train.main", "--help"]
