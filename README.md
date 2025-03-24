# Google Calendar API Python Script

このスクリプトは、Google Calendar APIを使用してカレンダーにイベントを追加するためのPythonプログラムです。
RESTful APIとしても利用可能です。

## セットアップ

1. 必要なパッケージをインストールします：
```bash
pip install -r requirements.txt
```

2. Google Cloud Consoleでプロジェクトを作成し、Calendar APIを有効にします。

3. 認証情報を作成し、`credentials.json`としてダウンロードします：
   - Google Cloud Consoleで「認証情報」→「認証情報を作成」→「OAuth 2.0 クライアント ID」を選択
   - アプリケーションの種類で「デスクトップアプリケーション」を選択
   - 作成した認証情報をダウンロードし、`credentials.json`として保存

## 使用方法

### コマンドラインからの使用

```bash
python calendar_api.py
```

### RESTful APIサーバーの使用 (未完成)

1. サーバーを起動します：
```bash
python server.py
```

2. APIエンドポイントにPOSTリクエストを送信します：
```bash
curl -X POST "http://localhost:8000/calendar/event" \
     -H "Content-Type: application/json" \
     -d '{
           "summary": "テストミーティング",
           "description": "これはテストイベントです。",
           "start_time": "2024-03-20T10:00:00Z",
           "end_time": "2024-03-20T11:00:00Z",
           "location": "会議室A"
         }'
```

3. APIドキュメントの確認：
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

### Streamlit Webアプリケーションの使用

1. Streamlitアプリケーションを起動します：
```bash
streamlit run streamlit_app.py
```

2. ブラウザで http://localhost:8501 にアクセスします

3. Webインターフェースで以下の情報を入力します：
   - イベントタイトル（必須）
   - イベントの説明（任意）
   - 場所（任意）
   - 日付と時間

4. 「イベントを作成」ボタンをクリックしてイベントを作成します

## 注意事項

- タイムゾーンは'Asia/Tokyo'に設定されています
- 認証情報（`credentials.json`）は安全に管理してください
- `token.pickle`ファイルも同様に安全に管理してください
- APIサーバーは開発用の設定で起動します。本番環境では適切なセキュリティ設定を行ってください
- Streamlitアプリケーションは開発用の設定で起動します。本番環境では適切なセキュリティ設定を行ってください