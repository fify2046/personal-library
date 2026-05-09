from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from db.database import get_db
from db.models import Book, Chapter, Paragraph, BookChapterSummary
from config import config_manager
from ai import create_ai_service
from datetime import datetime
import logging
import time
import threading

logger = logging.getLogger(__name__)

class RateLimiter:
    def __init__(self):
        self.call_times = {}
        self.lock = threading.Lock()

    def acquire(self, model_name: str, rate_limit: int) -> bool:
        current_time = time.time()
        with self.lock:
            if model_name not in self.call_times:
                self.call_times[model_name] = []
            self.call_times[model_name] = [
                t for t in self.call_times[model_name]
                if current_time - t < 1.0
            ]
            if len(self.call_times[model_name]) < rate_limit:
                self.call_times[model_name].append(current_time)
                return True
            return False

    def wait_for_slot(self, model_name: str, rate_limit: int, timeout: float = 60):
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.acquire(model_name, rate_limit):
                return True
            time.sleep(0.1)
        return False

rate_limiter = RateLimiter()

router = APIRouter(prefix="/api/ai", tags=["ai"])

class ChapterSummaryResponse(BaseModel):
    summary_id: str
    chapter_id: str
    summary_content: str
    model_name: Optional[str]
    create_time: str
    update_time: str

    class Config:
        from_attributes = True

class GenerateSummaryRequest(BaseModel):
    chapter_ids: List[str]
    model_name: Optional[str] = None
    template_name: Optional[str] = None

class GenerateSummaryResponse(BaseModel):
    success: bool
    message: str
    summaries: List[ChapterSummaryResponse]

@router.get("/status")
def get_ai_status():
    default_model = config_manager.get_default_model()
    model_config = config_manager.get_model(default_model) if default_model else None
    timeout = model_config.get('parameters', {}).get('timeout', 120) if model_config else 120

    return {
        "ai_enabled": config_manager.get_ai_enabled(),
        "default_model": default_model,
        "available_models": [m['name'] for m in config_manager.get_models()],
        "timeout": timeout * 1000
    }

@router.get("/summary/{chapter_id}", response_model=ChapterSummaryResponse)
def get_chapter_summary(chapter_id: str, db: Session = Depends(get_db)):
    if not config_manager.get_ai_enabled():
        raise HTTPException(status_code=403, detail="AI辅助阅读功能未开启")

    summary = db.query(BookChapterSummary).filter(
        BookChapterSummary.chapter_id == chapter_id
    ).first()

    if not summary:
        raise HTTPException(status_code=404, detail="该章节暂无AI摘要")

    return ChapterSummaryResponse(
        summary_id=str(summary.summary_id),
        chapter_id=str(summary.chapter_id),
        summary_content=summary.summary_content,
        model_name=summary.model_name,
        create_time=summary.create_time.isoformat() if summary.create_time else "",
        update_time=summary.update_time.isoformat() if summary.update_time else ""
    )

