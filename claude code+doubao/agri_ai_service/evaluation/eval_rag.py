"""
RAG 质量评估脚本
对比"纯 LLM" vs "LLM + ChromaDB 向量检索"的回答质量。

运行方式: python -m evaluation.eval_rag
从项目根目录 (agri_ai_service) 运行。

评估方法：
1. 对同一批农业问题，分别用纯LLM和RAG模式生成回答
2. 使用评分LLM对两个答案进行打分（准确性、完整性、实用性）
3. 输出对比报告
"""
import json
import sys
from pathlib import Path
from typing import List, Dict

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import llm
from tools.vector_db import AgriVectorDB

# RAG 测试问题集
RAG_TEST_QUERIES = [
    "水稻纹枯病的症状和防治方法",
    "小麦锈病用什么农药效果好",
    "玉米螟怎么防治",
    "棉花蚜虫的生物防治方法",
    "大豆根腐病怎么处理",
    "番茄晚疫病的早期症状",
    "稻飞虱的危害和防治",
    "苹果树腐烂病怎么治",
    "油菜菌核病的发生规律",
    "蔬菜大棚白粉病防治",
    "果树春季管理要点",
    "农药安全使用注意事项",
    "化肥和有机肥的区别",
    "水稻田杂草防除技术",
    "温室大棚温度管理",
    "土壤板结怎么改良",
    "马铃薯晚疫病识别",
    "花生叶斑病用什么药",
    "葡萄霜霉病防治技术",
    "辣椒病毒病怎么防治",
    "无公害蔬菜种植技术",
    "草莓灰霉病的防治",
    "玉米大小斑病区别",
    "水稻冷害的预防",
    "柑橘黄龙病怎么识别",
    "茶园病虫害绿色防控",
    "有机农业的病虫害防治原则",
    "冬小麦春季管理技术",
    "设施农业中的病虫害综合防治",
    "精准农业技术在水稻上的应用",
]


def create_vector_db() -> AgriVectorDB:
    """初始化向量数据库"""
    try:
        from config.settings import VECTOR_DB_DIR, VECTOR_COLLECTION_NAME, VECTOR_EMBEDDING_MODEL
        db = AgriVectorDB(
            persist_directory=VECTOR_DB_DIR,
            collection_name=VECTOR_COLLECTION_NAME,
            embedding_model=VECTOR_EMBEDDING_MODEL,
        )
        stats = db.get_collection_stats()
        doc_count = stats.get("document_count", 0) if stats else 0
        if doc_count == 0:
            print(f"  [注意] 向量库为空，请先运行数据导入。")
        else:
            print(f"  向量库已加载: {doc_count} 条文档")
        return db
    except Exception as e:
        print(f"  [警告] 向量库初始化失败: {e}")
        return None


def answer_with_llm(query: str) -> str:
    """纯 LLM 回答"""
    prompt = f"""你是一个专业的农业技术顾问。请准确回答以下农业问题。
如果不知道，请如实说不知道，不要编造信息。

问题：{query}

请用中文简洁回答（200字以内）。"""
    try:
        return llm.chat(prompt, temperature=0.1, max_tokens=400)
    except Exception as e:
        return f"[LLM调用失败: {e}]"


def answer_with_rag(query: str, vector_db: AgriVectorDB) -> str:
    """LLM + 向量检索增强回答"""
    # 检索相关知识
    context_docs = []
    if vector_db:
        try:
            results = vector_db.search(query, top_k=3)
            for r in results:
                doc = r.get("document", "")
                if doc:
                    context_docs.append(doc[:500])
        except Exception as e:
            context_docs.append(f"[检索失败: {e}]")

    context_text = "\n---\n".join(context_docs) if context_docs else "（未检索到相关知识）"

    prompt = f"""你是一个专业的农业技术顾问。请根据提供的知识库内容回答用户问题。
如果知识库中有相关信息，优先基于知识库回答。
如果知识库中没有相关信息，可以基于你的专业知识补充，但要明确说明哪些来自知识库，哪些是你补充的。
不要编造信息。

【知识库内容】
{context_text}

【用户问题】
{query}

请用中文简洁回答（200字以内）。"""
    try:
        return llm.chat(prompt, temperature=0.1, max_tokens=400)
    except Exception as e:
        return f"[LLM调用失败: {e}]"


