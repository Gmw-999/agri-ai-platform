"""
工具注册与调度中心
统一封装现有 agri_tools 中的所有工具函数，
为 LLM 提供结构化描述，支持自动调度和参数传递。

生产级特性：
- 工具参数严格校验（JSON Schema）
- 调用频次限制（每会话每工具最多 N 次/分钟）
- 工具名白名单验证
- 预留视觉模型接口
"""
import json
import logging
import time
from typing import Any, Callable, Dict, List, Optional

from tools.agri_tools import (
    _get_dep,
    farm_weather_advice,
    pest_risk_forecast_online,
    simple_drug_links,
    pest_treatment_from_image,
    crop_growth_management,
    farm_log_operation,
    pesticide_dilute,
    enhanced_agri_knowledge_query,
    agri_knowledge_query,
    search_nongyao001,
    pesticide_dilute_calc,
)

logger = logging.getLogger("agri_ai.tools")

# 每会话每工具最多调用次数（1分钟窗口）
MAX_TOOL_CALLS_PER_MINUTE = 5


# ====================== 工具描述结构 ======================

class ToolSpec:
    """工具规格定义"""

    def __init__(
        self,
        name: str,
        description: str,
        handler: Callable,
        parameters: Dict[str, Any],
        category: str = "general",
    ):
        self.name = name
        self.description = description
        self.handler = handler
        self.parameters = parameters  # JSON Schema 风格
        self.category = category

    def validate_params(self, **kwargs) -> Optional[str]:
        """
        校验参数是否符合 JSON Schema。
        Returns: None 表示合法，str 表示错误信息。
        """
        schema = self.parameters
        required = schema.get("required", [])
        props = schema.get("properties", {})

        # 检查必填参数
        for p in required:
            if p not in kwargs or kwargs[p] is None:
                return f"工具 {self.name} 缺少必填参数: {p}"

        # 检查参数值类型和合法性
        for pname, pvalue in kwargs.items():
            if pname not in props:
                continue
            pdef = props[pname]
            ptype = pdef.get("type", "string")

            # 类型检查
            if ptype == "string" and not isinstance(pvalue, str):
                return f"工具 {self.name} 参数 {pname} 应为字符串，实际为 {type(pvalue).__name__}"
            if ptype == "integer":
                try:
                    int(pvalue)
                except (ValueError, TypeError):
                    return f"工具 {self.name} 参数 {pname} 应为整数，实际为 {pvalue}"
            if ptype == "number":
                try:
                    float(pvalue)
                except (ValueError, TypeError):
                    return f"工具 {self.name} 参数 {pname} 应为数字，实际为 {pvalue}"

            # 字符串非空检查
            if ptype == "string" and isinstance(pvalue, str) and not pvalue.strip():
                return f"工具 {self.name} 参数 {pname} 不能为空"

        return None

    def execute(self, **kwargs) -> str:
        """执行工具，先校验参数再调用"""
        # 参数校验
        validation_error = self.validate_params(**kwargs)
        if validation_error:
            logger.warning(f"❌ 工具参数校验失败: {validation_error}")
            return json.dumps({"error": validation_error, "tool": self.name}, ensure_ascii=False)

        try:
            logger.info(f"🔧 Agent 调度工具: {self.name} | 参数: {kwargs}")
            result = self.handler(**kwargs)
            return result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)
        except Exception as e:
            logger.error(f"❌ 工具执行失败 {self.name}: {e}")
            return json.dumps({"error": f"{self.name} 执行失败: {str(e)}"}, ensure_ascii=False)

    def to_llm_description(self) -> str:
        """生成 LLM 可读的工具描述"""
        params_desc = []
        for pname, pinfo in self.parameters.get("properties", {}).items():
            req = "必填" if pname in self.parameters.get("required", []) else "可选"
            params_desc.append(f"  - {pname}（{req}）：{pinfo.get('description', '')}")
        return (
            f"【{self.name}】{self.description}\n"
            f"参数：\n" + "\n".join(params_desc)
        )


# ====================== 工具注册中心 ======================

