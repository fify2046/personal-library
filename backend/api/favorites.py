from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from db.database import get_db
from db.models import Favorite, ReadingList, Book
import uuid

router = APIRouter(prefix="/api/favorites", tags=["favorites"])

class FavoriteItem(BaseModel):
    book_id: str

class FavoriteBook(BaseModel):
    book_id: str
    title: str
    author: Optional[str]
    file_type: str
    add_time: datetime

@router.post("/add")
def add_favorite(item: FavoriteItem, db: Session = Depends(get_db)):
    try:
        book_uuid = uuid.UUID(item.book_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid book_id format")
    
    book = db.query(Book).filter(Book.book_id == book_uuid).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    existing = db.query(Favorite).filter(Favorite.book_id == book_uuid).first()
    if existing:
        return {"code": 200, "msg": "Already in favorites", "data": None}
    
    favorite = Favorite(book_id=book_uuid)
    db.add(favorite)
    db.commit()
    
    return {"code": 200, "msg": "success", "data": None}

@router.post("/remove")
def remove_favorite(item: FavoriteItem, db: Session = Depends(get_db)):
    try:
        book_uuid = uuid.UUID(item.book_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid book_id format")
    
    result = db.query(Favorite).filter(Favorite.book_id == book_uuid).delete()
    db.commit()
    
    return {"code": 200, "msg": "success", "data": {"deleted": result}}

@router.get("/list")
def get_favorites(db: Session = Depends(get_db)):
    favorites = db.query(Favorite).order_by(Favorite.add_time.desc()).all()
    
    result = []
    for f in favorites:
        book = db.query(Book).filter(Book.book_id == f.book_id).first()
        if book:
            result.append({
                "book_id": str(book.book_id),
                "title": book.title,
                "author": book.author,
                "file_type": book.file_type,
                "add_time": f.add_time.isoformat() if f.add_time else None
            })
    
    return {"code": 200, "msg": "success", "data": result}

@router.get("/check/{book_id}")
def check_favorite(book_id: str, db: Session = Depends(get_db)):
    try:
        book_uuid = uuid.UUID(book_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid book_id format")
    
    existing = db.query(Favorite).filter(Favorite.book_id == book_uuid).first()
    
    return {"code": 200, "msg": "success", "data": {"is_favorited": existing is not None}}
