FROM python:3.11-slim

WORKDIR /app

# 先に requirements.txt のみをコピーしてインストールすることでキャッシュを効率化
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# その後にソースコードをコピー
COPY . .

# コンテナ実行時のポート番号を 7000 に設定します
ENV PORT=7000
EXPOSE 7000

CMD ["python", "app.py"]