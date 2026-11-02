import csv, io, json
from urllib.parse import urlparse
from datetime import datetime, timezone
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from PIL import Image
import pytesseract
from .config import settings
from .database import Base, engine, get_db
from .models import KeyRecord, Activity, PublicSource, DailyKeyCount
from .schemas import KeyCreate, KeyOut, ReviewUpdate, SourceCreate
from .services import add_key, log, scan_public_feeds, ask_ai

if settings.tesseract_cmd: pytesseract.pytesseract.tesseract_cmd=settings.tesseract_cmd
Base.metadata.create_all(bind=engine)
app=FastAPI(title="NUSUK WINNER AI API",version="0.1.0")
app.add_middleware(CORSMiddleware,allow_origins=[x.strip() for x in settings.cors_origins.split(",") if x.strip()],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])

@app.get("/api/health")
def health(): return {"status":"ok","app":"NUSUK WINNER AI"}

@app.get("/api/dashboard")
def dashboard(db:Session=Depends(get_db)):
    today=datetime.now(timezone.utc).date().isoformat()
    daily=db.query(DailyKeyCount).filter_by(day=today).first()
    activities=db.query(Activity).order_by(Activity.created_at.desc()).limit(12).all()
    return {"total_keys":db.query(KeyRecord).count(),"duplicates":db.query(Activity).filter_by(action="duplicate_detected").count(),
      "reviewed":db.query(KeyRecord).filter_by(reviewed=True).count(),"daily_keys":daily.count if daily else 0,
      "activity":[{"id":a.id,"action":a.action,"details":a.details,"created_at":a.created_at.isoformat()} for a in activities]}

@app.get("/api/keys",response_model=list[KeyOut])
def list_keys(q:str="",db:Session=Depends(get_db)):
    query=db.query(KeyRecord)
    if q: query=query.filter(KeyRecord.code.contains(q)|KeyRecord.source_name.contains(q))
    return query.order_by(KeyRecord.created_at.desc()).limit(500).all()

@app.post("/api/keys",response_model=KeyOut)
def create_key(payload:KeyCreate,db:Session=Depends(get_db)):
    item,duplicate=add_key(db,payload)
    if duplicate: raise HTTPException(409,detail={"message":"هذا الرمز مسجل بالفعل","id":item.id})
    return item

@app.patch("/api/keys/{key_id}/review",response_model=KeyOut)
def review_key(key_id:int,payload:ReviewUpdate,db:Session=Depends(get_db)):
    item=db.get(KeyRecord,key_id)
    if not item: raise HTTPException(404,"الرمز غير موجود")
    item.reviewed=payload.reviewed; db.commit(); db.refresh(item)
    log(db,"key_reviewed",f"مراجعة الرمز #{key_id}")
    return item

@app.get("/api/keys/export")
def export_keys(format:str="csv",db:Session=Depends(get_db)):
    rows=db.query(KeyRecord).order_by(KeyRecord.id).all()
    data=[{"code":x.code,"category":x.category,"source_name":x.source_name,"source_url":x.source_url,"status":x.status,"reviewed":x.reviewed,"created_at":x.created_at.isoformat()} for x in rows]
    if format=="json":
        return StreamingResponse(io.BytesIO(json.dumps(data,ensure_ascii=False,indent=2).encode()),media_type="application/json",headers={"Content-Disposition":"attachment; filename=nusuk-keys.json"})
    output=io.StringIO(); writer=csv.DictWriter(output,fieldnames=list(data[0]) if data else ["code","category","source_name","source_url","status","reviewed","created_at"])
    writer.writeheader(); writer.writerows(data)
    return StreamingResponse(iter([output.getvalue().encode("utf-8-sig")]),media_type="text/csv",headers={"Content-Disposition":"attachment; filename=nusuk-keys.csv"})

@app.post("/api/sources")
def add_source(payload:SourceCreate,db:Session=Depends(get_db)):
    url=str(payload.feed_url)
    if urlparse(url).scheme!="https": raise HTTPException(400,"يجب أن يكون رابط المصدر HTTPS")
    if db.query(PublicSource).filter_by(feed_url=url).first(): raise HTTPException(409,"المصدر مسجل بالفعل")
    source=PublicSource(name=payload.name,feed_url=url); db.add(source); db.commit(); db.refresh(source)
    log(db,"source_added",f"إضافة مصدر عام: {payload.name}")
    return {"id":source.id,"name":source.name,"feed_url":source.feed_url}

@app.get("/api/sources")
def list_sources(db:Session=Depends(get_db)):
    return [{"id":s.id,"name":s.name,"feed_url":s.feed_url,"enabled":s.enabled,"last_checked":s.last_checked.isoformat() if s.last_checked else None} for s in db.query(PublicSource).all()]

@app.post("/api/scanner/run")
async def run_scanner(db:Session=Depends(get_db)): return {"results":await scan_public_feeds(db)}

@app.post("/api/questions/ocr")
async def question_ocr(file:UploadFile=File(...)):
    if not file.content_type or not file.content_type.startswith("image/"): raise HTTPException(400,"ارفع صورة فقط")
    raw=await file.read()
    if len(raw)>10*1024*1024: raise HTTPException(413,"حجم الصورة يتجاوز 10MB")
    try: extracted=pytesseract.image_to_string(Image.open(io.BytesIO(raw)).convert("RGB"),lang="ara+eng")
    except Exception as exc: raise HTTPException(503,"تعذر تشغيل OCR. تأكد من تثبيت Tesseract ولغتي العربية والإنجليزية.") from exc
    return {"extracted_text":extracted.strip()}

@app.post("/api/questions/solve")
async def solve_question(payload:dict):
    question=str(payload.get("question","")).strip()
    if not question: raise HTTPException(400,"اكتب السؤال أولًا")
    return await ask_ai(question)

@app.get("/api/activity")
def activity(db:Session=Depends(get_db)):
    return [{"id":a.id,"action":a.action,"details":a.details,"created_at":a.created_at.isoformat()} for a in db.query(Activity).order_by(Activity.created_at.desc()).limit(100).all()]