class ToolRegistry:
    """
    工具注册中心
    - 注册所有可用工具
    - 根据名称查找并执行
    - 参数严格校验
    - 调用频次限制
    - 生成供 LLM 使用的工具描述列表
    - 预留视觉模型注册接口
    """

    VALID_TOOL_NAMES = {
        "weather_advice", "pest_forecast", "pesticide_recommend",
        "pest_treatment", "crop_management", "farm_log",
        "pesticide_dilute", "agri_knowledge", "drug_links",
        "yolo_detect", "resnet_classify", "deeplab_segment",
    }

    def __init__(self):
        self._tools: Dict[str, ToolSpec] = {}
        # 调用频次记录: {session_id: {tool_name: [timestamp, ...]}}
        self._call_history: Dict[str, Dict[str, List[float]]] = {}
        self._register_default_tools()

    def register(self, tool: ToolSpec):
        self._tools[tool.name] = tool
        logger.debug(f"已注册工具: {tool.name}")

    def get(self, name: str) -> Optional[ToolSpec]:
        return self._tools.get(name)

    def list_tools(self) -> List[str]:
        return list(self._tools.keys())

    def list_descriptions(self) -> str:
        """返回所有工具的 LLM 描述"""
        descs = []
        for tool in self._tools.values():
            descs.append(tool.to_llm_description())
        return "\n\n".join(descs)

    def list_descriptions_with_rule(self) -> str:
        """返回工具描述 + 严格调用规则"""
        descs = self.list_descriptions()
        rule = (
            "\n\n【严格规则】\n"
            "1. 只能使用上面列出的工具名，禁止编造工具名。\n"
            "2. 工具名必须是以下之一：" + ", ".join(sorted(self.VALID_TOOL_NAMES)) + "\n"
            "3. 参数必须完整且符合要求，不可缺少必填参数。\n"
            "4. 如果拿不准用什么工具，设 direct_response=true 直接回答。\n"
            "5. 不要调用同一个工具超过 3 次。\n"
        )
        return descs + rule

    def execute(self, tool_name: str, session_id: str = "", **kwargs) -> str:
        """
        执行工具（带参数校验 + 频次限制）

        Args:
            tool_name: 工具名
            session_id: 会话ID（用于频次限制）
            **kwargs: 工具参数

        Returns:
            工具执行结果 JSON 字符串
        """
        # 1. 白名单校验
        if tool_name not in self.VALID_TOOL_NAMES:
            logger.warning(f"❌ 非法工具名: {tool_name}，不在白名单中")
            return json.dumps({
                "error": f"工具 '{tool_name}' 不存在",
                "valid_tools": sorted(self.VALID_TOOL_NAMES),
            }, ensure_ascii=False)

        # 2. 查找工具
        tool = self.get(tool_name)
        if not tool:
            return json.dumps({"error": f"未知工具: {tool_name}"}, ensure_ascii=False)

        # 3. 频次限制检查
        if session_id:
            allowed, remain = self._check_rate_limit(session_id, tool_name)
            if not allowed:
                logger.warning(f"⏳ 工具 {tool_name} 调用超频（会话 {session_id[:8]}）")
                return json.dumps({
                    "error": f"工具 {tool_name} 调用太频繁，请稍后再试",
                    "retry_after": "60秒",
                }, ensure_ascii=False)

        # 4. 执行（含参数校验）
        result = tool.execute(**kwargs)

        # 5. 记录调用
        if session_id:
            self._record_call(session_id, tool_name)

        return result

    # ====================== 频次控制 ======================

    def _check_rate_limit(self, session_id: str, tool_name: str) -> tuple:
        """
        检查调用是否超频。
        Returns: (allowed: bool, remaining: int)
        """
        now = time.time()
        window_start = now - 60

        history = self._call_history.get(session_id, {})
        timestamps = history.get(tool_name, [])

        # 只保留最近 1 分钟内的记录
        valid = [t for t in timestamps if t > window_start]
        history[tool_name] = valid

        if len(valid) >= MAX_TOOL_CALLS_PER_MINUTE:
            return False, 0
        return True, MAX_TOOL_CALLS_PER_MINUTE - len(valid)

    def _record_call(self, session_id: str, tool_name: str):
        """记录一次工具调用"""
        now = time.time()
        if session_id not in self._call_history:
            self._call_history[session_id] = {}
        if tool_name not in self._call_history[session_id]:
            self._call_history[session_id][tool_name] = []
        self._call_history[session_id][tool_name].append(now)

    def cleanup_session(self, session_id: str):
        """清理会话的调用记录"""
        self._call_history.pop(session_id, None)

    # ====================== 注册默认农业工具 ======================

    def _register_default_tools(self):
        """注册 agri_tools.py 中现有的 8 大类工具"""

        self.register(ToolSpec(
            name="weather_advice",
            description="查询某地区的实时天气、未来7天天气预报、极端天气预警，并生成农事操作建议（打药、施肥、浇水、收获等）",
            handler=farm_weather_advice,
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "用户关于天气的完整提问，如'山东菏泽明天适合打药吗'"},
                },
                "required": ["query"],
            },
            category="weather",
        ))

        self.register(ToolSpec(
            name="pest_forecast",
            description="生成某地区某种作物在未来1-2周的病虫害高发期预报，包括病虫害名称、预警等级、发生原因和防治建议",
            handler=pest_risk_forecast_online,
            parameters={
                "type": "object",
                "properties": {
                    "region": {"type": "string", "description": "地区，如'山东菏泽'"},
                    "crop": {"type": "string", "description": "作物名称，如'小麦'"},
                    "month": {"type": "integer", "description": "月份，1-12的数字"},
                },
                "required": ["region", "crop", "month"],
            },
            category="pest",
        ))

        self.register(ToolSpec(
            name="pesticide_recommend",
            description="根据病虫害名称或用户需求，从农药数据库中搜索推荐的低毒农药，返回药品名称、图片链接和购买链接。合成回答时必须把图片链接和购买链接附在药品后面。",
            handler=simple_drug_links,
            parameters={
                "type": "object",
                "properties": {
                    "demand": {"type": "string", "description": "用户对农药的需求描述，如'稻瘟病用什么药''买杀虫剂'"},
                },
                "required": ["demand"],
            },
            category="pesticide",
        ))

        self.register(ToolSpec(
            name="pest_treatment",
            description="生成病虫害的完整防治方案，包含农业防治、物理防治、化学防治措施，推荐3-4种低毒农药并附带药品的图片和购买链接",
            handler=pest_treatment_from_image,
            parameters={
                "type": "object",
                "properties": {
                    "pest_type": {"type": "string", "description": "病虫害名称，如'稻瘟病''小麦白粉病'"},
                    "crop_type": {"type": "string", "description": "作物名称，如'水稻''小麦'"},
                    "severity": {"type": "string", "description": "严重程度：轻度发生/中度发生/重度发生，默认中度发生"},
                },
                "required": ["pest_type", "crop_type"],
            },
            category="pest",
        ))

        self.register(ToolSpec(
            name="crop_management",
            description="生成作物在某个月份的田间管理方案，包含当前生长期、水肥管理、病虫害防控、田间操作和注意事项",
            handler=crop_growth_management,
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "用户关于作物管理的完整提问，如'水稻4月份怎么管理'"},
                },
                "required": ["query"],
            },
            category="cultivation",
        ))

        self.register(ToolSpec(
            name="farm_log",
            description="记录田间农事操作日志、查询历史日志、删除指定日志（记录到MySQL数据库）",
            handler=farm_log_operation,
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "用户关于田间日志的完整指令，如'记录今天施了复合肥''查看我的田间记录'"},
                },
                "required": ["query"],
            },
            category="management",
        ))

        self.register(ToolSpec(
            name="pesticide_dilute",
            description="农药稀释计算器：根据用药量（克/毫升）和稀释倍数，计算需要加多少公斤水。纯本地计算，无需联网。",
            handler=pesticide_dilute,
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "用户关于稀释计算的完整提问，如'用药30克稀释500倍需要加多少水'"},
                },
                "required": ["query"],
            },
            category="pesticide",
        ))

        self.register(ToolSpec(
            name="agri_knowledge",
            description="查询农业种植、养殖、病虫害等各方面的知识。适用于一般性农业知识问答。",
            handler=enhanced_agri_knowledge_query,
            parameters={
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "用户的农业知识问题"},
                },
                "required": ["question"],
            },
            category="knowledge",
        ))

        # 注册药品链接增强
        self._register_drug_enricher()
        # 注册视觉模型工具（描述性）
        self._register_vision_tools()

        logger.info(f"✅ 已注册 {len(self._tools)} 个工具（含参数校验+频次限制）")

    # ====================== 药品链接增强工具 ======================

    def _register_drug_enricher(self):
        """注册药品链接增强工具"""
        from agent.drug_enricher import enrich_drug_links, _search_drug

        def drug_enricher_handler(drug_name: str) -> str:
            drugs = _search_drug(drug_name)
            if not drugs:
                return json.dumps({"recommended_drugs": []}, ensure_ascii=False)
            return json.dumps({"recommended_drugs": drugs}, ensure_ascii=False, indent=2)

        self.register(ToolSpec(
            name="drug_links",
            description="根据药品名称查询农药数据库，返回该药品的图片链接和购买链接",
            handler=drug_enricher_handler,
            parameters={
                "type": "object",
                "properties": {
                    "drug_name": {"type": "string", "description": "药品名称，如'吡唑醚菌酯''阿维菌素'"},
                },
                "required": ["drug_name"],
            },
            category="pesticide",
        ))

    # ====================== 视觉模型工具 ======================

    def _register_vision_tools(self):
        """注册视觉模型工具（真实模型推理，延迟加载）"""
        _vs_cache = {}

        def _get_vs():
            if "vs" not in _vs_cache:
                from agent.vision_service import VisionService
                _vs_cache["vs"] = VisionService()
            return _vs_cache["vs"]

        def _make_handler(model_name: str):
            def handler(image_base64: str = "", **kw) -> str:
                if not image_base64:
                    return json.dumps({
                        "error": f"{model_name} 需要上传图片（base64）",
                        "info": "图片需通过接口上传，不支持纯文字调用",
                    }, ensure_ascii=False)
                from utils.image_utils import base64_to_image
                image_bytes, _ = base64_to_image(image_base64)
                if image_bytes is None:
                    return json.dumps({"error": "图片解码失败"}, ensure_ascii=False)
                vs = _get_vs()
                result = vs.manual_detect(model_name, image_bytes, **kw)
                return json.dumps(result, ensure_ascii=False)
            return handler

        self.register(ToolSpec(
            name="yolo_detect",
            description="YOLOv8 目标检测：识别图片中的作物、病虫害、杂草等目标的位置和类别。接收 base64 图片数据，返回检测到的目标列表（含标签、置信度、边界框）。",
            handler=_make_handler("yolov8"),
            parameters={
                "type": "object",
                "properties": {
                    "image_base64": {"type": "string", "description": "图片的 base64 编码数据"},
                    "confidence": {"type": "number", "description": "检测置信度阈值，默认0.25"},
                },
                "required": ["image_base64"],
            },
            category="vision",
        ))
        self.register(ToolSpec(
            name="resnet_classify",
            description="ResNet 图像分类：对作物病害图像进行分类，识别病害种类。接收 base64 图片数据，返回 top-k 分类结果。",
            handler=_make_handler("resnet"),
            parameters={
                "type": "object",
                "properties": {
                    "image_base64": {"type": "string", "description": "图片的 base64 编码数据"},
                    "top_k": {"type": "integer", "description": "返回前 k 个预测结果，默认5"},
                },
                "required": ["image_base64"],
            },
            category="vision",
        ))
        self.register(ToolSpec(
            name="deeplab_segment",
            description="DeepLabV3 语义分割：对作物叶片病斑进行像素级分割，计算病害面积占比。接收 base64 图片数据，返回分割结果。",
            handler=_make_handler("deeplabv3"),
            parameters={
                "type": "object",
                "properties": {
                    "image_base64": {"type": "string", "description": "图片的 base64 编码数据"},
                },
                "required": ["image_base64"],
            },
            category="vision",
        ))

    def register_vision_tool(
        self,
        name: str,
        description: str,
        handler: Callable,
        parameters: Dict[str, Any],
    ):
        """
        注册自定义视觉模型工具
        当用户训练好的模型就绪后，直接调用此方法注册。
        """
        self.register(ToolSpec(
            name=name,
            description=description,
            handler=handler,
            parameters=parameters,
            category="vision",
        ))
        self.VALID_TOOL_NAMES.add(name)
        logger.info(f"👁️ 已注册视觉工具: {name}")