def score_answers(query: str, llm_answer: str, rag_answer: str) -> Dict:
    """使用 LLM 对两个回答进行对比评分"""
    scorer_prompt = f"""你是一个AI回答质量评估专家。请对比以下两个回答，给每个回答打分并说明理由。

【用户问题】
{query}

【纯LLM回答】
{llm_answer}

【RAG增强回答(LLM+知识库)】
{rag_answer}

评分标准（每项1-5分）：
1. 准确性：回答内容是否正确、有依据
2. 完整性：是否覆盖了问题的关键信息
3. 实用性：对农民是否有实际帮助

请返回JSON格式（只返回JSON）：
{{
    "llm_scores": {{"accuracy": 5, "completeness": 5, "usefulness": 5}},
    "rag_scores": {{"accuracy": 5, "completeness": 5, "usefulness": 5}},
    "winner": "rag" 或 "llm" 或 "tie",
    "comment": "简要点评"
}}"""

    try:
        raw = llm.chat(scorer_prompt, temperature=0.0, max_tokens=300)
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
            if raw.endswith("```"):
                raw = raw[:-3]
        return json.loads(raw)
    except Exception as e:
        return {
            "llm_scores": {"accuracy": 0, "completeness": 0, "usefulness": 0},
            "rag_scores": {"accuracy": 0, "completeness": 0, "usefulness": 0},
            "winner": "error",
            "comment": f"评分失败: {e}"
        }


def main():
    print("=" * 60)
    print("  RAG 质量评估：纯LLM vs LLM+向量检索")
    print("=" * 60)

    print("\n[1/4] 初始化向量数据库...")
    vector_db = create_vector_db()

    print(f"\n[2/4] 测试问题数: {len(RAG_TEST_QUERIES)}")

    print("\n[3/4] 运行对比评估...")
    results = []
    llm_win = 0
    rag_win = 0
    tie = 0

    for i, query in enumerate(RAG_TEST_QUERIES):
        print(f"  [{i+1}/{len(RAG_TEST_QUERIES)}] {query[:40]}...", end=" ")

        llm_answer = answer_with_llm(query)
        rag_answer = answer_with_rag(query, vector_db)
        score = score_answers(query, llm_answer, rag_answer)

        winner = score.get("winner", "tie")
        if winner == "rag":
            rag_win += 1
        elif winner == "llm":
            llm_win += 1
        else:
            tie += 1

        results.append({
            "query": query,
            "llm_answer": llm_answer[:300],
            "rag_answer": rag_answer[:300],
            "scores": score,
        })
        print(f" 胜者: {winner.upper()}")

    print(f"\n[4/4] 评估完成")

    # 汇总
    n = len(RAG_TEST_QUERIES)
    summary = {
        "total_queries": n,
        "rag_win": rag_win,
        "llm_win": llm_win,
        "tie": tie,
        "rag_win_rate": round(rag_win / n * 100, 1) if n else 0,
        "llm_win_rate": round(llm_win / n * 100, 1) if n else 0,
        "per_query_results": results,
    }

    print("\n" + "=" * 60)
    print("  RAG 评估结果")
    print("=" * 60)
    print(f"  RAG 胜出:           {rag_win} ({summary['rag_win_rate']}%)")
    print(f"  纯LLM胜出:          {llm_win} ({summary['llm_win_rate']}%)")
    print(f"  平局:               {tie}")

    # 保存结果
    output_path = Path(__file__).parent / "rag_eval_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"\n  详细结果已保存到: {output_path}")

    # 生成 markdown 报告
    report_path = Path(__file__).parent / "rag_eval_report.md"
    markdown = generate_report(summary)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(markdown)
    print(f"  报告已保存到: {report_path}")

    return summary


def generate_report(summary: Dict) -> str:
    """生成 Markdown 格式的评估报告"""
    lines = [
        "# RAG 质量评估报告",
        "",
        f"## 概述",
        f"- 测试问题数: {summary['total_queries']}",
        f"- RAG 增强胜出: {summary['rag_win']} ({summary['rag_win_rate']}%)",
        f"- 纯LLM胜出: {summary['llm_win']} ({summary['llm_win_rate']}%)",
        f"- 平局: {summary['tie']}",
        "",
        "## 结论",
    ]
    if summary["rag_win_rate"] > 50:
        lines.append(f"RAG 增强在 {summary['rag_win_rate']}% 的问题上优于纯LLM，说明向量知识库对农业专业问题的回答质量有显著提升。")
    else:
        lines.append(f"RAG 增强在测试集上表现与纯LLM相当，可能需要优化检索策略或扩充知识库内容。")

    lines.extend([
        "",
        "## 各问题详情",
        "",
        "| # | 问题 | 胜者 |",
        "|---|------|------|",
    ])
    for r in summary["per_query_results"]:
        winner = r["scores"].get("winner", "tie").upper()
        lines.append(f"| {len(lines)-7} | {r['query'][:30]} | {winner} |")

    return "\n".join(lines)


if __name__ == "__main__":
    main()
