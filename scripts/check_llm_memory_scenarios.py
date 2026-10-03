"""Run ten real-model scenarios using isolated, temporary question memory.

This is an opt-in integration test: it uses the configured API and incurs usage.
No mocks or user-profile memory are used. Reports contain synthetic test inputs.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config import load_config
from knowledge_context import KnowledgeContext
from llm_client import LLMClient
from question_memory import QuestionMemory


SCENARIOS = [
    {"id": 1, "name": "真实知识：止损三分法", "turns": [
        "请根据本地知识库解释止损规则的三种类型、作者最喜欢哪一种，并标明资料标题或来源。150字以内。"],
     "source": "trading-psychology/stop-loss-discipline/SKILL.md",
     "groups": [["价格"], ["指标"], ["时间"], ["止损纪律", "斯蒂恩博格", "投资交易心理分析"]]},
    {"id": 2, "name": "真实知识：商业模式来源", "turns": [
        "根据本地知识库中的段永平商业模式评估，解释差异化、护城河、定价能力的关系，并写出来源。150字以内。"],
     "source": "duan-yongping/business-model-evaluator/SKILL.md",
     "groups": [["差异化"], ["护城河"], ["定价"], ["段永平"]]},
    {"id": 3, "name": "知识缺失时不编造来源", "turns": [
        "本地知识库有没有《月球温室种植手册》第17章？请逐字引用该章关于月球番茄的原文并写出页码。没有资料就明确说没有，不要编造。100字以内。"],
     "no_body": True, "groups": [["没有", "未找到", "不包含", "无法", "找不到"]]},
    {"id": 4, "name": "无关话题不硬套投资知识", "turns": [
        "怎么把煮鸡蛋的蛋壳剥完整？只给日常操作步骤，100字以内。"],
     "no_body": True, "groups": [["水"], ["壳"]],
     "forbidden": ["巴菲特", "段永平", "止损", "护城河", "投资交易心理分析"]},
    {"id": 5, "name": "最近一轮输入的精确记忆", "turns": [
        "以下是虚构测试资料：我的练习计划代号是青松731，复盘时间是每天21:17。请记住，回复收到即可。",
        "我刚才输入的练习计划代号、复盘时间分别是什么？只回答这两项。"],
     "groups": [["青松731"], ["21:17", "21：17"]]},
    {"id": 6, "name": "超出两轮后检索原始输入", "turns": [
        "以下是虚构测试资料：我的练习计划代号是紫竹842，复盘时间是每天20:43。请记住，回复收到即可。",
        "煮鸡蛋剥壳有什么小技巧？30字以内。",
        "书桌怎么收拾整齐？30字以内。",
        "我之前说的练习计划代号和复盘时间分别是什么？只回答这两项，不要猜。"],
     "groups": [["紫竹842"], ["20:43", "20：43"]], "memory_contains": ["紫竹842", "20:43"]},
    {"id": 7, "name": "重启客户端后检索输入", "turns": [
        "以下是虚构测试资料：我的练习计划代号是银杏953，复盘时间是每天19:26。请记住，回复收到即可。",
        "我以前输入的练习计划代号和复盘时间是什么？只回答这两项，不要猜。"],
     "restart_before": [1], "groups": [["银杏953"], ["19:26", "19：26"]],
     "memory_contains": ["银杏953", "19:26"]},
    {"id": 8, "name": "更正后重启：新值覆盖旧值", "turns": [
        "以下是虚构测试资料：我的练习计划代号是旧杉164，复盘时间是每天18:12。请记住，回复收到即可。",
        "更正前面的练习计划：代号改为新杉275，复盘时间改为每天22:38，旧杉164和18:12都作废。请记住最新值，回复收到即可。",
        "我目前有效的练习计划代号和复盘时间是什么？只回答当前值，不要列旧值。"],
     "restart_before": [2], "groups": [["新杉275"], ["22:38", "22：38"]],
     "forbidden": ["旧杉164", "18:12", "18：12"], "memory_contains": ["新杉275", "22:38"]},
    {"id": 9, "name": "长输入中部细节的记忆边界", "turns": [
        "以下是虚构长文记忆测试记录。" + "背景说明：今天整理练习素材，关注记录的完整性。" * 35
        + "关键记录：长文记忆测试记录的中部识别码为雪桥486。"
        + "补充说明：后续只核对记录中的信息，不自行补充。" * 35
        + "请记住这份长文记忆测试记录，回复收到即可。",
        "我之前输入的长文记忆测试记录，中部识别码是什么？只回答识别码；不知道就明确说不知道，不要猜。"],
     "restart_before": [1], "groups": [["雪桥486"]], "memory_contains": ["雪桥486"]},
    {"id": 10, "name": "不冒称记住未保存的模型回复", "turns": [
        "请给我的虚构练习计划随机生成一个八位大写英文字母代号，只回复代号。不要使用常见单词。",
        "你上次给练习计划随机生成的八位代号是什么？必须逐字复述。如果没有保存上次回复就明确说无法知道，不要重新生成。"],
     "restart_before": [1], "groups": [["没有", "无法", "未保存", "不保存", "不知道", "不能"]]},
]


class RecordingCompletions:
    def __init__(self, delegate):
        self.delegate = delegate
        self.calls = []

    def create(self, **kwargs):
        messages = kwargs["messages"]
        system = messages[0]["content"]
        memory_start = system.find("历史问题记忆（")
        capability_start = system.find("应用记忆能力：")
        capability = system[capability_start:].split("\n\n", 1)[0] if capability_start >= 0 else ""
        self.calls.append({
            "selected_sources": re.findall(r"^### 文件：(.+)$", system, re.MULTILINE),
            "memory_context": system[memory_start:] if memory_start >= 0 else "",
            "memory_capability": capability,
            "recent_history": messages[1:-1],
            "user_message": messages[-1]["content"],
            "system_chars": len(system),
        })
        response = self.delegate.create(**kwargs)
        usage = getattr(response, "usage", None)
        self.calls[-1]["usage"] = usage.model_dump() if usage else None
        self.calls[-1]["finish_reason"] = response.choices[0].finish_reason
        return response


def run_scenario(case, cfg, knowledge_root, memory_path):
    history, turns = [], []

    def new_client():
        client = LLMClient(cfg["deepseek_api_key"], cfg["deepseek_base_url"],
                           cfg["deepseek_model"], cfg["system_prompt"],
                           knowledge_root, QuestionMemory(memory_path))
        real_client = client._ensure_client()
        recorder = RecordingCompletions(real_client.chat.completions)
        client._client = SimpleNamespace(chat=SimpleNamespace(completions=recorder))
        return client, recorder, real_client

    client, recorder, real_client = new_client()
    try:
        for index, question in enumerate(case["turns"]):
            restarted = index in case.get("restart_before", [])
            if restarted:
                real_client.close()
                client, recorder, real_client = new_client()
                history = []
            start = time.monotonic()
            first_call = len(recorder.calls)
            # Matches chat_panel: only the last two turns are passed to LLMClient.
            reply = client.chat(question, history[-4:])
            calls = recorder.calls[first_call:]
            turns.append({"question": question, "reply": reply, "restart": restarted,
                          "seconds": round(time.monotonic() - start, 2), "requests": calls})
            history.extend([{"role": "user", "content": question},
                            {"role": "assistant", "content": reply}])
    finally:
        real_client.close()
    final = turns[-1]
    request = final["requests"][0] if final["requests"] else {}
    reply = final["reply"]
    checks = {
        "all_turns_received_response": all(t["reply"] and not t["reply"].startswith("[联系不上") for t in turns),
        "answer_contains_required_items": all(any(term in reply for term in group) for group in case["groups"]),
        "answer_avoids_forbidden_items": not any(term in reply for term in case.get("forbidden", [])),
        "expected_source_in_request": not case.get("source") or case["source"] in request.get("selected_sources", []),
        "unrelated_body_not_loaded": not case.get("no_body") or not request.get("selected_sources"),
        "required_memory_reached_model": all(term in request.get("memory_context", "") for term in case.get("memory_contains", [])),
    }
    if case["id"] == 10:
        checks["previous_answer_not_in_request"] = turns[0]["reply"] not in json.dumps(request, ensure_ascii=False)
    return {"id": case["id"], "name": case["name"], "passed": all(checks.values()),
            "checks": checks, "turns": turns}


def write_report(path, cfg, rows):
    document = {"date": datetime.now().astimezone().isoformat(timespec="seconds"),
                "mode": "real configured LLM; copied real knowledge; isolated synthetic memory",
                "model": cfg["deepseek_model"], "base_url": cfg["deepseek_base_url"],
                "criteria": "Rule-based content and request checks; full replies retained for human review. Not an LLM judge.",
                "passed": sum(row["passed"] for row in rows), "total": len(rows),
                "api_calls": sum(len(turn["requests"]) for row in rows for turn in row["turns"]),
                "results": sorted(rows, key=lambda row: row["id"])}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=ROOT / "tests/llm_memory_scenario_report.json")
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    cfg = load_config()
    if not cfg["deepseek_api_key"]:
        raise RuntimeError("No configured API key; no live scenarios were run.")
    rows = []
    with tempfile.TemporaryDirectory(prefix="stockpet-llm-scenarios-") as folder:
        base = Path(folder)
        knowledge_root = base / "knowledge"
        shutil.copytree(ROOT / "knowledge", knowledge_root)
        KnowledgeContext(knowledge_root).read_entries()
        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
            futures = {pool.submit(run_scenario, case, cfg, knowledge_root,
                                   base / f"case-{case['id']}.sqlite3"): case for case in SCENARIOS}
            for future in as_completed(futures):
                case = futures[future]
                try:
                    row = future.result()
                except Exception as error:
                    row = {"id": case["id"], "name": case["name"], "passed": False,
                           "checks": {"scenario_completed": False}, "turns": [],
                           "error_type": type(error).__name__}
                rows.append(row)
                write_report(args.report, cfg, rows)
                print(f"{'PASS' if row['passed'] else 'FAIL'} {row['id']:02d} {row['name']}", flush=True)
    print(f"{sum(row['passed'] for row in rows)}/{len(rows)} scenarios passed; {args.report}", flush=True)
    return 0 if all(row["passed"] for row in rows) else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
