FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p data/photos
EXPOSE 8000
ENV PORT=8000
CMD ["sh", "-c", "uvicorn parkguard.main:app --host 0.0.0.0 --port ${PORT}"]
