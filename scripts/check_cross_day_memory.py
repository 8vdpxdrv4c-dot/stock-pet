"""Opt-in real-model checks with simulated previous-day input timestamps."""
from contextlib import closing
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import shutil
import sqlite3
import sys
import tempfile
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config import load_config
from llm_client import LLMClient
from question_memory import QuestionMemory
from scripts.check_llm_memory_scenarios import RecordingCompletions

SEED = "以下为虚构测试资料：我今天参加了项目讨论，项目代号是雪桥486。"
CASES = [
    {"name": "无历史时正确说明跨天能力", "question": "你有没有跨天自动记忆功能？100字以内。",
     "groups": [["跨天"], ["本地", "应用"], ["输入"]]},
    {"name": "纠正上一轮的错误否认", "question": "你刚才说没有跨天自动记忆，是真的吗？请按当前应用实际能力回答，100字以内。",
     "history": [{"role": "user", "content": "你能跨天记住我说的事情吗？"},
                 {"role": "assistant", "content": "我没有跨天自动记忆。"}],
     "groups": [["跨天"], ["本地", "应用"], ["输入"]]},
    {"name": "重建客户端后宽泛回忆旧记录", "question": "你还记得我什么？", "seed": True,
     "groups": [["雪桥486"], ["项目讨论"]], "memory_required": True},
    {"name": "相对日期按保存日期解释", "question": "我昨天做了什么？", "seed": True,
     "groups": [["项目讨论"]], "memory_required": True},
    {"name": "跨天精确回忆代号", "question": "我昨天说的项目代号是什么？", "seed": True,
     "groups": [["雪桥486"]], "memory_required": True},
    {"name": "未检索到时不编造记忆", "question": "我以前说过的火星温室密码是什么？", "seed": True,
     "groups": [["未", "没有", "没找到", "不知道", "无法"]], "no_matching_memory": True},
]


def main():
    cfg = load_config()
    rows = []
    if not cfg["deepseek_api_key"]:
        raise RuntimeError("No configured API key; no live calls made.")
    with tempfile.TemporaryDirectory(prefix="stockpet-cross-day-") as folder:
        base = Path(folder)
        knowledge = base / "knowledge"
        shutil.copytree(ROOT / "knowledge", knowledge)
        for index, case in enumerate(CASES, 1):
            path = base / f"case-{index}.sqlite3"
            memory = QuestionMemory(path)
            previous_day = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(timespec="seconds")
            if case.get("seed"):
                assert memory.remember(SEED)
                with closing(sqlite3.connect(path)) as db:
                    db.execute("UPDATE questions SET first_asked = ?, last_asked = ?", (previous_day, previous_day))
                    db.commit()
            # Construct a new object; there is no temporary chat history for seeds.
            client = LLMClient(cfg["deepseek_api_key"], cfg["deepseek_base_url"],
                               cfg["deepseek_model"], cfg["system_prompt"], knowledge, QuestionMemory(path))
            real = client._ensure_client()
            recorder = RecordingCompletions(real.chat.completions)
            client._client = SimpleNamespace(chat=SimpleNamespace(completions=recorder))
            try:
                reply = client.chat(case["question"], case.get("history"))
            finally:
                real.close()
            request = recorder.calls[0]
            checks = {
                "received_reply": bool(reply) and not reply.startswith("[联系不上"),
                "expected_reply_content": all(any(word in reply for word in group) for group in case["groups"]),
                "capability_reached_model": "可跨天" in request["memory_capability"],
                "does_not_deny_app_capability": not re.search(
                    r"(?:我|本应用|这个应用)(?:确实)?(?:没有|不能|不具备).{0,8}(?:跨天|长期)(?:自动)?记忆", reply),
                "required_memory_reached_model": not case.get("memory_required") or "雪桥486" in request["memory_context"],
                "no_unrelated_memory": not case.get("no_matching_memory") or not request["memory_context"],
            }
            rows.append({"id": index, "name": case["name"], "question": case["question"],
                         "seed": SEED if case.get("seed") else None,
                         "simulated_seed_time": previous_day if case.get("seed") else None,
                         "reply": reply, "passed": all(checks.values()), "checks": checks, "requests": recorder.calls})
            print(f"{'PASS' if all(checks.values()) else 'FAIL'} {index} {case['name']}", flush=True)
    report = {"date": datetime.now().astimezone().isoformat(timespec="seconds"), "model": cfg["deepseek_model"],
              "mode": "real API; isolated test memory; previous-day timestamps simulated, no 24-hour wait",
              "passed": sum(row["passed"] for row in rows), "total": len(rows), "results": rows}
    path = ROOT / "tests/cross_day_memory_report.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{report['passed']}/{report['total']} passed; {path}")
    return 0 if all(row["passed"] for row in rows) else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
