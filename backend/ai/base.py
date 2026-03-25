from abc import ABC, abstractmethod
from typing import Dict, Any, List


class BaseAIService(ABC):
    def __init__(self, api_key: str, base_url: str, model_name: str, parameters: Dict[str, Any]):
        self.api_key = api_key
        self.base_url = base_url
        self.model_name = model_name
        self.parameters = parameters

    @abstractmethod
    def generate_summary(self, content: str, chapter_name: str, prompt_template: str) -> str:
        pass

    def format_prompt(self, prompt_template: str, chapter_name: str, content: str) -> str:
        return prompt_template.replace('{chapter_name}', chapter_name).replace('{content}', content)


class OpenAIService(BaseAIService):
    def generate_summary(self, content: str, chapter_name: str, prompt_template: str) -> str:
        try:
            import openai

            base_url = self.base_url.rstrip('/')
            if base_url.endswith('/chat/completions'):
                base_url = base_url[:-len('/chat/completions')]

            client = openai.OpenAI(api_key=self.api_key, base_url=base_url)
            prompt = self.format_prompt(prompt_template, chapter_name, content)

            messages = [
                {"role": "system", "content": "你是一个专业的图书阅读助手。"},
                {"role": "user", "content": prompt}
            ]

            kwargs = {
                "model": self.model_name,
                "messages": messages,
                "temperature": self.parameters.get('temperature', 0.7),
            }

            max_tokens = self.parameters.get('max_tokens')
            if max_tokens:
                kwargs["max_tokens"] = max_tokens

            timeout = self.parameters.get('timeout', 120)
            response = client.chat.completions.create(**kwargs, timeout=timeout)

            return response.choices[0].message.content

        except Exception as e:
            raise Exception(f"OpenAI API调用失败: {str(e)}")


class AnthropicService(BaseAIService):
    def generate_summary(self, content: str, chapter_name: str, prompt_template: str) -> str:
        try:
            import anthropic
            prompt = self.format_prompt(prompt_template, chapter_name, content)

            client = anthropic.Anthropic(
                api_key=self.api_key,
                base_url=self.base_url.rstrip('/')
            )

            max_tokens = self.parameters.get('max_tokens', 1000)
            timeout = self.parameters.get('timeout', 120)

            message = client.messages.create(
                model=self.model_name,
                max_tokens=max_tokens,
                system="你是一个专业的图书阅读助手。",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                timeout=timeout
            )

            if message.content and len(message.content) > 0:
                for block in message.content:
                    if hasattr(block, 'text') and block.text:
                        return block.text
            return str(message)

        except Exception as e:
            raise Exception(f"Anthropic API调用失败: {str(e)}")


def create_ai_service(
    api_key: str,
    base_url: str,
    model_name: str,
    parameters: Dict[str, Any],
    api_protocol: str = 'openai-completions',
    local_model_path: str = None
) -> BaseAIService:
    model = model_name
    if local_model_path:
        model = local_model_path

    if api_protocol == 'anthropic-messages':
        return AnthropicService(api_key, base_url, model, parameters)
    else:
        return OpenAIService(api_key, base_url, model, parameters)
