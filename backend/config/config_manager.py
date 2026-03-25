import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

class ConfigManager:
    def __init__(self, config_path: str = None):
        if config_path is None:
            base_dir = Path(__file__).parent.parent
            config_path = base_dir / "config" / "system_config.json"
        self.config_path = Path(config_path)
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            example_path = self.config_path.parent / "system_config.example.json"
            if example_path.exists():
                with open(example_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
                return config
            else:
                raise FileNotFoundError(f"配置文件不存在: {self.config_path}")
        else:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)

    def _save_config(self):
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)
        self.config = self._load_config()

    def get_ai_enabled(self) -> bool:
        return self.config.get('ai_enabled', False)

    def set_ai_enabled(self, enabled: bool):
        self.config['ai_enabled'] = enabled
        self._save_config()

    def get_min_content_length(self) -> int:
        return self.config.get('min_content_length', 300)

    def set_min_content_length(self, length: int):
        self.config['min_content_length'] = length
        self._save_config()

    def get_default_model(self) -> Optional[str]:
        return self.config.get('default_model')

    def set_default_model(self, model_name: str):
        self.config['default_model'] = model_name
        self._save_config()

    def get_models(self) -> List[Dict[str, Any]]:
        self.config = self._load_config()
        return self.config.get('models', [])

    def get_model(self, model_name: str) -> Optional[Dict[str, Any]]:
        models = self.get_models()
        for model in models:
            if model.get('name') == model_name:
                return model
        return None

    def add_model(self, model: Dict[str, Any]):
        models = self.get_models()
        existing_index = None
        for i, m in enumerate(models):
            if m.get('name') == model.get('name'):
                existing_index = i
                break

        if existing_index is not None:
            models[existing_index] = model
        else:
            models.append(model)

        self.config['models'] = models
        self._save_config()

    def remove_model(self, model_name: str):
        models = self.get_models()
        models = [m for m in models if m.get('name') != model_name]
        self.config['models'] = models
        self._save_config()

        if self.get_default_model() == model_name and models:
            self.set_default_model(models[0]['name'])
        elif not models:
            self.config['default_model'] = None
            self._save_config()

    def update_model(self, model_name: str, updates: Dict[str, Any]):
        model = self.get_model(model_name)
        if model:
            for key, value in updates.items():
                if key == 'parameters' and isinstance(value, dict):
                    if 'parameters' not in model:
                        model['parameters'] = {}
                    model['parameters'].update(value)
                else:
                    model[key] = value
            self.add_model(model)

    def get_prompt(self, prompt_type: str = 'summary') -> Optional[str]:
        prompts = self.config.get('prompts', {})
        return prompts.get(prompt_type)

    def set_prompt(self, prompt_type: str, prompt_template: str):
        if 'prompts' not in self.config:
            self.config['prompts'] = {}
        self.config['prompts'][prompt_type] = prompt_template
        self._save_config()

    def get_all_config(self) -> Dict[str, Any]:
        config_copy = self.config.copy()
        for model in config_copy.get('models', []):
            if model.get('api_key'):
                model['api_key'] = '***' if len(model['api_key']) > 4 else '****'
        return config_copy

config_manager = ConfigManager()
