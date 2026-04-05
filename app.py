import os
import logging
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# .envファイルがある場合、環境変数を読み込む
load_dotenv()

app = Flask(__name__)

# 画像の保存先設定
UPLOAD_FOLDER = Path('static/uploads')
app.config['UPLOAD_FOLDER'] = str(UPLOAD_FOLDER)

# アップロードを許可する拡張子の定義
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 環境変数 DATABASE_URL があればそれを使用し、なければローカルの 127.0.0.1 を使用します
raw_db_url = os.environ.get('DATABASE_URL', 'postgresql://postgres:igaki@127.0.0.1:5432/igaki').strip()

# URLに client_encoding が明示されていない場合のみ、デフォルトの utf8 を追加
if 'client_encoding' not in raw_db_url and 'postgresql' in raw_db_url:
    separator = '&' if '?' in raw_db_url else '?'
    raw_db_url = f"{raw_db_url}{separator}client_encoding=utf8"

app.config['SQLALCHEMY_DATABASE_URI'] = raw_db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "pool_pre_ping": True,  # 接続切れを自動検知して再接続する
}
app.config['SQLALCHEMY_ECHO'] = True  # 発行されるSQLクエリをコンソールに表示します

# アクセスログのレベルを調整（デバッグを容易にするため）
logging.basicConfig(level=logging.INFO)

# 起動時に接続先を表示（デバッグ用）
masked_url = app.config['SQLALCHEMY_DATABASE_URI'].split('@')[-1] if '@' in app.config['SQLALCHEMY_DATABASE_URI'] else app.config['SQLALCHEMY_DATABASE_URI']
app.logger.info(f"Connecting to database at: {masked_url}")

db = SQLAlchemy(app)

# 検索対象となるテーブルのモデル定義
class Item(db.Model):
    __tablename__ = 'sample' # テーブル名を 'sample' に変更
    no = db.Column(db.Integer, primary_key=True) # 'id' を 'no' に変更
    name = db.Column(db.String(100), nullable=False)
    memo = db.Column(db.Text) # 'description' を 'memo' に変更
    image_filename = db.Column(db.String(255)) # 画像ファイル名保存用

# アプリ起動時にアップロードフォルダを作成
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

@app.before_request
def log_request_info():
    """全リクエストのアクセス元IPをログ出力する（接続確認用）"""
    app.logger.info(f"Incoming request from: {request.remote_addr} to {request.path}")

def save_image(file):
    """画像を保存し、ファイル名を返すヘルパー関数"""
    if file and file.filename != '' and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        save_path = UPLOAD_FOLDER / filename
        file.save(str(save_path))
        return filename
    return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search')
def search():
    query_param = request.args.get('q', '')
    results = []
    error_message = None
    if query_param:
        try:
            # 名前またはメモのいずれかにキーワードが含まれるものを検索（強化版）
            stmt = db.select(Item).filter(
                or_(
                    Item.name.ilike(f'%{query_param}%'),
                    Item.memo.ilike(f'%{query_param}%')
                )
            )
            results = db.session.execute(stmt).scalars().all()
            app.logger.info(f"Search query: {query_param}, Found: {len(results)} items")
        except Exception as e:
            # 文字コードエラーを避けるため、エラー内容を安全に文字列化して出力
            error_detail = str(e).encode('utf-8', 'replace').decode('utf-8')
            app.logger.error(f"Database connection error: {error_detail}")
            error_message = f"データベース接続エラーが発生しました。詳細はログを確認してください。"
    return render_template('search.html', q=query_param, results=results, error_message=error_message)

@app.route('/add', methods=['GET', 'POST'])
def add():
    error_message = None
    success_message = None
    if request.method == 'POST':
        name = request.form.get('name')
        memo = request.form.get('memo')
        if not name:
            error_message = "名前を入力してください"
        else:
            # 重複していた保存処理を削除し、共通関数のみを使用するように集約
            filename = save_image(request.files.get('image'))

            try:
                new_item = Item(name=name, memo=memo, image_filename=filename)
                db.session.add(new_item)
                db.session.commit()
                success_message = f"「{name}」を正常に追加しました"
                app.logger.info(f"Item added: {name}")
            except Exception as e:
                db.session.rollback()
                app.logger.exception("Failed to add item")
                error_message = f"データベースエラーが発生しました: {type(e).__name__}"
    return render_template('add.html', error_message=error_message, success_message=success_message)

@app.route('/all')
def all_items():
    error_message = None
    results = []
    try:
        # データベースから全レコードを取得（No順）
        results = db.session.execute(db.select(Item).order_by(Item.no)).scalars().all()
        app.logger.info(f"Total items retrieved: {len(results)}")
    except Exception as e:
        app.logger.exception("Failed to retrieve items")
        # 改行を含めてエラーを見やすくし、文字化け対策も継続
        error_detail = str(e).encode('utf-8', 'replace').decode('utf-8')
        error_message = f"データの取得に失敗しました。<br><small>{error_detail}</small>"
    return render_template('all_items.html', results=results, error_message=error_message)

@app.route('/edit/<int:no>', methods=['GET', 'POST'])
def edit_item(no):
    # SQLAlchemy 2.0 スタイルの推奨される取得方法
    item = db.session.get(Item, no)
    if not item:
        abort(404)

    error_message = None
    success_message = None
    if request.method == 'POST':
        item.name = request.form.get('name')
        item.memo = request.form.get('memo')
        
        filename = save_image(request.files.get('image'))
        if filename:
            # 古いイメージファイルが存在する場合は削除してストレージを節約する
            if item.image_filename:
                old_image_path = UPLOAD_FOLDER / item.image_filename
                try:
                    if old_image_path.exists():
                        old_image_path.unlink()
                except Exception as e:
                    app.logger.warning(f"Could not delete old image file: {e}")
            item.image_filename = filename

        if not item.name:
            error_message = "名前を入力してください"
        else:
            try:
                db.session.commit()
                success_message = "更新しました"
            except Exception as e:
                db.session.rollback()
                app.logger.exception(f"Failed to edit item {no}")
                error_message = "更新に失敗しました。"
    return render_template('edit.html', item=item, error_message=error_message, success_message=success_message)

@app.route('/delete/<int:no>', methods=['POST'])
def delete_item(no):
    item = db.session.get(Item, no)
    if item:
        # 追加：画像ファイルの物理削除
        if item.image_filename:
            image_path = UPLOAD_FOLDER / item.image_filename
            if image_path.exists():
                image_path.unlink()
        try:
            db.session.delete(item)
            db.session.commit()
            app.logger.info(f"Item deleted: {no}")
        except Exception as e:
            db.session.rollback()
    return redirect(url_for('all_items'))

if __name__ == '__main__':
    # 環境変数からポート番号を取得し、設定がない場合はデフォルトの 5000 を使用します
    port = int(os.environ.get('PORT', 5000))
    app.logger.info(f"Server is starting on http://0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port, debug=True)