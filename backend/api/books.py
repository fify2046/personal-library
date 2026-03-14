from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from pydantic import BaseModel
from db.database import get_db
from db.models import Book, Chapter, Image
import uuid

router = APIRouter(prefix="/api/books", tags=["books"])

class BookListItem(BaseModel):
    book_id: str
    title: str
    author: Optional[str]
    publisher: Optional[str]
    publish_date: Optional[str]
    isbn: Optional[str] = None
    file_type: str
    chapter_count: int = 0
    image_count: int = 0
    
    class Config:
        from_attributes = True

class BookDetail(BaseModel):
    book_id: str
    title: str
    author: Optional[str]
    publisher: Optional[str]
    publish_date: Optional[str]
    isbn: Optional[str] = None
    file_type: str
    file_size: Optional[int]
    chapter_count: int
    image_count: int
    rating: int = 0
    
    class Config:
        from_attributes = True

class BookListResponse(BaseModel):
    total: int
    list: List[BookListItem]

@router.get("", response_model=BookListResponse)
def get_books(
    page: int = Query(1, ge=1),
    size: int = Query(12, ge=1, le=100),
    type: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    sort: str = Query("recent"),
    all_books: bool = Query(False),
    db: Session = Depends(get_db)
):
    if all_books:
        query = db.query(Book)
    else:
        query = db.query(Book).filter(Book.extract_status == 'success')
    
    if type and type.lower() in ['pdf', 'epub']:
        query = query.filter(Book.file_type == type.lower())
    
    if keyword:
        query = query.filter(
            or_(
                Book.title.ilike(f"%{keyword}%"),
                Book.author.ilike(f"%{keyword}%")
            )
        )
    
    if sort == "title":
        query = query.order_by(Book.title.asc())
    else:
        query = query.order_by(Book.create_time.desc())
    
    total = query.count()
    
    offset = (page - 1) * size
    books = query.offset(offset).limit(size).all()
    
    result = []
    for book in books:
        chapter_count = db.query(Chapter).filter(Chapter.book_id == book.book_id).count()
        image_count = db.query(Image).join(Chapter).filter(Chapter.book_id == book.book_id).count()
        result.append(BookListItem(
            book_id=str(book.book_id),
            title=book.title,
            author=book.author,
            publisher=book.publisher,
            publish_date=book.publish_date,
            isbn=book.isbn,
            file_type=book.file_type,
            chapter_count=chapter_count,
            image_count=image_count
        ))
    
    return BookListResponse(total=total, list=result)

