import streamlit as st
import requests
from PIL import Image
import io
from datetime import datetime, time
import pytz

# タイムゾーンの設定
JST = pytz.timezone('Asia/Tokyo')

# ページ設定
st.set_page_config(
    page_title="画像からカレンダーイベント作成",
    page_icon="📅",
    layout="wide"
)

# タイトル
st.title("📅 画像からカレンダーイベント作成")

# 説明
st.markdown("""
このアプリケーションは、画像からイベント情報を抽出し、Googleカレンダーに登録します。

### 使い方
1. イベント情報が含まれる画像をアップロード
2. 抽出された情報を確認
3. 必要に応じて情報を編集
4. カレンダーに登録
""")

# 画像アップロード
uploaded_file = st.file_uploader("画像をアップロード", type=['jpg', 'jpeg', 'png'])

if uploaded_file is not None:
    # 画像の表示
    image = Image.open(uploaded_file)
    st.image(image, caption="アップロードされた画像", use_column_width=True)
    
    # 抽出ボタン
    if st.button("イベント情報を抽出"):
        with st.spinner("イベント情報を抽出中..."):
            try:
                # 画像をバイトデータに変換
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format='JPEG')
                img_byte_arr = img_byte_arr.getvalue()
                
                # ファイルをアップロード
                files = {'file': ('image.jpg', img_byte_arr, 'image/jpeg')}
                response = requests.post('http://localhost:8000/extract-event', files=files)
                
                if response.status_code == 200:
                    event_info = response.json()
                    
                    # フォームの作成
                    with st.form("event_form"):
                        st.subheader("イベント情報")
                        
                        # タイトル
                        title = st.text_input("タイトル", value=event_info["title"])
                        
                        # 説明
                        description = st.text_area("説明", value=event_info["description"])
                        
                        # 開始時刻
                        start_time = datetime.fromisoformat(event_info["start_time"].replace('Z', '+00:00'))
                        start_time = start_time.astimezone(JST)
                        
                        start_date = st.date_input(
                            "開始日",
                            value=start_time.date()
                        )
                        start_time_input = st.time_input(
                            "開始時刻",
                            value=start_time.time()
                        )
                        
                        # 終了時刻
                        end_time = datetime.fromisoformat(event_info["end_time"].replace('Z', '+00:00'))
                        end_time = end_time.astimezone(JST)
                        
                        end_date = st.date_input(
                            "終了日",
                            value=end_time.date()
                        )
                        end_time_input = st.time_input(
                            "終了時刻",
                            value=end_time.time()
                        )
                        
                        # 送信ボタン（フォーム内に配置）
                        submitted = st.form_submit_button("カレンダーに登録")
                        
                        if submitted:
                            try:
                                # 日付と時刻を組み合わせて datetime オブジェクトを作成し、JSTタイムゾーンを設定
                                start_datetime = JST.localize(datetime.combine(start_date, start_time_input))
                                end_datetime = JST.localize(datetime.combine(end_date, end_time_input))
                                
                                # イベント情報の作成
                                event_data = {
                                    "title": title,
                                    "description": description,
                                    "start_time": start_datetime.isoformat(),
                                    "end_time": end_datetime.isoformat()
                                }
                                
                                st.write("送信するデータ:", event_data)  # デバッグ用
                                
                                # カレンダーに登録
                                response = requests.post(
                                    'http://localhost:8000/calendar/event',
                                    json=event_data
                                )
                                
                                st.write("レスポンス:", response.text)  # デバッグ用
                                
                                if response.status_code == 200:
                                    st.success("イベントが正常に登録されました！")
                                else:
                                    st.error(f"エラーが発生しました: {response.text}")
                            except Exception as e:
                                st.error(f"カレンダー登録中にエラーが発生しました: {str(e)}")
                else:
                    st.error(f"エラーが発生しました: {response.text}")
                    
            except Exception as e:
                st.error(f"エラーが発生しました: {str(e)}")

# フッター
st.markdown("---")
st.markdown("Made with ❤️ by Your Name")