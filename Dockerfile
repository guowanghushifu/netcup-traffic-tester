FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装Python包
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY netcup_traffic_tester.py .

# 设置环境变量默认值（只保留必要的）
ENV TZ=Asia/Shanghai

# 暴露端口
EXPOSE 51000

# 设置启动命令
CMD ["python3", "netcup_traffic_tester.py"] 