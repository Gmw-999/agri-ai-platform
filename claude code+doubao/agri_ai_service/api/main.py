import sys
import asyncio
import json
import logging
import os
import subprocess
import re
from pathlib import Path

# 解决 Windows 下 OpenMP 多副本冲突（必须在 torch 导入前设置）
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

# 项目根目录加入Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 强制 UTF-8 编码（必须在任何 stdio 包装之前执行）
from utils.common import force_utf8_encoding
force_utf8_encoding()


# ====================== Windows 双保险 stdio ======================
# 目标：控制台有输出，同时永不崩溃。
# 策略：
#   1. os.dup2 把 OS 层 fd 1/2 重定向到文件（C 层/第三方库写入安全）
#   2. Python 层用 _DualStream：同时写控制台 + 文件
#      - 控制台可用 → 用户看到日志
#      - 控制台关闭 → 自动降级到文件，不抛异常
_log_dir = Path(__file__).parent.parent / "logs"
_log_dir.mkdir(parents=True, exist_ok=True)

if sys.platform == 'win32':
    # 保存已 UTF-8 编码的 Python 控制台流（供 _DualStream 使用）
    _console_out_stream = sys.stdout
    _console_err_stream = sys.stderr
    # 备份原始控制台 fd（必须在 dup2 之前做）
    _console_out_fd = os.dup(1)
    _console_err_fd = os.dup(2)

    # 打开文件 fd 用于安全写入
    _safe_out_fd = os.open(str(_log_dir / 'stdout.log'), os.O_WRONLY | os.O_CREAT | os.O_APPEND)
    _safe_err_fd = os.open(str(_log_dir / 'stderr.log'), os.O_WRONLY | os.O_CREAT | os.O_APPEND)

    # 用 os.dup2 把 fd 1/2 重定向到文件
    # 此后所有 C 层写入（os.fdopen(1)、print_error 等）都去文件，安全
    os.dup2(_safe_out_fd, 1)
    os.dup2(_safe_err_fd, 2)
    os.close(_safe_out_fd)
    os.close(_safe_err_fd)

    # Python 层双写流：同时写控制台 + 文件
    class _DualStream:
        """双写流：控制台（Python 流）+ 文件，任一失败不影响另一个"""

        def __init__(self, console_stream, console_fd: int, file_fd: int):
            self._console_stream = console_stream  # UTF-8 TextIOWrapper
            self._console_fd = console_fd          # 原始控制台 fd（降级用）
            self._file_fd = file_fd                # 当前 fd 1/2（已指向文件）

        def write(self, data):
            encoded = data.encode('utf-8', errors='replace') if isinstance(data, str) else data
            # 写控制台（优先用 Python 流，降级到 raw fd）
            try:
                self._console_stream.write(data)
                self._console_stream.flush()
            except Exception:
                try:
                    os.write(self._console_fd, encoded)
                except Exception:
                    pass
            # 写文件 fd（永不跳过 — C 层安全 + 消息不丢）
            try:
                os.write(self._file_fd, encoded)
            except Exception:
                pass

        def flush(self):
            try:
                self._console_stream.flush()
            except Exception:
                pass

        def isatty(self):
            try:
                return self._console_stream.isatty()
            except Exception:
                return False

        def close(self):
            pass

        @property
        def closed(self):
            return False

        @property
        def encoding(self):
            return 'utf-8'

        @property
        def buffer(self):
            """供 force_utf8_encoding() 等函数访问底层的 binary buffer"""
            return self._console_stream.buffer


    # 用已 UTF-8 编码的流包裹 _DualStream
    sys.stdout = _DualStream(_console_out_stream, _console_out_fd, 1)
    sys.stderr = _DualStream(_console_err_stream, _console_err_fd, 2)
    sys.__stdout__ = sys.stdout
    sys.__stderr__ = sys.stderr

# 第三方库导入
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
import pandas as pd

