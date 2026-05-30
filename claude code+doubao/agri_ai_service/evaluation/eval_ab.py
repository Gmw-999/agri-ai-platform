"""
模型 A/B 测试框架
同一问题发给两个 LLM 配置，对比回答质量。

运行方式: python -m evaluation.eval_ab
支持两种模式:
1. 自动模式: 使用评判LLM自动打分
2. 交互模式: 人工在终端选择更好的回答
"""
import json
import sys
from pathlib import Path
from typing import List, Dict, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import llm
from core.llm_factory import LLMFactory

# A/B 测试问题集
AB_TEST_QUERIES = [
    "水稻稻瘟病的防治方案",
    "怎么判断作物缺氮",
    "推荐一种小麦除草剂",
    "有机种植的病虫害防治",
    "温室大棚黄瓜霜霉病",
    "玉米追肥的最佳时间",
    "果树修剪的基本原则",
    "农药混用的注意事项",
    "水稻直播技术要点",
    "蔬菜轮作的好处和方法",
    "如何提高土壤有机质",
    "油菜菌核病的防治",
    "花生高产栽培技术",
    "葡萄套袋技术要点",
    "柑橘黄龙病的防控",
]


def get_model_a_answer(query: str) -> Dict:
    """模型A: 当前默认配置 (DeepSeek)"""
    prompt = f"""你是农业技术专家，请回答以下问题。
要求：准确、专业、实用，控制在200字以内。

问题：{query}"""
    try:
        start = __import__("time").time()
        answer = llm.chat(prompt, temperature=0.3, max_tokens=400)
        elapsed = int((__import__("time").time() - start) * 1000)
        return {"answer": answer, "elapsed_ms": elapsed, "config": "DeepSeek (当前默认)"}
    except Exception as e:
        return {"answer": f"[错误: {e}]", "elapsed_ms": 0, "config": "DeepSeek"}


def get_model_b_answer(query: str) -> Dict:
    """模型B: 不同温度配置 (DeepSeek 高创造力)"""
    prompt = f"""你是农业技术专家，请回答以下问题。
要求：准确、专业、实用，控制在200字以内。

问题：{query}"""
    try:
        start = __import__("time").time()
        answer = llm.chat(prompt, temperature=0.8, max_tokens=400)
        elapsed = int((__import__("time").time() - start) * 1000)
        return {"answer": answer, "elapsed_ms": elapsed, "config": "DeepSeek (temperature=0.8)"}
    except Exception as e:
        return {"answer": f"[错误: {e}]", "elapsed_ms": 0, "config": "DeepSeek (高创造力)"}


def judge_answers(query: str, answer_a: str, answer_b: str) -> Dict:
    """评判LLM打分，决定哪个回答更好"""
    prompt = f"""你是一个AI回答质量评估专家。请对比下面两个回答，判断哪个更好。

【问题】{query}

【回答A】{answer_a}

【回答B】{answer_b}

评分标准：
1. 准确性 (1-5分): 信息是否正确、专业
2. 完整性 (1-5分): 是否覆盖关键信息
3. 实用性 (1-5分): 对农民是否有实际帮助
4. 简洁性 (1-5分): 是否简洁明了

返回JSON（只返回JSON）：
{{
    "a_scores": {{"accuracy": 5, "completeness": 5, "usefulness": 5, "conciseness": 5}},
    "b_scores": {{"accuracy": 5, "completeness": 5, "usefulness": 5, "conciseness": 5}},
    "winner": "A" 或 "B" 或 "平局",
    "reason": "判断理由"
}}"""
    try:
        raw = llm.chat(prompt, temperature=0.0, max_tokens=300)
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
            if raw.endswith("```"):
                raw = raw[:-3]
        return json.loads(raw)
    except Exception as e:
        return {"winner": "error", "reason": str(e)}


def run_auto_mode():
    """自动模式：LLM 评判"""
    print("=" * 60)
    print("  模型 A/B 测试 (自动评判模式)")
    print("  A: DeepSeek (temperature=0.3)")
    print("  B: DeepSeek (temperature=0.8)")
    print("=" * 60)

    results = []
    a_wins = b_wins = ties = 0

    for i, query in enumerate(AB_TEST_QUERIES):
        print(f"\n[{i+1}/{len(AB_TEST_QUERIES)}] {query[:50]}")
        print("  生成回答A...", end=" ")
        result_a = get_model_a_answer(query)
        print(f"({result_a['elapsed_ms']}ms)")

        print("  生成回答B...", end=" ")
        result_b = get_model_b_answer(query)
        print(f"({result_b['elapsed_ms']}ms)")

        print("  评判中...", end=" ")
        judgement = judge_answers(query, result_a["answer"], result_b["answer"])
        winner = judgement.get("winner", "平局")
        if winner == "A":
            a_wins += 1
        elif winner == "B":
            b_wins += 1
        else:
            ties += 1
        print(f"胜者: {winner}")

        results.append({
            "query": query,
            "answer_a": result_a,
            "answer_b": result_b,
            "judgement": judgement,
        })

    # 汇总
    n = len(AB_TEST_QUERIES)
    print("\n" + "=" * 60)
    print("  A/B 测试结果")
    print("=" * 60)
    print(f"  模型A胜出: {a_wins} ({round(a_wins/n*100,1)}%)")
    print(f"  模型B胜出: {b_wins} ({round(b_wins/n*100,1)}%)")
    print(f"  平局:     {ties}")

    # 保存
    output_path = Path(__file__).parent / "ab_test_results.json"
    summary = {
        "model_a": "DeepSeek (temperature=0.3)",
        "model_b": "DeepSeek (temperature=0.8)",
        "total_queries": n,
        "a_wins": a_wins,
        "b_wins": b_wins,
        "ties": ties,
        "results": results,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"\n详细结果: {output_path}")

    return summary


def run_interactive_mode():
    """交互模式：人工评判"""
    print("=" * 60)
    print("  模型 A/B 测试 (交互评判模式)")
    print("  在终端查看两个回答，选择更好的一个")
    print("=" * 60)

    results = []
    a_wins = b_wins = ties = 0

    for i, query in enumerate(AB_TEST_QUERIES[:5]):  # 交互模式只测5条
        print(f"\n{'='*60}")
        print(f"[{i+1}/{min(5, len(AB_TEST_QUERIES))}] 问题: {query}")
        print(f"{'='*60}")

        result_a = get_model_a_answer(query)
        result_b = get_model_b_answer(query)

        print(f"\n--- 回答A ---")
        print(result_a["answer"][:300])
        print(f"\n--- 回答B ---")
        print(result_b["answer"][:300])

        choice = input("\n哪个更好? (A/B/=): ").strip().upper()
        if choice == "B":
            b_wins += 1
        elif choice == "A":
            a_wins += 1
        else:
            ties += 1

        results.append({
            "query": query,
            "answer_a": result_a,
            "answer_b": result_b,
            "human_choice": choice,
        })

    print("\n交互评判完成!")
    return {
        "a_wins": a_wins, "b_wins": b_wins, "ties": ties,
        "results": results,
    }


def main():
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else "auto"
    if mode == "interactive":
        run_interactive_mode()
    else:
        run_auto_mode()


if __name__ == "__main__":
    main()
