"""
Agent 核心引擎
完整流程：意图识别 → 任务规划 → 工具调度执行 → 记忆更新 → 应答合成 → 药品链接增强

设计原则：
- 复杂需求自动拆解为多步，分步执行
- 简单问题快速回复，不绕弯子
- 所有工具通过 ToolRegistry 统一调度
- 用户画像由 LLM 自动提取积累
- 视觉模型（YOLOv8/ResNet/DeepLabV3）自动/手动调用
- 生成防治方案后自动附加药品购买链接
"""
import asyncio
import json
import re
import logging
from typing import Any, Dict, List, Optional, Tuple

from core.llm_factory import LLMFactory
from agent.memory import SessionMemory, UserProfileManager
from agent.tool_registry import ToolRegistry
from agent.drug_enricher import enrich_drug_links
from utils.tracer import AgentTrace

logger = logging.getLogger("agri_ai.agent")

# 单次执行最大工具步数
MAX_TOOL_STEPS = 5
# 工具结果截断长度
MAX_TOOL_RESULT_LEN = 800
# 图片最大描述长度
MAX_IMAGE_DESC_LEN = 500


class AgentCore:
    """农业智能助理核心引擎"""

    def __init__(
        self,
        session_memory: SessionMemory = None,
        user_profile: UserProfileManager = None,
        tool_registry: ToolRegistry = None,
    ):
        self.llm = LLMFactory.get_llm()
        self.session_memory = session_memory or SessionMemory()
        self.user_profile = user_profile or UserProfileManager()
        self.tool_registry = tool_registry or ToolRegistry()
        self._vision_service = None  # 延迟初始化

    @property
    def vision_service(self):
        if self._vision_service is None:
            try:
                from agent.vision_service import VisionService
                self._vision_service = VisionService()
            except Exception as e:
                logger.warning(f"[Agent] 视觉模型服务初始化失败: {e}")
                self._vision_service = None
        return self._vision_service

    # ====================== 对外接口 ======================

    def process(
        self,
        user_message: str,
        session_id: str,
        openid: str = "",
        image_data: Optional[bytes] = None,
    ) -> Dict[str, Any]:
        """
        处理用户消息，返回 Agent 执行结果。

        Args:
            user_message: 用户文本输入
            session_id: 会话ID
            openid: 用户标识
            image_data: 可选的上传图片字节数据

        Returns:
            {
                "reply": str,           # 最终回答
                "session_id": str,      # 会话ID
                "intent": str,          # 识别的意图
                "tools_used": [str],    # 调用的工具列表
                "steps": [dict],        # 执行步骤详情
                "vision_results": [dict], # 视觉模型结果（有图片时）
            }
        """
        # ===== 1. 加载上下文 =====
        session = self.session_memory.get_or_create(session_id, openid)
        profile = self.user_profile.get_profile(openid)
        session.add_message("user", user_message)
        logger.info(f"[Agent] 处理消息 | session={session_id[:8]} | openid={openid[:8] or 'anon'} | has_image={image_data is not None}")

        # 初始化 Trace
        trace = AgentTrace(session_id, user_message, has_image=(image_data is not None))

        vision_results = []

        # ===== 1.5 图片处理（如果有图片） =====
        image_description = ""
        if image_data is not None:
            vision_results = self._handle_image(image_data, user_message)
            if vision_results:
                image_description = self._summarize_vision_results(vision_results)
                logger.info(f"[Agent] 图片分析完成: {len(vision_results)} 个模型结果")

        # ===== 1.8 快速通道：简单问候/闲聊直接回复，不走规划-执行-合成全流程 =====
        quick_reply = self._quick_reply(user_message)
        if quick_reply:
            session.add_message("assistant", quick_reply)
            logger.info(f"[Agent] 快速回复 | intent=闲聊")
            trace.log_step("quick_reply", 0, output_data=quick_reply[:200])
            trace.finish("success")
            return {
                "reply": quick_reply,
                "session_id": session_id,
                "intent": "闲聊",
                "tools_used": [],
                "steps": [],
                "vision_results": [],
            }

        # ===== 2. 规划阶段：意图识别 + 工具选择 =====
        import time as _time
        _plan_start = _time.time()
        try:
            plan = self._plan(user_message, session, profile, image_description)
            trace.log_step("plan", 0,
                          input_data={"query": user_message[:200]},
                          output_data=plan,
                          duration_ms=int((_time.time() - _plan_start) * 1000))
        except Exception as e:
            logger.error(f"[Agent] 规划失败: {e}", exc_info=True)
            plan = {"intent": "无法识别", "tools": [], "direct_response": True}
            trace.log_step("plan", 0, error=str(e))

        intent = plan.get("intent", "一般咨询")
        tools_to_call = plan.get("tools", [])

        # ===== 3. 执行阶段：调用工具 =====
        tool_results: Dict[str, str] = {}
        executed_tools: List[str] = []

        if tools_to_call and not plan.get("direct_response"):
            for step_idx, step in enumerate(tools_to_call):
                if step_idx >= MAX_TOOL_STEPS:
                    break

                tool_name = step.get("tool", "")
                tool_input = step.get("input", {})
                if not tool_name or tool_name == "none":
                    continue

                logger.info(f"[Agent] ⚡ 步骤 {step_idx + 1}: {tool_name} | 输入: {tool_input}")
                # 传入 session_id 用于频次限制
                _tool_start = _time.time()
                result = self.tool_registry.execute(tool_name, session_id=session_id, **tool_input)
                trace.log_step("tool_call", step_idx + 1,
                              input_data={"tool": tool_name, "args": tool_input},
                              output_data=result[:500] if result else None,
                              duration_ms=int((_time.time() - _tool_start) * 1000))
                # 药品相关工具不截断，确保图片和购买链接完整传递
                drug_tools = {"pesticide_recommend", "drug_links", "pest_treatment"}
                if tool_name not in drug_tools and len(result) > MAX_TOOL_RESULT_LEN:
                    result = result[:MAX_TOOL_RESULT_LEN] + "...(截断)"
                tool_results[tool_name] = result
                executed_tools.append(tool_name)

        # ===== 4. 更新用户画像 =====
        try:
            if openid:
                self.user_profile.extract_and_update(openid, user_message, self.llm)
                profile = self.user_profile.get_profile(openid)
        except Exception as e:
            logger.warning(f"[Agent] 画像更新跳过: {e}")

        # ===== 5. 合成阶段：生成最终回答 =====
        try:
            reply = self._synthesize(
                user_message=user_message,
                intent=intent,
                tool_results=tool_results,
                executed_tools=executed_tools,
                session=session,
                profile=profile,
                image_description=image_description,
            )
        except Exception as e:
            logger.error(f"[Agent] 合成失败: {e}", exc_info=True)
            reply = self._fallback_reply(user_message)

        # ===== 5.5 药品链接增强（纯正则，不走 LLM） =====
        try:
            reply = enrich_drug_links(reply)
        except Exception as e:
            logger.warning(f"[Agent] 药品增强跳过: {e}")

        # ===== 6. 更新短期记忆 =====
        session.add_message("assistant", reply)

        logger.info(f"[Agent] ✅ 完成 | intent={intent} | tools={executed_tools}")
        trace.log_step("synthesize", len(executed_tools) + 1, output_data=reply[:200])
        trace.finish("success")
        return {
            "reply": reply,
            "session_id": session_id,
            "intent": intent,
            "tools_used": executed_tools,
            "steps": tools_to_call,
            "vision_results": vision_results,
        }

    async def process_async(
        self,
        user_message: str,
        session_id: str,
        openid: str = "",
        image_data: Optional[bytes] = None,
    ) -> Dict[str, Any]:
        """异步版 process()——在 FastAPI 端点中调用，不阻塞事件循环"""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.process(user_message, session_id, openid, image_data)
        )

    # ====================== 图片处理 ======================

    def _handle_image(self, image_data: bytes, user_message: str) -> List[Dict]:
        """
        处理用户上传的图片：
        1. 如果用户明确指定了模型 → manual_detect
        2. 否则 → auto_detect（LLM自动判断）
        """
        vs = self.vision_service
        if not vs:
            return [{"model": "none", "error": "视觉服务未就绪"}]

        # 检查用户是否指定了模型
        model_keywords = {
            "yolov8": ["yolo", "目标检测", "检测"],
            "resnet": ["resnet", "分类", "病害识别"],
            "deeplabv3": ["deeplab", "分割", "病斑"],
        }

        specified_model = None
        msg_lower = user_message.lower()
        for model_name, keywords in model_keywords.items():
            if any(kw in msg_lower for kw in keywords):
                specified_model = model_name
                break

        try:
            if specified_model:
                logger.info(f"[Agent] 用户指定视觉模型: {specified_model}")
                result = vs.manual_detect(specified_model, image_data)
                return [result]
            else:
                logger.info("[Agent] LLM 自动判断视觉模型")
                result = vs.auto_detect(image_data, user_message)
                # 展开 results 中的各模型结果
                models_called = result.get("results", {})
                output = []
                for model_name, model_result in models_called.items():
                    output.append(model_result)
                if not output:
                    output = [result]
                return output
        except Exception as e:
            logger.error(f"[Agent] 图片处理异常: {e}")
            return [{"model": "error", "error": str(e)}]

    def _summarize_vision_results(self, vision_results: List[Dict]) -> str:
        """将视觉模型结果汇总为文本描述，供 LLM 规划/合成使用"""
        parts = []
        for vr in vision_results:
            model = vr.get("model", "未知模型")
            if not vr.get("success"):
                parts.append(f"[{model}] 分析失败：{vr.get('error', '未知错误')}")
                continue

            if model == "yolov8":
                dets = vr.get("detections", [])
                descs = [f"{d['label']}(置信度{d['confidence']:.0%})" for d in dets[:5]]
                parts.append(f"[目标检测] 检测到 {len(dets)} 个目标：{'、'.join(descs)}")
            elif model == "resnet":
                tops = vr.get("top_predictions", [])
                descs = [f"{t.get('class_cn', t['class'])}({t['confidence']:.0%})" for t in tops[:3]]
                parts.append(f"[图像分类] 识别结果：{'、'.join(descs)}")
            elif model == "deeplabv3":
                seg = vr.get("segmentation", {})
                ratio = seg.get("disease_area_ratio", 0)
                parts.append(f"[语义分割] 病害区域占比：{ratio:.0%}")

        text = "；".join(parts)
        if len(text) > MAX_IMAGE_DESC_LEN:
            text = text[:MAX_IMAGE_DESC_LEN] + "..."
        return text

    # ====================== 快速通道 ======================

    _GREETINGS = {
        "你好", "您好", "hello", "hi", "在吗", "在不在", "早上好", "下午好", "晚上好",
        "谢谢", "感谢", "多谢", "辛苦了", "好的", "ok", "好的谢谢", "好",
    }

    def _quick_reply(self, message: str) -> str:
        """简单问候/闲聊直接回复，不走完整 Agent 流程"""
        m = message.strip().lower()
        if m in self._GREETINGS or len(m) <= 4:
            if any(g in m for g in ["你好", "您好", "hello", "hi", "在吗"]):
                return "你好！我是农业智能助理，可以帮你查询天气、识别病虫害、推荐农药、管理田间农事等，有什么可以帮你的？"
            if any(g in m for g in ["谢谢", "感谢", "多谢", "辛苦了"]):
                return "不客气！有需要随时找我。"
            if m in {"好的", "ok", "好"}:
                return "好的，有什么问题随时问我。"
        return ""

    # ====================== 规划 ======================

    def _plan(
        self,
        user_message: str,
        session,
        profile,
        image_description: str = "",
    ) -> Dict[str, Any]:
        """规划阶段：LLM 分析意图，决定是否/如何调用工具"""
        history = session.to_chat_history(max_turns=6)
        profile_summary = self.user_profile.profile_summary(profile.openid)
        # 使用带严格规则的描述（禁止LLM乱编工具名）
        tool_descriptions = self.tool_registry.list_descriptions_with_rule()

        image_context = ""
        if image_description:
            image_context = f"\n【图片分析结果】\n{image_description}\n"

        prompt = f"""你是农业智能助理的【规划器】，负责分析用户问题并规划工具调用。

【用户画像】
{profile_summary}

【最近对话】
{history if history else "（无）"}

【用户新消息】
{user_message}
{image_context}
【可用工具】
{tool_descriptions}

【规则 — 必须严格遵守】
1. 分析用户的核心意图。
2. 如果需要使用工具才能回答，列出要调用的工具和参数。
3. **禁止编造工具名**：只能使用【可用工具】中列出的工具名，工具名必须完全匹配。
4. **禁止编造参数**：参数名必须与工具定义的参数一致，不要自己发明参数。
5. 如果问题简单（问候、闲聊、无需工具），设 direct_response=true 直接回答。
6. 如果涉及多个方面（如天气+病虫害+农药），可以调用多个工具。
7. 如果已有图片分析结果，应优先参考图片信息回答问题。
8. 输出严格的 JSON 格式，不要多余的文字：

{{
    "intent": "简短描述用户意图",
    "direct_response": false,
    "tools": [
        {{"tool": "工具名", "input": {{"参数名": "参数值"}}}}
    ]
}}

对于 pesticide_recommend 工具，input 中的 demand 参数需要用完整的自然语言描述用户需求。
对于 pest_treatment 工具，参数中的 severity 如果不明确就用"中度发生"。
对于 weather_advice 工具，query 参数需要包含地点。

如果不需要工具：
{{
    "intent": "意图描述",
    "direct_response": true,
    "tools": []
}}"""
        response_text = self.llm.chat(prompt, temperature=0.1, max_tokens=1024)
        return self._parse_plan(response_text)

    def _parse_plan(self, text: str) -> Dict[str, Any]:
        """解析 LLM 规划的 JSON"""
        text = text.strip()
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            text = match.group()
        text = text.replace("```json", "").replace("```", "")

        try:
            plan = json.loads(text)
            if not isinstance(plan, dict):
                raise ValueError("plan is not dict")
            return plan
        except json.JSONDecodeError as e:
            logger.warning(f"[Agent] 规划JSON解析失败: {e}，尝试直接回复")
            return {"intent": "自动判断", "direct_response": True, "tools": []}

    # ====================== 合成 ======================

    def _synthesize(
        self,
        user_message: str,
        intent: str,
        tool_results: Dict[str, str],
        executed_tools: List[str],
        session,
        profile,
        image_description: str = "",
    ) -> str:
        """合成阶段：基于工具结果生成自然语言回答"""
        history = session.to_chat_history(max_turns=6)
        profile_summary = self.user_profile.profile_summary(profile.openid)

        image_context = ""
        if image_description:
            image_context = f"\n【图片分析结果】\n{image_description}\n"

        results_block = ""
        if tool_results:
            parts = []
            for tname in executed_tools:
                res = tool_results.get(tname, "")
                parts.append(f"【{tname} 执行结果】\n{res}")
            results_block = "\n\n".join(parts)
        else:
            results_block = "（本回答未调用工具，基于自身知识回答）"

        prompt = f"""你是国家级的农业智能助理，专业、耐心、实战。

【用户画像】
{profile_summary}

【对话历史】
{history if history else "（无）"}

【意图】
{intent}

【用户问题】
{user_message}
{image_context}
【工具执行结果】
{results_block}

【回答要求】
1. 用通俗易懂的语言回答，让农户能听懂、能操作。
2. 有工具结果时必须基于工具结果回答。
3. 分点说明时用 1、2、3、。
4. 涉及药品时：
   - **只有工具结果中明确提供了 image_url 字段的药品，才输出图片**：![药品名称](真实URL)
   - **只有工具结果中明确提供了 purchase_url 字段的药品，才输出购买链接**：[点击购买](真实URL)
   - **[点击购买](url) 本身就是可点击跳转的购买按钮，严禁在后面或任意位置再写出原始URL地址！**
   - **如果工具结果中没有 image_url 或 purchase_url 字段，绝对不要输出图片或购买链接**，只写药品名称和用法用量即可。
   - 正确示例（工具结果有URL时）：
     1. **吡唑醚菌酯 25% 悬浮剂**
     ![吡唑醚菌酯](https://ima.nongyao001.com/real-image.jpg)
     [点击购买](https://www.nongyao001.com/sell/show-12345.html)
     每亩用量30克，稀释2000倍均匀喷雾。
   - 错误示例（严禁出现）：
     1. **吡唑醚菌酯 25% 悬浮剂**
     [点击购买](https://xxx.com) 购买地址：https://xxx.com  ← 禁止！按钮后面不要再写URL！
     用法用量：每亩30克。
5. 涉及天气时给出农事建议。
6. 回答完后可以主动询问是否需要进一步帮助。
7. 不要提及"工具""函数""接口"等技术术语，直接给答案。
8. 如果已有图片分析，结合图片信息给出针对性判断。
9. **严禁编造任何URL！严禁输出 alicdn.com、taobao.com、jd.com 等电商平台链接！只能使用工具结果中已存在的真实URL。没有URL就只写文字。**
10. 只输出回答，不要输出 JSON 或多余结构。"""
        reply = self.llm.chat(prompt, temperature=0.5, max_tokens=2048)
        return reply.strip()

    # ====================== 降级处理 ======================

    def _fallback_reply(self, user_message: str) -> str:
        """当规划或合成失败时的降级回复"""
        try:
            reply = self.llm.chat(
                f"你是农业专家，请用通俗的语言回答：{user_message}",
                temperature=0.5,
                max_tokens=1024,
            )
            return reply.strip()
        except Exception:
            return "抱歉，我现在暂时无法处理，请稍后再试。"

    # ====================== 生命周期 ======================

    def clear_session(self, session_id: str, openid: str = ""):
        """主动清除会话记忆和工具调用记录"""
        self.session_memory.clear_session(session_id, openid=openid)
        self.tool_registry.cleanup_session(session_id)
        logger.info(f"[Agent] 已清除会话: {session_id[:8]} | openid={openid[:8] or 'anon'}")