@router.get("/{book_id}", response_model=BookDetail)
def get_book(book_id: str, db: Session = Depends(get_db)):
    try:
        book_uuid = uuid.UUID(book_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid book_id format")
    
    book = db.query(Book).filter(Book.book_id == book_uuid).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    chapter_count = db.query(Chapter).filter(Chapter.book_id == book.book_id).count()
    image_count = db.query(Image).join(Chapter).filter(Chapter.book_id == book.book_id).count()
    
    return BookDetail(
        book_id=str(book.book_id),
        title=book.title,
        author=book.author,
        publisher=book.publisher,
        publish_date=book.publish_date,
        isbn=book.isbn,
        file_type=book.file_type,
        file_size=book.file_size,
        chapter_count=chapter_count,
        image_count=image_count,
        rating=book.rating or 0
    )

@router.get("/{book_id}/chapters")
def get_chapters(book_id: str, db: Session = Depends(get_db)):
    try:
        book_uuid = uuid.UUID(book_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid book_id format")
    
    book = db.query(Book).filter(Book.book_id == book_uuid).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    chapters = db.query(Chapter).filter(Chapter.book_id == book_uuid).order_by(Chapter.chapter_order).all()
    
    chapter_map = {}
    for c in chapters:
        chapter_map[str(c.chapter_id)] = {
            "chapter_id": str(c.chapter_id),
            "chapter_name": c.chapter_name,
            "chapter_order": c.chapter_order,
            "chapter_level": c.chapter_level or 0,
            "parent_id": str(c.parent_id) if c.parent_id else None,
            "children": []
        }
    
    root_chapters = []
    for c in chapter_map.values():
        if c["parent_id"] and c["parent_id"] in chapter_map:
            chapter_map[c["parent_id"]]["children"].append(c)
        else:
            root_chapters.append(c)
    
    return root_chapters

class DisplayModeUpdate(BaseModel):
    display_mode: str

@router.put("/{book_id}/display_mode")
def update_display_mode(book_id: str, data: DisplayModeUpdate, db: Session = Depends(get_db)):
    try:
        book_uuid = uuid.UUID(book_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid book_id format")
    
    book = db.query(Book).filter(Book.book_id == book_uuid).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    if data.display_mode not in ['original', 'traditional', 'simplified']:
        raise HTTPException(status_code=400, detail="Invalid display_mode")
    
    book.display_mode = data.display_mode
    db.commit()
    
    return {"code": 200, "msg": "success", "data": {"display_mode": book.display_mode}}

@router.get("/{book_id}/display_mode")
def get_display_mode(book_id: str, db: Session = Depends(get_db)):
    try:
        book_uuid = uuid.UUID(book_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid book_id format")
    
    book = db.query(Book).filter(Book.book_id == book_uuid).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    return {"code": 200, "msg": "success", "data": {"display_mode": book.display_mode or 'original'}}

class BookUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    publisher: Optional[str] = None
    publish_date: Optional[str] = None
    isbn: Optional[str] = None

@router.put("/{book_id}")
def update_book(book_id: str, data: BookUpdate, db: Session = Depends(get_db)):
    try:
        book_uuid = uuid.UUID(book_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid book_id format")
    
    book = db.query(Book).filter(Book.book_id == book_uuid).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    if data.title is not None:
        book.title = data.title
    if data.author is not None:
        book.author = data.author
    if data.publisher is not None:
        book.publisher = data.publisher
    if data.publish_date is not None:
        book.publish_date = data.publish_date
    if data.isbn is not None:
        book.isbn = data.isbn
    
    db.commit()
    
    return {"code": 200, "msg": "success", "data": None}

class RatingUpdate(BaseModel):
    rating: int

@router.put("/{book_id}/rating")
def update_book_rating(book_id: str, data: RatingUpdate, db: Session = Depends(get_db)):
    try:
        book_uuid = uuid.UUID(book_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid book_id format")
    
    if data.rating < 0 or data.rating > 10:
        raise HTTPException(status_code=400, detail="Rating must be between 0 and 10")
    
    book = db.query(Book).filter(Book.book_id == book_uuid).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    book.rating = data.rating
    db.commit()
    
    return {"code": 200, "msg": "success", "data": {"rating": book.rating}}

@router.delete("/{book_id}")
def delete_book(book_id: str, db: Session = Depends(get_db)):
    import os
    import shutil
    try:
        book_uuid = uuid.UUID(book_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid book_id format")
    
    book = db.query(Book).filter(Book.book_id == book_uuid).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    from db.config import config
    image_dir = config.IMAGES_DIR
    book_img_dir = os.path.join(image_dir, book_id)
    if os.path.exists(book_img_dir):
        shutil.rmtree(book_img_dir)
    
    from db.models import Paragraph, Image, Chapter
    
    chapters = db.query(Chapter).filter(Chapter.book_id == book_uuid).all()
    for chapter in chapters:
        db.query(Image).filter(Image.chapter_id == chapter.chapter_id).delete()
        db.query(Paragraph).filter(Paragraph.chapter_id == chapter.chapter_id).delete()
    
    db.query(Chapter).filter(Chapter.book_id == book_uuid).delete()
    
    try:
        from db.models import ReadingHistory
        db.query(ReadingHistory).filter(ReadingHistory.book_id == book_uuid).delete()
    except:
        pass
    
    try:
        from db.models import Favorite
        db.query(Favorite).filter(Favorite.book_id == book_uuid).delete()
    except:
        pass
    
    try:
        from db.models import ReadingList
        db.query(ReadingList).filter(ReadingList.book_id == book_uuid).delete()
    except:
        pass
    
    db.query(Book).filter(Book.book_id == book_uuid).delete()
    db.commit()
    
    return {"code": 200, "msg": "success", "data": None}
