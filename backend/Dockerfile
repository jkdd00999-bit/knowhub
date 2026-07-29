# 后端 Dockerfile
FROM python:3.10-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制代码
COPY . .

# 创建数据目录
RUN mkdir -p documents vector_db chroma_db data

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# 注意：不使用非 root 用户，因为 docker-compose bind mount 目录
# 由宿主机 root 创建，appuser 无法写入。如需更高安全性，
# 可改用 named volumes 并取消注释以下两行：
# RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser
# USER appuser

# 启动命令
CMD ["uvicorn", "FastAPI:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