@router.post("/summary/generate", response_model=GenerateSummaryResponse)
def generate_summary(request: GenerateSummaryRequest, db: Session = Depends(get_db)):
    if not config_manager.get_ai_enabled():
        raise HTTPException(status_code=403, detail="AI辅助阅读功能未开启")

    model_name = request.model_name or config_manager.get_default_model()
    if not model_name:
        raise HTTPException(status_code=400, detail="未配置默认AI模型，请在系统设置中配置")

    model_config = config_manager.get_model(model_name)
    if not model_config:
        raise HTTPException(status_code=404, detail=f"未找到模型: {model_name}")

    if not model_config.get('api_key'):
        raise HTTPException(status_code=400, detail=f"模型 {model_name} 未配置API密钥")

    prompt_template = None
    template_name = request.template_name
    if template_name:
        template = config_manager.get_prompt_template(template_name)
        if template:
            prompt_template = template.get('prompt_template')
            if template.get('model_name') and not request.model_name:
                model_name = template['model_name']
                model_config = config_manager.get_model(model_name)
                if not model_config:
                    raise HTTPException(status_code=404, detail=f"模板关联的模型 {model_name} 不存在")

    if not prompt_template:
        prompt_template = config_manager.get_prompt('summary')
    if not prompt_template:
        raise HTTPException(status_code=400, detail="未配置摘要生成提示词")

    rate_limit = model_config.get('rate_limit', 1)

    try:
        ai_service = create_ai_service(
            api_key=model_config['api_key'],
            base_url=model_config['base_url'],
            model_name=model_config['name'],
            parameters=model_config.get('parameters', {}),
            api_protocol=model_config.get('api_protocol', 'openai'),
            local_model_path=model_config.get('local_model_path')
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI服务初始化失败: {str(e)}")

    summaries = []
    errors = []

    for chapter_id in request.chapter_ids:
        try:
            if not rate_limiter.wait_for_slot(model_name, rate_limit, timeout=300):
                errors.append(f"章节 {chapter_id} 限速等待超时")
                continue

            chapter = db.query(Chapter).filter(Chapter.chapter_id == chapter_id).first()
            if not chapter:
                errors.append(f"章节 {chapter_id} 不存在")
                continue

            paragraphs = db.query(Paragraph).filter(
                Paragraph.chapter_id == chapter_id,
                Paragraph.is_footnote == False
            ).order_by(Paragraph.para_order).all()

            content = "\n".join([p.content for p in paragraphs if p.content and p.content.strip()])

            min_length = config_manager.get_min_content_length()
            if not content or len(content) < min_length:
                errors.append(f"章节 '{chapter.chapter_name}' 内容不足{min_length}字，跳过")
                continue

            logger.info(f"开始为章节 {chapter.chapter_name} 生成摘要...")

            summary_text = ai_service.generate_summary(
                content=content,
                chapter_name=chapter.chapter_name or "未命名章节",
                prompt_template=prompt_template
            )

            logger.info(f"AI摘要生成成功，长度: {len(summary_text)} 字符")

            existing_summary = db.query(BookChapterSummary).filter(
                BookChapterSummary.chapter_id == chapter_id
            ).first()

            if existing_summary:
                existing_summary.summary_content = summary_text
                existing_summary.model_name = model_name
                existing_summary.update_time = datetime.now()
                summary = existing_summary
                logger.info(f"更新已有摘要: {existing_summary.summary_id}")
            else:
                summary = BookChapterSummary(
                    chapter_id=chapter_id,
                    summary_content=summary_text,
                    model_name=model_name
                )
                db.add(summary)
                logger.info(f"添加新摘要到会话")

            db.commit()
            logger.info(f"提交数据库成功")
            db.refresh(summary)
            logger.info(f"刷新实体成功, summary_id: {summary.summary_id}")

            summaries.append(ChapterSummaryResponse(
                summary_id=str(summary.summary_id),
                chapter_id=str(summary.chapter_id),
                summary_content=summary.summary_content,
                model_name=summary.model_name,
                create_time=summary.create_time.isoformat() if summary.create_time else "",
                update_time=summary.update_time.isoformat() if summary.update_time else ""
            ))

        except Exception as e:
            db.rollback()
            logger.error(f"生成摘要时发生错误: {str(e)}", exc_info=True)
            chapter_name = db.query(Chapter).filter(Chapter.chapter_id == chapter_id).first()
            chapter_name_str = chapter_name.chapter_name if chapter_name else chapter_id
            errors.append(f"章节 '{chapter_name_str}' 生成失败: {str(e)}")

    message = f"成功生成 {len(summaries)} 个摘要"
    if errors:
        message += f"，{len(errors)} 个失败"

    return GenerateSummaryResponse(
        success=len(summaries) > 0,
        message=message,
        summaries=summaries
    )

@router.delete("/summary/{chapter_id}")
def delete_summary(chapter_id: str, db: Session = Depends(get_db)):
    summary = db.query(BookChapterSummary).filter(
        BookChapterSummary.chapter_id == chapter_id
    ).first()

    if not summary:
        raise HTTPException(status_code=404, detail="该章节暂无AI摘要")

    db.delete(summary)
    db.commit()

    return {"success": True, "message": "AI摘要已删除"}
