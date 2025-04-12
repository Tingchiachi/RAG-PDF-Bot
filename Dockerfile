# 使用輕量級 Python 基底映像
FROM python:3.10-slim

# 設定工作目錄
WORKDIR /app

# 複製所有專案檔案到容器
COPY . .

# 安裝依賴套件
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# 設定環境變數（可選）
ENV PYTHONUNBUFFERED=1

# 預設啟動 Flask 應用
CMD ["python", "app.py"]
