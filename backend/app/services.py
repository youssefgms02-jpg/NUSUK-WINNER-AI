import ipaddress
import re
import socket
from datetime import datetime, timezone
from urllib.parse import urlparse

import feedparser
import httpx
from sqlalchemy.orm import Session

from .models import KeyRecord, Activity, PublicSource, DailyKeyCount
from .config import settings

CODE_PATTERN = re.compile(r"(?<![A-Za-z0-9])([A-Za-z0-9][A-Za-z0-9_-]{5,39})(?![A-Za-z0-9])")
MAX_FEED_BYTES = 2 * 1024 * 1024


def validate_public_feed_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("يجب أن يكون المصدر رابط HTTPS عامًا وصالحًا")
    if parsed.port not in (None, 443):
        raise ValueError("منافذ المصادر المخصصة غير مسموح بها")
    try:
        addresses = socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ValueError("تعذر العثور على عنوان المصدر") from exc
    if not addresses:
        raise ValueError("عنوان المصدر غير صالح")
    for item in addresses:
        address = ipaddress.ip_address(item[4][0])
        if not address.is_global:
            raise ValueError("المصدر يجب أن يشير إلى عنوان إنترنت عام")


def log(db: Session, action: str, details: str = ""):
    db.add(Activity(action=action, details=details))
    db.commit()


def normalize(code: str) -> str:
    return re.sub(r"\\s+", "", code).upper()


def add_key(db: Session, payload):
    normalized = normalize(payload.code)
    existing = db.query(KeyRecord).filter_by(normalized_code=normalized).first()
    if existing:
        log(db, "duplicate_detected", f"تكرر الرمز: {payload.code}")
        return existing, True
    item = KeyRecord(
        code=payload.code.strip(), normalized_code=normalized,
        category=payload.category, source_name=payload.source_name,
        source_url=payload.source_url, notes=payload.notes, status="unverified"
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    today = datetime.now(timezone.utc).date().isoformat()
    daily = db.query(DailyKeyCount).filter_by(day=today).first()
    if not daily:
        daily = DailyKeyCount(day=today, count=0)
        db.add(daily)
    daily.count += 1
    db.commit()
    log(db, "key_added", f"تم تسجيل رمز جديد من {payload.source_name}")
    return item, False


async def scan_public_feeds(db: Session):
    found = []
    client_timeout = httpx.Timeout(12.0, connect=5.0)
    async with httpx.AsyncClient(timeout=client_timeout, follow_redirects=False, headers={"User-Agent": "NusukWinnerAI/1.0 public-feed-reader"}) as client:
        for source in db.query(PublicSource).filter_by(enabled=True).all():
            try:
                validate_public_feed_url(source.feed_url)
                response = await client.get(source.feed_url)
                response.raise_for_status()
                if len(response.content) > MAX_FEED_BYTES:
                    raise ValueError("حجم الموجز أكبر من الحد المسموح")
                parsed = feedparser.parse(response.content)
                for entry in parsed.entries[:100]:
                    blob = " ".join([str(entry.get("title", "")), str(entry.get("summary", ""))])
                    for match in CODE_PATTERN.findall(blob):
                        class Payload:
                            pass
                        payload = Payload()
                        payload.code = match
                        payload.category = "من مصدر عام"
                        payload.source_name = source.name
                        payload.source_url = str(entry.get("link", ""))
                        payload.notes = "اكتُشف آليًا؛ يحتاج مراجعة وتأكيدًا رسميًا."
                        item, duplicate = add_key(db, payload)
                        found.append({"code": item.code, "duplicate": duplicate, "source": source.name, "url": payload.source_url})
                source.last_checked = datetime.now(timezone.utc)
            except Exception as exc:
                source.last_checked = datetime.now(timezone.utc)
                log(db, "source_scan_error", f"{source.name}: {str(exc)[:180]}")
    db.commit()
    log(db, "public_scan", f"فحص {len(db.query(PublicSource).all())} مصدر عام")
    return found


async def ask_ai(question: str):
    if not settings.ai_api_key:
        return {
            "answer": "خدمة الذكاء الاصطناعي غير مهيأة. أضف AI_API_KEY في إعدادات الخادم.",
            "confidence": "غير متاح", "sources": []
        }
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=settings.ai_api_key, base_url=settings.ai_base_url or None)
    result = await client.chat.completions.create(
        model=settings.ai_model, temperature=0.2,
        messages=[
            {"role": "system", "content": "أجب بالعربية بوضوح. لا تخترع مصادر أو حقائق. ميّز بين المعلومة المؤكدة والتقدير، واطلب التحقق الرسمي من صلاحية أي رمز."},
            {"role": "user", "content": question}
        ]
    )
    return {"answer": result.choices[0].message.content or "", "confidence": "تقديري؛ راجع المصادر", "sources": []}
