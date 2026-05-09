from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from config import config_manager

router = APIRouter(prefix="/api/config", tags=["system-config"])

class AIModelConfig(BaseModel):
    name: str
    platform: str
    api_protocol: str = 'openai-completions'
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    local_model_path: Optional[str] = None
    parameters: Dict[str, Any] = {}
    rate_limit: int = 1

class SystemConfigResponse(BaseModel):
    ai_enabled: bool
    default_model: Optional[str]
    models: List[AIModelConfig]
    prompts: Dict[str, str]
    prompt_templates: List[Dict[str, Any]]

class AIModelCreateRequest(BaseModel):
    name: str
    platform: str
    api_protocol: str = 'openai-completions'
    api_key: str
    base_url: str
    local_model_path: Optional[str] = None
    parameters: Dict[str, Any] = {
        "temperature": 0.7,
        "max_tokens": 1000
    }
    rate_limit: int = 1

class AIModelUpdateRequest(BaseModel):
    platform: Optional[str] = None
    api_protocol: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    local_model_path: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    rate_limit: Optional[int] = None

class PromptUpdateRequest(BaseModel):
    prompt_type: str
    prompt_template: str

class PromptTemplateCreateRequest(BaseModel):
    name: str
    description: Optional[str] = ''
    prompt_template: str
    model_name: Optional[str] = None

class PromptTemplateUpdateRequest(BaseModel):
    description: Optional[str] = None
    prompt_template: Optional[str] = None
    model_name: Optional[str] = None

@router.get("", response_model=SystemConfigResponse)
def get_config():
    config = config_manager.get_all_config()
    config['models'] = config_manager.get_models()
    config['prompt_templates'] = config_manager.get_prompt_templates()
    return SystemConfigResponse(**config)

@router.put("/ai-enabled")
def update_ai_enabled(enabled: bool):
    config_manager.set_ai_enabled(enabled)
    return {"success": True, "message": "AI功能已" + ("开启" if enabled else "关闭")}

@router.put("/default-model")
def update_default_model(model_name: str):
    model = config_manager.get_model(model_name)
    if not model:
        raise HTTPException(status_code=404, detail="模型不存在")
    config_manager.set_default_model(model_name)
    return {"success": True, "message": f"默认模型已设置为: {model_name}"}

@router.get("/min-content-length")
def get_min_content_length():
    return {"min_content_length": config_manager.get_min_content_length()}

@router.put("/min-content-length")
def update_min_content_length(length: int):
    if length < 0 or length > 10000:
        raise HTTPException(status_code=400, detail="字数限制应在0-10000之间")
    config_manager.set_min_content_length(length)
    return {"success": True, "message": f"最小内容字数已设置为: {length}"}

@router.post("/models")
def create_model(model: AIModelCreateRequest):
    model_dict = model.dict()
    config_manager.add_model(model_dict)
    return {"success": True, "message": f"模型 {model.name} 已添加"}

@router.put("/models/{model_name}")
def update_model(model_name: str, updates: AIModelUpdateRequest):
    model = config_manager.get_model(model_name)
    if not model:
        raise HTTPException(status_code=404, detail="模型不存在")

    updates_dict = updates.dict(exclude_unset=True)
    config_manager.update_model(model_name, updates_dict)
    return {"success": True, "message": f"模型 {model_name} 已更新"}

@router.delete("/models/{model_name}")
def delete_model(model_name: str):
    model = config_manager.get_model(model_name)
    if not model:
        raise HTTPException(status_code=404, detail="模型不存在")
    config_manager.remove_model(model_name)
    return {"success": True, "message": f"模型 {model_name} 已删除"}

@router.get("/models")
def list_models():
    return config_manager.get_models()

@router.get("/models/{model_name}")
def get_model(model_name: str):
    model = config_manager.get_model(model_name)
    if not model:
        raise HTTPException(status_code=404, detail="模型不存在")
    return model

@router.put("/prompts")
def update_prompt(request: PromptUpdateRequest):
    config_manager.set_prompt(request.prompt_type, request.prompt_template)
    return {"success": True, "message": f"提示词已更新"}

@router.get("/prompts")
def get_prompts():
    return config_manager.config.get('prompts', {})

@router.post("/prompt-templates")
def create_prompt_template(request: PromptTemplateCreateRequest):
    existing = config_manager.get_prompt_template(request.name)
    if existing:
        raise HTTPException(status_code=400, detail="模板名称已存在")
    template = {
        "name": request.name,
        "description": request.description or '',
        "prompt_template": request.prompt_template,
        "model_name": request.model_name
    }
    config_manager.add_prompt_template(template)
    return {"success": True, "message": f"模板 {request.name} 已添加"}

@router.put("/prompt-templates/{template_name}")
def update_prompt_template(template_name: str, request: PromptTemplateUpdateRequest):
    template = config_manager.get_prompt_template(template_name)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    updates = {}
    if request.description is not None:
        updates['description'] = request.description
    if request.prompt_template is not None:
        updates['prompt_template'] = request.prompt_template
    if request.model_name is not None:
        updates['model_name'] = request.model_name
    if updates:
        for key, value in updates.items():
            template[key] = value
        config_manager.add_prompt_template(template)
    return {"success": True, "message": f"模板 {template_name} 已更新"}

@router.delete("/prompt-templates/{template_name}")
def delete_prompt_template(template_name: str):
    template = config_manager.get_prompt_template(template_name)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    config_manager.remove_prompt_template(template_name)
    return {"success": True, "message": f"模板 {template_name} 已删除"}

@router.get("/prompt-templates")
def list_prompt_templates():
    return config_manager.get_prompt_templates()

@router.get("/prompt-templates/{template_name}")
def get_prompt_template(template_name: str):
    template = config_manager.get_prompt_template(template_name)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    return template

@router.get("/models/{model_name}/rate-limit")
def get_model_rate_limit(model_name: str):
    rate_limit = config_manager.get_model_rate_limit(model_name)
    return {"model_name": model_name, "rate_limit": rate_limit}

@router.put("/models/{model_name}/rate-limit")
def update_model_rate_limit(model_name: str, rate_limit: int):
    if rate_limit < 1 or rate_limit > 10:
        raise HTTPException(status_code=400, detail="限速设置应在1-10次/秒之间")
    config_manager.set_model_rate_limit(model_name, rate_limit)
    return {"success": True, "message": f"模型 {model_name} 的限速已设置为 {rate_limit} 次/秒"}
