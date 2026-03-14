from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from db.database import get_db
from db.models import ReadingList, ReadingHistory, Book, Chapter
import uuid

router = APIRouter(prefix="/api/reading_list", tags=["reading_list"])

class ReadingListItem(BaseModel):
    book_id: str

class ReadingListBook(BaseModel):
    book_id: str
    title: str
    author: Optional[str]
    file_type: str
    add_time: datetime
    last_chapter_id: Optional[str] = None
    last_chapter_name: Optional[str] = None
    progress: Optional[int] = None

@router.post("/add")
def add_to_reading_list(item: ReadingListItem, db: Session = Depends(get_db)):
    try:
        book_uuid = uuid.UUID(item.book_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid book_id format")
    
    book = db.query(Book).filter(Book.book_id == book_uuid).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    existing = db.query(ReadingList).filter(ReadingList.book_id == book_uuid).first()
    if existing:
        return {"code": 200, "msg": "Already in reading list", "data": None}
    
    reading_item = ReadingList(book_id=book_uuid)
    db.add(reading_item)
    db.commit()
    
    return {"code": 200, "msg": "success", "data": None}

@router.post("/remove")
def remove_from_reading_list(item: ReadingListItem, db: Session = Depends(get_db)):
    try:
        book_uuid = uuid.UUID(item.book_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid book_id format")
    
    result = db.query(ReadingList).filter(ReadingList.book_id == book_uuid).delete()
    db.commit()
    
    return {"code": 200, "msg": "success", "data": {"deleted": result}}

@router.get("/list")
def get_reading_list(db: Session = Depends(get_db)):
    reading_items = db.query(ReadingList).order_by(ReadingList.add_time.desc()).all()
    
    result = []
    for item in reading_items:
        book = db.query(Book).filter(Book.book_id == item.book_id).first()
        if book:
            chapter_count = db.query(Chapter).filter(Chapter.book_id == book.book_id).count()
            
            history = db.query(ReadingHistory).filter(
                ReadingHistory.book_id == book.book_id
            ).order_by(ReadingHistory.read_time.desc()).first()
            
            last_chapter_id = None
            last_chapter_name = None
            progress = None
            
            if history:
                last_chapter_id = str(history.chapter_id)
                last_chapter_name = history.chapter_name
                if chapter_count > 0:
                    current_ch = db.query(Chapter).filter(
                        Chapter.chapter_id == history.chapter_id
                    ).first()
                    if current_ch:
                        progress = int((current_ch.chapter_order / chapter_count) * 100)
            
            result.append({
                "book_id": str(book.book_id),
                "title": book.title,
                "author": book.author,
                "file_type": book.file_type,
                "add_time": item.add_time.isoformat() if item.add_time else None,
                "last_chapter_id": last_chapter_id,
                "last_chapter_name": last_chapter_name,
                "progress": progress,
                "chapter_count": chapter_count
            })
    
    return {"code": 200, "msg": "success", "data": result}

@router.get("/check/{book_id}")
def check_in_reading_list(book_id: str, db: Session = Depends(get_db)):
    try:
        book_uuid = uuid.UUID(book_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid book_id format")
    
    existing = db.query(ReadingList).filter(ReadingList.book_id == book_uuid).first()
    
    return {"code": 200, "msg": "success", "data": {"in_list": existing is not None}}
