FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render 通过 $PORT 注入端口号，开发环境默认 8000
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
