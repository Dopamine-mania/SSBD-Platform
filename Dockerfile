# 声匠录音棚排班与计费桌面平台 - Docker 镜像
FROM python:3.10-slim

# 安装系统依赖（Qt 运行时库）
# 使用 Debian Bookworm 兼容的包名
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libxcb-xinerama0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-shape0 \
    libxkbcommon-x11-0 \
    libdbus-1-3 \
    libxcb-cursor0 \
    libxcb-xfixes0 \
    libfontconfig1 \
    libfreetype6 \
    libx11-6 \
    libx11-xcb1 \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 初始化数据库
RUN python3 init_db.py && python3 init_sample_data.py

# 暴露端口（虽然是桌面应用，但为未来 Web 版预留）
EXPOSE 8000

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV QT_QPA_PLATFORM=offscreen

# 启动命令
CMD ["python3", "app.py"]
