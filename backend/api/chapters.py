from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from db.database import get_db
from db.models import Chapter, Paragraph, Image
from typing import List, Union, Dict, Optional
import uuid

router = APIRouter(prefix="/api/chapters", tags=["chapters"])

class ContentItem(BaseModel):
    type: str
    id: str
    content: str
    order: int
    is_footnote: Optional[bool] = False

class ChapterContent(BaseModel):
    chapter_name: str
    content: List[ContentItem]

@router.get("/{chapter_id}/content", response_model=ChapterContent)
def get_chapter_content(chapter_id: str, db: Session = Depends(get_db)):
    try:
        chapter_uuid = uuid.UUID(chapter_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid chapter_id format")
    
    chapter = db.query(Chapter).filter(Chapter.chapter_id == chapter_uuid).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    
    paragraphs = db.query(Paragraph).filter(
        Paragraph.chapter_id == chapter_uuid
    ).order_by(Paragraph.para_order).all()
    
    content = []
    for p in paragraphs:
        para_type = p.para_type if p.para_type else 'text'
        content.append({
            "type": para_type, 
            "id": str(p.para_id), 
            "content": p.content or "", 
            "order": p.para_order,
            "is_footnote": p.is_footnote if p.is_footnote else False
        })
    
    return ChapterContent(
        chapter_name=chapter.chapter_name or "",
        content=content
    )
