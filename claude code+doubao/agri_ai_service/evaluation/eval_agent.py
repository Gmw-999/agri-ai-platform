"""
Agent 工具选择评估脚本
运行方式: python -m evaluation.eval_agent
从项目根目录 (agri_ai_service) 运行。

评估指标:
- 工具选择准确率 (Precision)
- 工具召回率 (Recall)
- 幻觉工具率 (Hallucination rate)
- 平均工具步数
"""
import json
import sys
from pathlib import Path
from typing import List, Dict, Set

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import llm


def load_test_set() -> List[Dict]:
    path = Path(__file__).parent / "test_set.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["test_cases"]


def get_available_tools() -> Set[str]:
    """获取工具注册表中所有可用工具名称"""
    from agent.tool_registry import ToolRegistry
    registry = ToolRegistry()
    tools = set()
    for name, spec in registry._tools.items():
        tools.add(name)
        if spec.aliases:
            tools.update(spec.aliases)
    return tools


def call_llm_plan(user_message: str) -> Dict:
    """让 LLM 决定应该调用哪些工具（模拟 Agent 规划阶段）"""
    available_tools = get_available_tools()
    tool_list = "\n".join(f"- {t}" for t in sorted(available_tools) if not t.startswith("_"))

    prompt = f"""你是一个农业AI的规划器。根据用户问题，决定需要调用哪些工具。

可用工具：
{tool_list}

规则：
1. 简单问候/闲聊不需要任何工具
2. 涉及具体病虫害防治需要知识库查询和药品推荐
3. 天气相关需要天气工具
4. 农药稀释计算需要稀释工具
5. 只返回真实存在的工具名，不要编造
6. 最多调用2-3个工具

用户问题：{user_message}

请返回JSON格式：
{{"tools": ["工具名1", "工具名2"], "intent": "意图描述"}}
只返回JSON，不要多余文字。"""

    try:
        raw = llm.chat(prompt, temperature=0.0, max_tokens=300)
        raw = raw.strip()
        # 处理可能的 markdown 代码块包裹
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
            if raw.endswith("```"):
                raw = raw[:-3]
        result = json.loads(raw)
        return result
    except Exception as e:
        return {"tools": [], "error": str(e)}


def evaluate_tool_selection(test_cases: List[Dict]) -> Dict:
    """评估工具选择准确性"""
    results = []
    total_precision = 0.0
    total_recall = 0.0
    total_hallucination = 0
    hallucination_details = []

    for tc in test_cases:
        plan = call_llm_plan(tc["query"])
        predicted = set(plan.get("tools", []))
        expected = set(tc["expected_tools"])
        available = get_available_tools()

        # 检查幻觉工具
        hallucinated = predicted - available
        if hallucinated:
            total_hallucination += 1
            hallucination_details.append({
                "query": tc["query"],
                "hallucinated": list(hallucinated)
            })

        # 计算指标
        tp = len(predicted & expected)
        precision = tp / len(predicted) if predicted else (1.0 if not expected else 0.0)
        recall = tp / len(expected) if expected else 1.0

        total_precision += precision
        total_recall += recall

        results.append({
            "id": tc["id"],
            "query": tc["query"],
            "expected": list(expected),
            "predicted": list(predicted),
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "hallucinated": list(hallucinated),
            "correct": predicted == expected,
        })

    n = len(test_cases)
    avg_precision = round(total_precision / n * 100, 1) if n else 0
    avg_recall = round(total_recall / n * 100, 1) if n else 0
    exact_match = sum(1 for r in results if r["correct"])

    return {
        "total_cases": n,
        "avg_precision_pct": avg_precision,
        "avg_recall_pct": avg_recall,
        "exact_match_count": exact_match,
        "exact_match_pct": round(exact_match / n * 100, 1) if n else 0,
        "hallucination_count": total_hallucination,
        "hallucination_rate_pct": round(total_hallucination / n * 100, 1) if n else 0,
        "hallucination_details": hallucination_details,
        "per_case_results": results,
    }


def main():
    print("=" * 60)
    print("  农智AI Agent 工具选择评估")
    print("=" * 60)

    print("\n[1/3] 加载测试集...")
    test_cases = load_test_set()
    print(f"  已加载 {len(test_cases)} 条测试用例")

    print("\n[2/3] 可用工具列表:")
    for t in sorted(get_available_tools()):
        if not t.startswith("_"):
            print(f"  - {t}")

    print("\n[3/3] 运行评估...")
    result = evaluate_tool_selection(test_cases)

    print("\n" + "=" * 60)
    print("  评估结果")
    print("=" * 60)
    print(f"  测试用例数:           {result['total_cases']}")
    print(f"  平均精确率:           {result['avg_precision_pct']}%")
    print(f"  平均召回率:           {result['avg_recall_pct']}%")
    print(f"  完全匹配数:           {result['exact_match_count']}/{result['total_cases']} ({result['exact_match_pct']}%)")
    print(f"  幻觉工具次数:         {result['hallucination_count']} ({result['hallucination_rate_pct']}%)")

    if result["hallucination_details"]:
        print("\n  幻觉工具详情:")
        for h in result["hallucination_details"]:
            print(f"    问题: {h['query'][:40]}...")
            print(f"    幻觉工具: {h['hallucinated']}")

    # 保存结果
    output_path = Path(__file__).parent / "eval_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n  详细结果已保存到: {output_path}")

    return result


if __name__ == "__main__":
    main()
