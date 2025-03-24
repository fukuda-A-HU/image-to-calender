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

def extract_datetime_info(text):
    """テキストから日時情報を抽出"""
    # 日時表現の抽出
    date_patterns = [
        r'\d{4}年\d{1,2}月\d{1,2}日',
        r'\d{1,2}月\d{1,2}日',
        r'\d{1,2}日',
        r'\d{1,2}時',
        r'\d{1,2}:\d{2}'
    ]
    
    dates = []
    for pattern in date_patterns:
        matches = re.finditer(pattern, text)
        for match in matches:
            try:
                date_str = match.group()
                # 年が含まれていない場合は現在の年を追加
                if not re.search(r'\d{4}年', date_str):
                    current_year = datetime.now().year
                    if '月' in date_str:
                        date_str = f"{current_year}年{date_str}"
                
                date = parser.parse(date_str, fuzzy=True)
                dates.append(date)
            except:
                continue
    
    # 日付が1つしかない場合は、終了時刻を開始時刻から1時間後に設定
    if len(dates) == 1:
        dates.append(dates[0] + timedelta(hours=1))
    
    return dates

def extract_event_info(text, dates):
    """テキストからイベント情報を抽出"""
    # イベント情報の抽出
    doc = nlp(text)
    
    # タイトルと説明の抽出（簡単な実装）
    sentences = [sent.text for sent in doc.sents]
    title = sentences[0] if sentences else "イベント"
    description = " ".join(sentences[1:]) if len(sentences) > 1 else text
    
    # 日時の設定
    start_time = dates[0] if dates else None
    end_time = dates[1] if len(dates) > 1 else None
    
    return EventInfo(
        title=title,
        description=description,
        start_time=start_time,
        end_time=end_time
    )

@app.post("/extract-event", response_model=EventInfo)
async def extract_event(file: UploadFile = File(...)):
    """画像からイベント情報を抽出するエンドポイント"""
    # 画像の読み込み
    contents = await file.read()
    image = Image.open(io.BytesIO(contents))
    
    # 画像からテキストを抽出
    text = extract_text_from_image(image)
    
    # 日時情報の抽出
    dates = extract_datetime_info(text)
    
    # イベント情報の構造化
    event_info = extract_event_info(text, dates)
    
    return event_info

@app.post("/calendar/event")
async def create_calendar_event(event: EventInfo):
    """カレンダーにイベントを追加するエンドポイント"""
    try:
        # タイムゾーンをUTCに設定
        start_time = event.start_time.replace(tzinfo=pytz.UTC)
        end_time = event.end_time.replace(tzinfo=pytz.UTC)
        
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
        
        # 日時情報の抽出
        dates = extract_datetime_info(text)
        
        if not dates:
            raise HTTPException(
                status_code=400,
                detail="画像から日時情報を抽出できませんでした"
            )
        
        # イベント情報の構造化
        event_info = extract_event_info(text, dates)
        
        # タイムゾーンをUTCに設定
        start_time = event_info.start_time.replace(tzinfo=pytz.UTC)
        end_time = event_info.end_time.replace(tzinfo=pytz.UTC)
        
        # カレンダーにイベントを追加
        result = add_event(
            summary=event_info.title,
            description=event_info.description,
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