# 本地模块导入
from utils.logger import init_app_logging, get_logger
from utils.production import suppress_noisy_warnings
from utils.cache import weather_cache, pesticide_cache, knowledge_cache
from config.settings import llm, df as pesticide_df, FORCE_ENCODING
from utils.common import ensure_utf8_string, force_utf8_encoding
from tools.agri_tools import (
    set_global_deps,
    _get_dep,
    simple_drug_links,
    pest_treatment_from_image,
    enhanced_agri_knowledge_query,
    pesticide_dilute,
    pest_risk_forecast_online, farm_weather_advice, farm_log_operation, crop_growth_management
)
from agent import AgentCore

# ====================== 核心全局变量 ======================
chat_memory = []
MAX_MEMORY_ROUNDS = 5

# ====================== 初始化日志系统 ======================
logger = init_app_logging(debug=False)
logger.info("农业智能体API启动中...")

# ====================== 屏蔽生产噪音警告 ======================
suppress_noisy_warnings()

# ====================== 日志编码（已在顶部提前执行 force_utf8_encoding） ======================

# 让 uvicorn 的日志传播到我们的文件处理器（日志配置由 log_config=None 接管）
for _uv_logger in ('uvicorn', 'uvicorn.error', 'uvicorn.access'):
    _l = logging.getLogger(_uv_logger)
    _l.handlers.clear()
    _l.propagate = True
    _l.setLevel(logging.INFO)


# ====================== FastAPI ======================
app = FastAPI(title="农业智能体API（极简5轮记忆版）")

# 注册子路由
from api.routers.knowledge import router as knowledge_router
from api.routers.reminder import router as reminder_router
app.include_router(knowledge_router)
app.include_router(reminder_router)


# ====================== 跨域 ======================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ====================== 依赖注入 ======================
# 先导入搜索工具
from tools.nongyao_search import Nongyao001Searcher
from tools.vector_db import AgriVectorDB

# 初始化搜索（使用农药信息网搜索器，返回真实图片/购买链接）
searcher = Nongyao001Searcher()

# 初始化向量数据库
try:
    agri_vector_db = AgriVectorDB()
    logger.info(f"向量数据库初始化成功 | 文档数: {agri_vector_db.get_document_count()}")
except Exception as e:
    logger.warning(f"向量数据库初始化失败（不影响核心功能）: {e}")
    agri_vector_db = None

# 注入（使用关键字参数避免位置错乱）
set_global_deps(llm=llm, pesticide_df=pesticide_df, vector_db=agri_vector_db, searcher=searcher)
logger.info(f"依赖注入完成 | 农药记录数：{len(pesticide_df) if pesticide_df is not None else 0}")

# ====================== Agent 引擎初始化 ======================
agent_engine = AgentCore()
logger.info("Agent 智能引擎初始化完成")
# =============================================================
# ====================== 请求模型 ======================
class ChatRequest(BaseModel):
    func: str
    message: str


class AgentChatRequest(BaseModel):
    """Agent 智能助理请求"""
    message: str
    session_id: str = "default"
    openid: str = ""
    image_base64: str = ""  # 可选的 base64 图片数据


class VisionDetectRequest(BaseModel):
    """视觉模型手动调用请求"""
    model_name: str = "yolov8"  # yolov8 / resnet / deeplabv3
    image_base64: str
    params: dict = {}  # 额外参数，如 {"confidence": 0.5, "top_k": 3}


