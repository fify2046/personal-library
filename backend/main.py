import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api import books, chapters, images, reading, favorites, reading_list, system_config, ai_summary
from db.config import config

app = FastAPI(
    title="E-Book API",
    description="Personal E-Book Display System API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(books.router)
app.include_router(chapters.router)
app.include_router(images.router)
app.include_router(reading.router)
app.include_router(favorites.router)
app.include_router(reading_list.router)
app.include_router(system_config.router)
app.include_router(ai_summary.router)

@app.get("/")
def root():
    return {"message": "E-Book API is running", "docs": "/docs"}

if __name__ == "__main__":
    os.makedirs(config.IMAGES_DIR, exist_ok=True)
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=12001)
