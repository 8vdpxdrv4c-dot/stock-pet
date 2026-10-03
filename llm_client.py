"""DeepSeek 大模型客户端（OpenAI 兼容接口）。"""
import logging
from datetime import datetime
from knowledge_context import KnowledgeContext
from question_memory import compact_history

logger = logging.getLogger(__name__)
MAX_OUTPUT_TOKENS = 4096
MAX_CONTINUATIONS = 2
CONTINUE_PROMPT = "上一条回复因长度限制中断。请从中断处接着完成原问题的回答，直接续写，不要重复已有内容或重新开头。"
MEMORY_CAPABILITY = (
    "应用记忆能力：本桌宠已启用本地长期记忆，自动保存用户输入并提取重点，"
    "可跨天、跨会话、重启后按相关性检索；不长期保存模型回复。"
    "这项能力由应用提供，不取决于模型自身是否有记忆。"
    "只依据当前上下文和附带的历史输入回答；附带的是部分记录，不代表全部历史。"
    "没有相关记录时说本轮未检索到相关记忆，"
    "不要笼统说没有跨天或长期记忆，也不要承诺完整记住一切。"
    "如果先前回复否认该能力，应根据本轮状态纠正。"
)


class LLMClient:
    def __init__(self, api_key, base_url, model, system_prompt, knowledge_dir=None, question_memory=None):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.system_prompt = system_prompt
        self._client = None
        self.knowledge = KnowledgeContext(knowledge_dir)
        self.question_memory = question_memory

    def _ensure_client(self):
        if self._client is not None:
            return self._client
        try:
            from openai import OpenAI
        except ImportError as e:
            raise RuntimeError("缺少 openai 库，请先 pip install openai") from e
        if not self.api_key or "在此填入" in self.api_key:
            raise RuntimeError("还没配置 DeepSeek API Key")
        self._client = OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=120)
        return self._client

    def chat(self, user_message, history=None):
        client = self._ensure_client()
        history = compact_history(history)
        context = self.knowledge.build(user_message, history)
        memory_context = ""
        memory_capability = ""
        if self.question_memory is not None:
            # Retrieve before saving: the current question is not a past memory.
            memory_context = self.question_memory.build(user_message, history)
            saved = self.question_memory.remember(user_message)
            read_ok = getattr(self.question_memory, "last_read_ok", None)
            memory_capability = MEMORY_CAPABILITY
            memory_capability += "\n当前本地时间：" + datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %z") + "。"
            if read_ok is False:
                memory_capability += "\n本轮历史读取失败；不要把读取失败说成从未保存或没有历史。"
            memory_capability += ("\n本轮输入保存成功。" if saved
                                  else "\n本轮输入保存失败，不要声称已记住或承诺下次可回忆此条输入。")
        system_prompt = "\n\n".join(part for part in
                                   (self.system_prompt, memory_capability, context, memory_context) if part)
        messages = [{"role": "system", "content": system_prompt}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_message})
        parts = []
        for attempt in range(MAX_CONTINUATIONS + 1):
            try:
                resp = client.chat.completions.create(
                    model=self.model, messages=list(messages), temperature=0.8,
                    max_tokens=MAX_OUTPUT_TOKENS)
                choice = resp.choices[0]
                content = choice.message.content or ""
                parts.append(content)
                reply = "".join(parts).strip()
                if not content.strip():
                    return (reply + "\n\n（续写没有返回内容，可发送“继续”重试。）"
                            if reply else "（这次没有收到回复，请再试一次。）")
                if getattr(choice, "finish_reason", None) != "length":
                    return reply
                logger.info("LLM 回复达到输出长度限制，续写 %d/%d", attempt, MAX_CONTINUATIONS)
                if attempt == MAX_CONTINUATIONS:
                    return reply + "\n\n（回复仍未结束，可发送“继续”让我接着说。）"
                messages.extend([
                    {"role": "assistant", "content": content},
                    {"role": "user", "content": CONTINUE_PROMPT},
                ])
            except Exception as e:
                logger.exception("LLM 调用失败")
                if parts:
                    return "".join(parts).strip() + "\n\n（续写暂时失败，已保留收到的内容；可发送“继续”重试。）"
                return f"[联系不上大脑了：{e}]"
