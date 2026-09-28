"""DeepSeek 大模型客户端（OpenAI 兼容接口）。"""
import logging

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self, api_key, base_url, model, system_prompt):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.system_prompt = system_prompt
        self._client = None

    def _ensure_client(self):
        if self._client is not None:
            return self._client
        try:
            from openai import OpenAI
        except ImportError as e:
            raise RuntimeError("缺少 openai 库，请先 pip install openai") from e
        if not self.api_key or "在此填入" in self.api_key:
            raise RuntimeError("还没配置 DeepSeek API Key")
        self._client = OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=30)
        return self._client

    def chat(self, user_message, history=None):
        client = self._ensure_client()
        messages = [{"role": "system", "content": self.system_prompt}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_message})
        try:
            resp = client.chat.completions.create(model=self.model, messages=messages, temperature=0.8, max_tokens=300)
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logger.exception("LLM 调用失败")
            return f"[小戒联系不上大脑了：{e}]"