# ====================== 工具路由（完整稳定版） ======================
# ====================== 核心回答逻辑 ======================
def agent_answer(user_msg: str) -> str:
    user_msg = ensure_utf8_string(user_msg)
    tool_result = ""
    llm = _get_dep("llm")
    logger.debug(f"处理用户消息: {user_msg[:50]}...")
    try:
        # ====================== 【已精细化·互不干扰】 ======================
        if any(k in user_msg for k in ["高发期", "病虫害预报", "病虫害预警","病虫害情况","预测", "病虫害预测", "虫害预警", "病害预警", "病虫害情况", "虫情预报", "病情预报"]):
            logger.info("🔧 调用：病虫害高发期预报（联网搜索）")
            try:
                extract_prompt = f"""任务：从用户问题中提取【地区、作物、月份】。仅输出标准JSON。格式：{{"region":"","crop":"","month":1}}。问题：{user_msg}"""
                raw = llm.invoke(extract_prompt, temperature=0.0)
                data = json.loads(raw.strip().replace("```json", "").replace("```", ""))
                tool_result = pest_risk_forecast_online(
                    region=data.get("region", ""),
                    crop=data.get("crop", ""),
                    month=data.get("month", 1)
                )
            except Exception as e:
                logger.error(f"预报流程异常: {e}")
                tool_result = json.dumps({"error":"搜索服务异常，已切换本地专家模式"}, ensure_ascii=False)

        elif any(k in user_msg for k in ["推荐农药","购买链接" ,"药品","低毒农药","低毒药品","用哪种药","用啥药","哪种药", "买农药", "农药购买", "农药链接", "买药", "农药推荐", "杀虫剂推荐","推荐用药", "杀菌剂推荐"]):
            logger.info("🔧 调用：农药推荐")
            tool_result = simple_drug_links(user_msg)

        elif any(k in user_msg for k in ["怎么防治", "如何防治", "咋处理","如何解决","怎么治疗","咋防治", "如何治疗", "防治方法", "防治方案","防控方案", "防治措施", "怎么打药治"]):
            logger.info("🔧 调用：病虫害防治方案")
            tool_result = pest_treatment_from_image(user_msg, "农作物")

        elif any(k in user_msg for k in ["生长期管理", "生长期怎么管", "田间管理方案", "月份管理", "栽培管理", "作物管理", "管理要点"]):
            tool_result = crop_growth_management(user_msg)

        elif any(k in user_msg for k in ["记录田间", "记录农事", "添加田间日志", "查看农事日志", "查看田间记录", "删除农事记录", "我的田间日志"]):
            tool_result = farm_log_operation(user_msg)

        elif any(k in user_msg for k in ["稀释倍数","稀释","要加多少水","配药计算", "兑水量计算", "药剂兑水", "农药兑水", "多少水配药", "毫升配水", "克数兑水"]):
            logger.info("🔧 调用：农药稀释计算器")
            tool_result = pesticide_dilute(user_msg)

        elif any(k in user_msg for k in ["天气", "气象", "下雨", "温度", "风力", "湿度", "适不适合打药", "能否打药", "适合施肥", "适合浇水", "今天能打药吗", "今天能施肥吗", "农事天气"]):
            logger.info("🔧 调用：真实天气API+LLM农事建议")
            tool_result = farm_weather_advice(user_msg)

        else:
            logger.info("🔧 调用：农业知识查询")
            tool_result = enhanced_agri_knowledge_query(user_msg)

        tool_result = ensure_utf8_string(tool_result)

    except Exception as e:
        logger.error(f"❌ 工具调用总失败：{str(e)}")
        tool_result = json.dumps({"error": "服务异常，请稍后再试"}, ensure_ascii=False)

    # ====================== 拼接记忆 ======================
    history_text = ""
    for item in chat_memory:
        role = "用户" if item["role"] == "user" else "助手"
        history_text += f"{role}：{item['content']}\n"

    prompt = f"""
你是专业、耐心、实战型农业助手。
请严格根据参考信息回答，不编造、不乱答。

【历史对话】
{history_text}

用户问题：{user_msg}
参考信息：{tool_result if tool_result else '无'}

输出规则：
1. 有天气数据必须用天气数据
2. 有药品数据正常展示
3. 语言通俗、专业、可直接操作
4. 只输出最终回答
5. 【重要】药品图片和购买链接：
   - 只有参考信息中明确提供了 image_url 字段时才输出图片：![药品名](URL)
   - 只有参考信息中明确提供了 purchase_url 字段时才输出购买链接：[点击购买](URL)
   - [点击购买](URL) 本身就是可点击按钮，严禁在后面或任何位置再重复写出原始URL文本！
   - 没有 image_url/purchase_url 字段时只写药品名称和用法用量，严禁编造任何URL。

请输出最终回答：
"""

    try:
        final_reply = llm.invoke(prompt).strip()
        return final_reply if final_reply else "抱歉，未查询到相关信息~"
    except Exception as e:
        logger.error(f"❌ LLM调用失败：{str(e)}")
        return "服务异常，请稍后再试"


