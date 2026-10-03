"""Exercise real knowledge retrieval and request assembly without a network call."""
import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm_client import LLMClient


def run_cases():
    cases = json.loads((ROOT / "tests/knowledge_trigger_cases.json").read_text(encoding="utf-8"))
    client = LLMClient("fake", "https://invalid.example", "test", "测试角色", ROOT / "knowledge")
    create = Mock(return_value=SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="模拟响应"))]))
    client._client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    rows = []
    for case in cases:
        client.chat(case["question"])
        prompt = create.call_args.kwargs["messages"][0]["content"]
        paths = re.findall(r"^### 文件：(.+)$", prompt, re.MULTILINE)
        slugs = [Path(path).parent.name for path in paths]
        expected = case["expected"]
        rank = slugs.index(expected) + 1 if expected in slugs else None
        selection_ok = (rank is not None and rank <= case.get("max_rank", 6)) if expected else not paths
        # Check full bodies are actually in the API request, not just catalog labels.
        contents = [(ROOT / "knowledge" / path).read_text(encoding="utf-8-sig").strip() for path in paths]
        injected = all(f"### 文件：{path}\n{body}\n### 文件结束：{path}" in prompt
                       for path, body in zip(paths, contents))
        budget_ok = len(paths) <= 6 and sum(map(len, contents)) <= 32000
        rows.append({**case, "passed": selection_ok and injected and budget_ok,
                     "rank": rank, "bodies_in_request": injected, "within_budget": budget_ok,
                     "selected": paths})
    return rows


if __name__ == "__main__":
    rows = run_cases()
    report = {"mode": "mocked API; real knowledge retrieval and request construction",
              "criteria": "Expected documents must be included (specified ranks enforced); negative cases must select no bodies. All bodies and budget limits are checked.",
              "passed": sum(row["passed"] for row in rows), "total": len(rows), "results": rows}
    (ROOT / "tests/knowledge_trigger_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for row in rows:
        print("PASS" if row["passed"] else "FAIL", row["question"], "=>",
              ", ".join(Path(path).parent.name for path in row["selected"]) or "(none)")
    print(f"{report['passed']}/{report['total']} passed")
    sys.exit(0 if all(row["passed"] for row in rows) else 1)
