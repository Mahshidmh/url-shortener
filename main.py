from config import settings
from pydantic import BaseModel ,HttpUrl
from fastapi import FastAPI , HTTPException , Depends , Request
import uuid
from fastapi.responses import RedirectResponse , JSONResponse
from database import get_session , URL
from sqlmodel import Session , select
from sqlalchemy import text
from datetime import datetime , UTC
from fastapi.security import APIKeyHeader
import logging
from config import settings
from logging_config import setup_logging

setup_logging(settings.log_level)
logger = logging.getLogger(__name__)

app = FastAPI()
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled error on %s %s", request.method, request.url.path, exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

RESERVED_WORDS = {"health","urls", "docs", "openapi.json","redoc"}
request_log = {}
api_key_header = APIKeyHeader(name="X-API-Key")

def verify_api_key(key: str = Depends(api_key_header)):
    if key != settings.api_key:
        logger.warning("Invalid API key attempt")
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

class URLCreate(BaseModel):
    original_url: HttpUrl
    expires_at: datetime | None = None

class URLUpdate(BaseModel):
    original_url: HttpUrl


@app.post("/urls", status_code = 201)
def create_url(url: URLCreate ,request : Request ,session : Session = Depends(get_session), _: bool = Depends(verify_api_key)):
    ip = request.client.host

    if is_rate_limited(ip):
        logger.warning("Rate limit exceeded for %s", ip)
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again later.")

    code = generate_unique_code(session)
    db_url = URL(original_url=str(url.original_url), short_code=code, expires_at=url.expires_at)
    session.add(db_url)
    session.commit()
    logger.info("URL created %s", code)
    session.refresh(db_url)
    return {"short_code": code, "original_url": url.original_url, "expires_at": url.expires_at}


@app.get("/urls")
def list_urls(skip: int = 0, limit: int = 10, session: Session = Depends(get_session)):
    statement = select(URL).offset(skip).limit(limit)
    return session.exec(statement).all()



@app.patch("/urls/{short_code}")
def update_url(short_code: str, url:URLUpdate, session: Session = Depends(get_session), _: bool = Depends(verify_api_key)):
    db_url = session.exec(select(URL).where(URL.short_code == short_code)).first()
    if db_url is None:
        raise HTTPException(status_code=404, detail="Short code not found")
    db_url.original_url = str(url.original_url)
    session.add(db_url)
    session.commit()
    session.refresh(db_url)
    return db_url


@app.delete("/urls/{short_code}", status_code=204)
def delete_url(short_code: str, session: Session = Depends(get_session), _: bool = Depends(verify_api_key)):
    db_url = session.exec(select(URL).where(URL.short_code == short_code)).first()
    if db_url is None:
        raise HTTPException(status_code=404, detail="Short code not found")
    session.delete(db_url)
    session.commit()

@app.get("/health")
def health_check(session: Session = Depends(get_session)):
    try:
        session.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(status_code=503, detail="Database unavailable")
    return {"status": "ok"}

@app.get("/{short_code}")
def redirect_to_url(short_code : str, session: Session = Depends(get_session)):
    statement = select(URL).where(URL.short_code == short_code)
    result = session.exec(statement).first()
    if result is None:
        raise HTTPException(status_code=404, detail="Short code not found")

    if result.expires_at is not None and result.expires_at < datetime.now(UTC):
        logger.info("Expired link requested: %s", short_code)
        raise HTTPException(status_code = 410, detail="Link is expired or not found!")
    result.click_count += 1
    session.add(result)
    session.commit()
    return RedirectResponse(url=result.original_url)


@app.get("/urls/{short_code}/stats")
def get_url_stats(short_code: str, session: Session = Depends(get_session)):
    statement = select(URL).where(URL.short_code == short_code)
    result = session.exec(statement).first()
    if result is None:
        raise HTTPException(status_code=404, detail="Short code not found")
    return {"short_code": result.short_code, "original_url": result.original_url, "click_count": result.click_count}

def generate_unique_code(session: Session) -> str:
    while True:
        code = uuid.uuid4().hex[:6]
        if not is_valid_alias(code):
            continue
        existing = session.exec(select(URL).where(URL.short_code == code)).first()
        if existing is None:
            return code

def is_valid_alias(code: str) -> bool:
    if code in RESERVED_WORDS:
        return False
    if not code.isalnum():
        return False
    if not(1 <= len(code) <= 10):
        return False
    return True

def is_rate_limited(ip: str) -> bool:
    LIMIT = 5
    WINDOW_SECONDS = 60

    if ip not in request_log:
        request_log[ip] = []

    now = datetime.now(UTC)

    request_log[ip] = [
        timestamp for timestamp in request_log[ip]
        if (now - timestamp).total_seconds() < WINDOW_SECONDS
    ]

    if len(request_log[ip]) >= LIMIT:
        return True

    request_log[ip].append(now)
    return False