# ====================== API接口 ======================
@app.post("/api/run")
async def api_run(req: ChatRequest):
    global chat_memory
    try:
        if req.func != "chat":
            return JSONResponse(status_code=400, content={"code":400,"msg":"仅支持chat","data":None})

        user_msg = req.message.strip()
        if not user_msg:
            return JSONResponse(status_code=400, content={"code":400,"msg":"消息不能为空","data":None})

        final_reply = agent_answer(user_msg)

        # 5轮记忆
        chat_memory.append({"role":"user","content":user_msg})
        chat_memory.append({"role":"assistant","content":final_reply})
        if len(chat_memory) > MAX_MEMORY_ROUNDS * 2:
            chat_memory = chat_memory[-MAX_MEMORY_ROUNDS*2:]

        # 一次性返回（不逐字延迟）
        return StreamingResponse(
            iter([json.dumps({"reply": final_reply}, ensure_ascii=False) + "\n"]),
            media_type="text/event-stream; charset=utf-8"
        )

    except Exception as e:
        logger.error(f"❌ API异常：{str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"code":500,"msg":f"服务器错误：{str(e)}","data":None}
        )


# ====================== Agent 智能助理接口 ======================
@app.post("/api/agent/chat")
async def agent_chat(req: AgentChatRequest):
    """
    智能助理接口（支持多轮对话、自动规划、工具调度）
    - 自动识别意图，拆解任务
    - 自动调度天气/植保/农药/知识工具
    - 基于 openid 的长期用户画像
    - 滑动窗口多轮记忆
    - 预留视觉模型接口
    """
    try:
        user_msg = req.message.strip()
        if not user_msg and not req.image_base64:
            return JSONResponse(status_code=400, content={
                "code": 400, "msg": "消息和图片不能同时为空", "data": None
            })

        # 解码图片（如果有）
        image_bytes = None
        if req.image_base64:
            from utils.image_utils import base64_to_image
            image_bytes, _ = base64_to_image(req.image_base64)
            if image_bytes is None:
                return JSONResponse(status_code=400, content={
                    "code": 400, "msg": "图片 Base64 解码失败", "data": None
                })

        # Agent 处理（支持图片）
        result = agent_engine.process(
            user_message=user_msg or "(用户上传了图片)",
            session_id=req.session_id,
            openid=req.openid,
            image_data=image_bytes,
        )

        reply = result["reply"]

        # 一次性返回元信息和回复（不逐字延迟）
        meta = {
            "type": "meta",
            "intent": result["intent"],
            "tools_used": result["tools_used"],
            "session_id": result["session_id"],
            "has_vision": bool(result.get("vision_results")),
        }
        reply_line = json.dumps({"type": "reply", "content": reply}, ensure_ascii=False)
        done_line = json.dumps({"type": "done"}, ensure_ascii=False)
        body = f"{json.dumps(meta, ensure_ascii=False)}\n{reply_line}\n{done_line}\n"

        return StreamingResponse(
            iter([body]),
            media_type="text/event-stream; charset=utf-8"
        )

    except Exception as e:
        logger.error(f"❌ Agent API异常：{str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"code": 500, "msg": f"服务器错误：{str(e)}", "data": None}
        )







# ====================== 视觉模型手动调用接口 ======================
@app.post("/api/vision/detect")
async def vision_detect(req: VisionDetectRequest):
    """
    前端手动调用指定的视觉小模型。
    - 支持 yolov8、resnet、deeplabv3
    - 前端传递 base64 图片 + 模型名称 + 额外参数
    - 返回模型推理结果（非流式）
    """
    try:
        from utils.image_utils import base64_to_image
        from agent.vision_service import VisionService

        # 解码图片
        image_bytes, mime = base64_to_image(req.image_base64)
        if image_bytes is None:
            return JSONResponse(status_code=400, content={
                "success": False, "error": "图片 Base64 解码失败"
            })

        # 调用视觉模型
        vs = VisionService()
        result = vs.manual_detect(req.model_name, image_bytes, **req.params)

        if not result.get("success"):
            return JSONResponse(status_code=400, content=result)

        return JSONResponse(content=result)

    except Exception as e:
        logger.error(f"❌ Vision API异常：{str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"视觉模型调用失败：{str(e)}"}
        )


