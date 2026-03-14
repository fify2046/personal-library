import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from db.config import config

router = APIRouter(prefix="/api/images", tags=["images"])

@router.get("/{image_path:path}")
async def get_image(image_path: str):
    image_path_normalized = image_path.replace('/', os.sep)
    full_path = os.path.join(config.IMAGES_DIR, image_path_normalized)
    full_path = os.path.normpath(full_path)
    
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail=f"Image not found: {full_path}")
    
    ext = os.path.splitext(full_path)[1].lower()
    media_types = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp',
        '.svg': 'image/svg+xml'
    }
    
    media_type = media_types.get(ext, 'application/octet-stream')
    
    return FileResponse(full_path, media_type=media_type)
