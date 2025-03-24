from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from PIL import Image
import io
import base64
import spacy
from dateutil import parser
import re
from typing import Optional
from datetime import datetime, timedelta
from calendar_api import add_event
import pytz
from openai import OpenAI
import os
from dotenv import load_dotenv
import json

# 環境変数の読み込み
load_dotenv()

app = FastAPI(title="Google Calendar API Server")

# CORSミドルウェアの設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OpenAIクライアントの初期化
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 自然言語処理モデルの初期化
nlp = spacy.load("ja_core_news_sm")

# タイムゾーンの設定
JST = pytz.timezone('Asia/Tokyo')
UTC = pytz.UTC

class EventInfo(BaseModel):
    title: str
    description: str
    start_time: Optional[datetime]
    end_time: Optional[datetime]

def encode_image_to_base64(image):
    """画像をBase64エンコードする"""
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def extract_text_from_image(image):
    """OpenAI Vision APIを使用して画像からテキストを抽出"""
    try:
        # 画像をBase64エンコード
        base64_image = encode_image_to_base64(image)
        
        # OpenAI Vision APIにリクエスト
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "この画像に含まれるテキストと内容を詳しく説明してください。特に日時に関する情報があれば、その情報も含めてください。"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=1000
        )
        
        return response.choices[0].message.content
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"画像の処理中にエラーが発生しました: {str(e)}"
        )

def extract_datetime_with_gpt(text, max_retries=3):
    """GPTを使用してテキストから日時情報を抽出（最大3回まで再試行）"""
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": """あなたは日時情報を抽出する専門家です。
                        与えられたテキストから日時情報を抽出し、以下のJSON形式で出力してください：
                        {
                            "start_time": "YYYY-MM-DD HH:mm:ss",
                            "end_time": "YYYY-MM-DD HH:mm:ss",
                            "title": "イベントのタイトル",
                            "description": "イベントの説明"
                        }
                        日時が不明な場合は、nullを設定してください。
                        日付のみが指定されている場合は、時間は00:00:00としてください。
                        終了時刻が不明な場合は、開始時刻から1時間後を設定してください。
                        日時情報が見つからない場合は、必ずstart_timeとend_timeをnullに設定してください。
                        全ての日時は日本時間（JST）として解釈してください。"""
                    },
                    {
                        "role": "user",
                        "content": text
                    }
                ],
                response_format={ "type": "json_object" },
                max_tokens=1000
            )
            
            # JSON文字列をパース
            result = json.loads(response.choices[0].message.content)
            
            # 文字列の日時をdatetimeオブジェクトに変換（JSTとして解釈）
            if result["start_time"]:
                naive_dt = datetime.strptime(result["start_time"], "%Y-%m-%d %H:%M:%S")
                result["start_time"] = JST.localize(naive_dt)
            if result["end_time"]:
                naive_dt = datetime.strptime(result["end_time"], "%Y-%m-%d %H:%M:%S")
                result["end_time"] = JST.localize(naive_dt)
            
            # 日時情報が正しく抽出できた場合のみ返す
            if result["start_time"] and result["end_time"]:
                return result
            
            # 日時情報が抽出できなかった場合は再試行
            if attempt < max_retries - 1:
                continue
                
        except Exception as e:
            if attempt < max_retries - 1:
                continue
            raise HTTPException(
                status_code=500,
                detail=f"日時情報の抽出中にエラーが発生しました: {str(e)}"
            )
    
    # 全ての試行が失敗した場合
    raise HTTPException(
        status_code=400,
        detail="画像から日時情報を抽出できませんでした（3回試行しましたが失敗しました）"
    )

@app.post("/extract-event", response_model=EventInfo)
async def extract_event(file: UploadFile = File(...)):
    """画像からイベント情報を抽出するエンドポイント"""
    # 画像の読み込み
    contents = await file.read()
    image = Image.open(io.BytesIO(contents))
    
    # 画像からテキストを抽出
    text = extract_text_from_image(image)
    
    # GPTを使用して日時情報を抽出
    event_info = extract_datetime_with_gpt(text)
    
    return EventInfo(**event_info)

@app.post("/calendar/event")
async def create_calendar_event(event: EventInfo):
    """カレンダーにイベントを追加するエンドポイント"""
    try:
        # JSTからUTCに変換
        start_time = event.start_time.astimezone(UTC)
        end_time = event.end_time.astimezone(UTC)
        
        result = add_event(
            summary=event.title,
            description=event.description,
            start_time=start_time,
            end_time=end_time,
            location=None
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/calendar/event-from-image")
async def create_calendar_event_from_image(file: UploadFile = File(...)):
    """画像からイベント情報を抽出し、Googleカレンダーに追加するエンドポイント"""
    try:
        # 画像の読み込み
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        
        # 画像からテキストを抽出
        text = extract_text_from_image(image)
        
        # GPTを使用して日時情報を抽出
        event_info = extract_datetime_with_gpt(text)
        
        if not event_info["start_time"]:
            raise HTTPException(
                status_code=400,
                detail="画像から日時情報を抽出できませんでした"
            )
        
        # JSTからUTCに変換
        start_time = event_info["start_time"].astimezone(UTC)
        end_time = event_info["end_time"].astimezone(UTC)
        
        # カレンダーにイベントを追加
        result = add_event(
            summary=event_info["title"],
            description=event_info["description"],
            start_time=start_time,
            end_time=end_time,
            location=None
        )
        
        return {
            "message": "イベントが正常に作成されました",
            "event_info": event_info,
            "calendar_result": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"message": "Google Calendar API Server is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 