# ====================== 病斑裁剪 + ResNet 分类（组合接口） ======================
@app.post("/api/vision/crop_classify")
async def vision_crop_classify(req: VisionDetectRequest):
    """
    病斑裁剪后分类：DeepLabV3 分割 → 病斑区域裁剪 → ResNet 分类
    去除背景干扰，提升 ResNet 识别准确率。
    """
    try:
        from utils.image_utils import base64_to_image
        from agent.vision_service import VisionService

        image_bytes, mime = base64_to_image(req.image_base64)
        if image_bytes is None:
            return JSONResponse(status_code=400, content={
                "success": False, "error": "图片 Base64 解码失败"
            })

        vs = VisionService()
        result = vs.crop_and_classify(image_bytes)

        if not result.get("success"):
            return JSONResponse(status_code=400, content=result)

        return JSONResponse(content=result)

    except Exception as e:
        logger.error(f"❌ CropClassify API异常：{str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"病斑裁剪分类失败：{str(e)}"}
        )


# ====================== 天气数据接口（结构化JSON） ======================
@app.get("/api/weather")
async def get_weather(region: str = "长沙"):
    """获取指定地区的实时天气和7天预报（结构化数据）"""
    from tools.agri_tools import get_real_weather
    data = get_real_weather(region)
    if not data:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"无法获取 {region} 的天气数据"}
        )
    return JSONResponse(content={"success": True, "data": data})


# ====================== 图片代理接口（绕过微信小程序域名白名单） ======================
import urllib.request
import urllib.error
from fastapi.responses import Response as FastAPIResponse

ALLOWED_IMAGE_DOMAINS = {
    "ima.nongyao001.com",
    "www.nongyao001.com",
    "nongyao001.com",
    "img.alicdn.com",
    "img.pic3.cn",
}


@app.get("/api/proxy/image")
async def proxy_image(url: str):
    """代理获取外部图片，解决微信小程序域名白名单限制"""
    from urllib.parse import urlparse

    # 校验域名白名单
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.split(":")[0]
        if domain not in ALLOWED_IMAGE_DOMAINS:
            return JSONResponse(status_code=403, content={"error": f"域名未授权: {domain}"})
    except Exception:
        return JSONResponse(status_code=400, content={"error": "无效的URL"})

    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.nongyao001.com/",
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read()
            content_type = resp.headers.get("Content-Type", "image/jpeg")
            return FastAPIResponse(content=content, media_type=content_type)
    except urllib.error.HTTPError as e:
        return JSONResponse(status_code=e.code, content={"error": f"图片加载失败: {e.code}"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# ====================== 启动 ======================
if __name__ == "__main__":
# ====================== Agent Trace 接口 ======================

@app.get("/api/traces")
async def get_traces(limit: int = 20):
    """获取最近的 Agent Trace 列表"""
    from utils.tracer import get_recent_traces
    traces = get_recent_traces(limit)
    return JSONResponse(content={"success": True, "traces": traces})


@app.get("/api/traces/{trace_id}")
async def get_trace_detail(trace_id: str):
    """获取单个 Trace 的详细信息"""
    from utils.tracer import get_trace_detail
    trace = get_trace_detail(trace_id)
    if not trace:
        return JSONResponse(status_code=404, content={"error": "Trace 不存在"})
    return JSONResponse(content={"success": True, "trace": trace})


@app.get("/api/traces/stats/summary")
async def get_trace_stats():
    """获取 Trace 统计信息"""
    from utils.tracer import get_trace_stats
    stats = get_trace_stats()
    return JSONResponse(content={"success": True, "stats": stats})


if __name__ == "__main__":
    import uvicorn
    if not llm:
        logger.error("LLM未初始化")
        sys.exit(1)
    logger.info("农业智能体API启动在 http://0.0.0.0:8000")
    # log_config=None 让 uvicorn 不配置日志（避免 Windows Git Bash 下控制台崩溃）
    # uvicorn 的日志通过根 logger 传播到我们的 RotatingFileHandler
    uvicorn.run(app, host="0.0.0.0", port=8000, log_config=None)
