from sqlalchemy import create_engine, text
from db.config import config

engine = create_engine(config.DATABASE_URL)

sql = """
CREATE TABLE IF NOT EXISTS reading_history (
    id SERIAL PRIMARY KEY,
    book_id UUID NOT NULL REFERENCES books(book_id) ON DELETE CASCADE,
    chapter_id UUID NOT NULL,
    chapter_name VARCHAR(500),
    book_title VARCHAR(500),
    read_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_reading_history_book_id ON reading_history(book_id);
CREATE INDEX IF NOT EXISTS idx_reading_history_read_time ON reading_history(read_time DESC);
"""

with engine.connect() as conn:
    conn.execute(text(sql))
    conn.commit()
    print("Table created successfully!")
