FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖（OpenCV、编译工具）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 默认环境变量（docker-compose 可覆盖）
ENV API_SERVER_HOST=0.0.0.0
ENV API_SERVER_PORT=8000

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
