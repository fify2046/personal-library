from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_
from pydantic import BaseModel
from db.database import get_db
from db.models import Book, Chapter, Image, Paragraph
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
    cover_path: Optional[str] = None
    
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
    cover_path: Optional[str] = None
    
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
            image_count=image_count,
            cover_path=book.cover_path
        ))

    return BookListResponse(total=total, list=result)

class SearchResultItem(BaseModel):
    book_id: str
    title: str
    author: Optional[str] = None
    cover_path: Optional[str] = None
    file_type: str
    matched_snippet: Optional[str] = None
    matched_chapter_id: Optional[str] = None
    matched_para_id: Optional[str] = None
    chapter_name: Optional[str] = None

class SearchResponse(BaseModel):
    total: int
    list: List[SearchResultItem]

from sqlalchemy import text

@router.get("/search", response_model=SearchResponse)
def search_books(
    keyword: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    if not keyword or not keyword.strip():
        return SearchResponse(total=0, list=[])
    
    keyword = keyword.strip().replace('；', ';')
    keywords = [k.strip() for k in keyword.split(';') if k.strip()]
    if not keywords:
        return SearchResponse(total=0, list=[])
    
    results = []
    seen_keys = set()
    
    use_trgm = False
    try:
        result = db.execute(text("""
            SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm'
        """))
        use_trgm = result.fetchone() is not None
    except:
        pass
    
    keyword_patterns = [f"%{k}%" for k in keywords]
    
    title_conditions = []
    for pattern in keyword_patterns:
        title_conditions.append(
            or_(
                Book.title.ilike(pattern),
                Book.author.ilike(pattern)
            )
        )
    title_matches = db.query(Book).filter(
        Book.extract_status == 'success'
    ).filter(or_(*title_conditions)).all()
    
    for book in title_matches:
        key = f"{book.book_id}_title"
        if key not in seen_keys:
            seen_keys.add(key)
            results.append(SearchResultItem(
                book_id=str(book.book_id),
                title=book.title,
                author=book.author,
                cover_path=book.cover_path,
                file_type=book.file_type,
                matched_snippet=None,
                matched_chapter_id=None,
                matched_para_id=None,
                chapter_name="书名/作者匹配"
            ))
    
    max_results = 500
    max_per_book = 20
    
    if use_trgm and len(keywords) == 1:
        keyword_str = keywords[0]
        para_matches = db.execute(text("""
            SELECT p.para_id, p.chapter_id, p.content, c.chapter_name, c.book_id, b.title, b.author, b.cover_path, b.file_type
            FROM paragraphs p
            JOIN chapters c ON p.chapter_id = c.chapter_id
            JOIN books b ON c.book_id = b.book_id
            WHERE b.extract_status = 'success'
            AND p.content % :keyword
            ORDER BY p.para_id
        """), {"keyword": keyword_str}).fetchall()
    else:
        para_conditions = []
        for pattern in keyword_patterns:
            para_conditions.append(Paragraph.content.ilike(pattern))
        para_query = db.query(Paragraph).join(Chapter).join(Book).filter(
            Book.extract_status == 'success'
        ).filter(or_(*para_conditions)).order_by(Paragraph.para_id)
        
        para_matches = []
        for para in para_query:
            chapter = db.query(Chapter).filter(Chapter.chapter_id == para.chapter_id).first()
            if chapter:
                book = db.query(Book).filter(Book.book_id == chapter.book_id).first()
                if book:
                    para_matches.append((para.para_id, para.chapter_id, para.content, chapter.chapter_name, chapter.book_id, book.title, book.author, book.cover_path, book.file_type))
    
    book_para_count = {}
    
    for row in para_matches:
        if len(results) >= max_results:
            break
        
        para_id, chapter_id, content, chapter_name, book_id, title, author, cover_path, file_type = row
        
        book_id_str = str(book_id)
        if book_id_str not in book_para_count:
            book_para_count[book_id_str] = 0
        if book_para_count[book_id_str] >= max_per_book:
            continue
        book_para_count[book_id_str] += 1
        
        key = f"{book_id_str}_{para_id}"
        if key in seen_keys:
            continue
        seen_keys.add(key)
        
        snippet = content.strip() if content else ""
        if len(snippet) > 100:
            idx = snippet.lower().find(keyword.lower())
            if idx >= 0:
                start = max(0, idx - 40)
                end = min(len(snippet), idx + 60)
                snippet = ('...' if start > 0 else '') + snippet[start:end] + ('...' if end < len(snippet) else '')
            else:
                snippet = snippet[:100] + '...'
        
        results.append(SearchResultItem(
            book_id=str(book_id),
            title=title,
            author=author,
            cover_path=cover_path,
            file_type=file_type,
            matched_snippet=snippet,
            matched_chapter_id=str(chapter_id),
            matched_para_id=str(para_id),
            chapter_name=chapter_name
        ))
    
    total = len(results)
    offset = (page - 1) * size
    paginated_results = results[offset:offset + size]
    
    return SearchResponse(total=total, list=paginated_results)

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
        rating=book.rating or 0,
        cover_path=book.cover_path
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
