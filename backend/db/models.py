from sqlalchemy import Column, String, Integer, BigInteger, Text, ForeignKey, DateTime, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from db.database import Base
from datetime import datetime
import uuid

class Book(Base):
    __tablename__ = "books"
    
    book_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(500), nullable=False)
    author = Column(String(200))
    file_path = Column(String(1000), nullable=False)
    file_type = Column(String(10), nullable=False)
    file_size = Column(BigInteger)
    create_time = Column(DateTime, default=lambda: datetime.now())
    extract_status = Column(String(20), default='pending')
    display_mode = Column(String(30), default='original')
    publisher = Column(String(200))
    publish_date = Column(String(50))
    isbn = Column(String(30))
    rating = Column(Integer, default=0)
    cover_path = Column(String(1000))
    
    chapters = relationship("Chapter", back_populates="book", cascade="all, delete-orphan")

class Chapter(Base):
    __tablename__ = "chapters"
    
    chapter_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    book_id = Column(UUID(as_uuid=True), ForeignKey("books.book_id", ondelete="CASCADE"), nullable=False)
    chapter_name = Column(String(500))
    chapter_order = Column(Integer, nullable=False)
    chapter_level = Column(Integer, default=0)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("chapters.chapter_id", ondelete="SET NULL"), nullable=True)
    
    book = relationship("Book", back_populates="chapters")
    paragraphs = relationship("Paragraph", back_populates="chapter", cascade="all, delete-orphan")
    images = relationship("Image", back_populates="chapter", cascade="all, delete-orphan")
    summary = relationship("BookChapterSummary", back_populates="chapter", uselist=False, cascade="all, delete-orphan")

class Paragraph(Base):
    __tablename__ = "paragraphs"
    
    para_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chapter_id = Column(UUID(as_uuid=True), ForeignKey("chapters.chapter_id", ondelete="CASCADE"), nullable=False)
    content = Column(Text)
    para_type = Column(String(20), default='text')
    para_order = Column(Integer, nullable=False)
    is_footnote = Column(Boolean, default=False)
    style_info = Column(JSON, nullable=True)
    
    chapter = relationship("Chapter", back_populates="paragraphs")

class Image(Base):
    __tablename__ = "images"
    
    image_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chapter_id = Column(UUID(as_uuid=True), ForeignKey("chapters.chapter_id", ondelete="CASCADE"), nullable=False)
    image_path = Column(String(1000), nullable=False)
    image_order = Column(Integer, nullable=False)
    width = Column(Integer)
    height = Column(Integer)
    alt = Column(String(500))
    original_format = Column(String(20))
    
    chapter = relationship("Chapter", back_populates="images")

class ReadingHistory(Base):
    __tablename__ = "reading_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    book_id = Column(UUID(as_uuid=True), ForeignKey("books.book_id", ondelete="CASCADE"), nullable=False)
    chapter_id = Column(UUID(as_uuid=True), nullable=False)
    chapter_name = Column(String(500))
    book_title = Column(String(500))
    read_time = Column(DateTime, default=lambda: datetime.now())
    read_duration = Column(Integer, default=0)
    progress = Column(Integer, default=0)

class Favorite(Base):
    __tablename__ = "favorites"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    book_id = Column(UUID(as_uuid=True), ForeignKey("books.book_id", ondelete="CASCADE"), nullable=False)
    add_time = Column(DateTime, default=lambda: datetime.now())

class ReadingList(Base):
    __tablename__ = "reading_list"

    id = Column(Integer, primary_key=True, autoincrement=True)
    book_id = Column(UUID(as_uuid=True), ForeignKey("books.book_id", ondelete="CASCADE"), nullable=False)
    add_time = Column(DateTime, default=lambda: datetime.now())

class BookChapterSummary(Base):
    __tablename__ = "book_chapter_summary"

    summary_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chapter_id = Column(UUID(as_uuid=True), ForeignKey("chapters.chapter_id", ondelete="CASCADE"), nullable=False)
    summary_content = Column(Text, nullable=False)
    model_name = Column(String(100))
    create_time = Column(DateTime, default=lambda: datetime.now())
    update_time = Column(DateTime, default=lambda: datetime.now(), onupdate=lambda: datetime.now())

    chapter = relationship("Chapter", back_populates="summary")

