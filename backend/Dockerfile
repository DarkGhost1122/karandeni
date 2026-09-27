FROM python:3.11-slim

WORKDIR /app

# System deps (kept minimal; bcrypt/pymongo build fine without extra libs on slim)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Hugging Face Spaces routes traffic to port 7860 by default
ENV PORT=7860
EXPOSE 7860

CMD ["python", "app.py"]
