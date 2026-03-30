# テストアプリ (Mark-2)

Flask、PostgreSQL、Dockerを使用したシンプルなデータ管理アプリケーションです。

## 主な機能
- **検索機能**: 名前およびメモからのキーワード検索。
- **データ管理**: データの追加、編集、削除（画像ファイルの物理削除対応）。
- **イメージ管理**: 写真を1枚登録・表示可能。
- **レスポンシブ対応**: PCおよびスマートフォンからの利用に最適化。

## 技術スタック
- **Backend**: Python 3.11 (Flask)
- **Frontend**: Jinja2, CSS (Responsive)
- **Database**: PostgreSQL
- **Infrastructure**: Docker / Docker Compose (WSL2)

## セットアップ

### 1. データベースの準備
ホストマシンのPostgreSQLに以下のテーブルを作成してください。

```sql
CREATE TABLE IF NOT EXISTS sample (
  no SERIAL PRIMARY KEY,
  name TEXT,
  memo TEXT,
  image_filename VARCHAR(255)
);
```

### 2. アプリの起動
プロジェクトのルートディレクトリに `.env` ファイルを作成し、データベース接続情報を記述してください。

```text
DATABASE_URL=postgresql://ユーザー名:パスワード@ホスト:ポート/DB名?client_encoding=utf8
```

その後、以下のコマンドを実行します。

```bash
docker compose up --build
```

## 注意事項
- `docker-compose.yml` 内の `DATABASE_URL` にはデータベースの接続パスワードが含まれています。GitHubに公開リポジトリとして作成する場合は、パスワードの取り扱いに注意してください（`.env` ファイルへの移行を推奨します）。
