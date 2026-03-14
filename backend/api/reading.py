from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from db.database import get_db
from db.models import ReadingHistory, Book, Chapter
import uuid

router = APIRouter(prefix="/api/reading", tags=["reading"])

class ReadingProgress(BaseModel):
    book_id: str
    chapter_id: str
    chapter_name: str
    book_title: str
    read_duration: int = 0

class ReadingHistoryItem(BaseModel):
    id: int
    book_id: str
    chapter_id: str
    chapter_name: Optional[str]
    book_title: Optional[str]
    read_time: datetime
    read_duration: int = 0
    progress: int = 0
    author: Optional[str] = None
    
    class Config:
        from_attributes = True

class ReadingHistoryResponse(BaseModel):
    total: int
    list: List[dict]

@router.post("/progress")
def save_reading_progress(progress: ReadingProgress, db: Session = Depends(get_db)):
    try:
        book_uuid = uuid.UUID(progress.book_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid book_id format")
    
    book = db.query(Book).filter(Book.book_id == book_uuid).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    total_chapters = db.query(Chapter).filter(Chapter.book_id == book_uuid).count()
    
    try:
        current_chapter_uuid = uuid.UUID(progress.chapter_id)
        current_chapter = db.query(Chapter).filter(Chapter.chapter_id == current_chapter_uuid).first()
        if current_chapter and total_chapters > 0:
            progress_percent = int((current_chapter.chapter_order / total_chapters) * 100)
        else:
            progress_percent = 0
    except:
        progress_percent = 0
    
    existing = db.query(ReadingHistory).filter(
        ReadingHistory.book_id == book_uuid
    ).first()
    
    if existing:
        existing.chapter_id = uuid.UUID(progress.chapter_id)
        existing.chapter_name = progress.chapter_name
        existing.book_title = progress.book_title
        existing.read_time = datetime.now()
        existing.read_duration = progress.read_duration
        existing.progress = progress_percent
    else:
        history = ReadingHistory(
            book_id=book_uuid,
            chapter_id=uuid.UUID(progress.chapter_id),
            chapter_name=progress.chapter_name,
            book_title=progress.book_title,
            read_duration=progress.read_duration,
            progress=progress_percent
        )
        db.add(history)
    
    db.commit()
    
    return {"code": 200, "msg": "success", "data": None}

@router.get("/progress/{book_id}")
def get_reading_progress(book_id: str, db: Session = Depends(get_db)):
    try:
        book_uuid = uuid.UUID(book_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid book_id format")
    
    history = db.query(ReadingHistory).filter(
        ReadingHistory.book_id == book_uuid
    ).order_by(ReadingHistory.read_time.desc()).first()
    
    if not history:
        raise HTTPException(status_code=404, detail="No reading progress found")
    
    return {
        "code": 200,
        "msg": "success",
        "data": {
            "book_id": str(history.book_id),
            "chapter_id": str(history.chapter_id),
            "chapter_name": history.chapter_name,
            "book_title": history.book_title
        }
    }

@router.get("/history")
def get_reading_history(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(ReadingHistory).order_by(ReadingHistory.read_time.desc())
    
    total = query.count()
    offset = (page - 1) * size
    histories = query.offset(offset).limit(size).all()
    
    result = []
    for h in histories:
        book = db.query(Book).filter(Book.book_id == h.book_id).first()
        author = book.author if book else None
        
        result.append({
            "id": h.id,
            "book_id": str(h.book_id),
            "chapter_id": str(h.chapter_id),
            "chapter_name": h.chapter_name,
            "book_title": h.book_title,
            "author": author,
            "read_time": h.read_time.isoformat() if h.read_time else None,
            "read_duration": h.read_duration or 0,
            "progress": h.progress or 0
        })
    
    return {"code": 200, "msg": "success", "data": {"total": total, "list": result}}

@router.delete("/history/{book_id}")
def delete_reading_history(book_id: str, db: Session = Depends(get_db)):
    try:
        book_uuid = uuid.UUID(book_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid book_id format")
    
    result = db.query(ReadingHistory).filter(
        ReadingHistory.book_id == book_uuid
    ).delete()
    db.commit()
    
    return {"code": 200, "msg": "success", "data": {"deleted": result}}

@router.delete("/history")
def clear_all_reading_history(db: Session = Depends(get_db)):
    db.query(ReadingHistory).delete()
    db.commit()
    return {"code": 200, "msg": "success", "data": None}
