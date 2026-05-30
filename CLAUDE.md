# CLAUDE.md

此文件为 Claude Code (claude.ai/code) 在此仓库中工作时提供项目指引。

## 项目概述

农智 AI 助手 —— 多端农业智能平台。FastAPI 后端集成 LLM Agent 对话、计算机视觉模型（YOLOv8/ResNet/DeepLabV3）、农药数据库查询、农事提醒管理。

## 仓库目录结构

| 目录 | 用途 |
|------|------|
| `claude code+doubao/agri_ai_service/` | Python 后端（FastAPI + Agent 引擎） |
| `agri-uni-app/` | uni-app (Vue 3) 主前端 → 微信小程序 |
| `agri-miniapp/` | Taro (React) 备选前端 → 微信小程序 |
| `react/` | React + Vite + TypeScript Web 前端 |
| `yolo-weights/`、`resnet-weights/`、`deeplabv3_best.pth` | 视觉模型权重文件 |

## 后端：`agri_ai_service/`

### 启动开发

```bash
cd "claude code+doubao/agri_ai_service"
# Windows 一键启动:
run_server.bat
# 或命令行:
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

API 服务运行在 `http://192.168.43.228:8000`（通过 `.env` 中的 `API_SERVER_HOST` 配置）。

### 代码架构

```
api/main.py              # FastAPI 应用入口，所有 /api/* 路由注册，全局初始化
api/routers/knowledge.py # /api/knowledge/*  知识库增删改查
api/routers/reminder.py  # /api/reminder/*   农事提醒 + 日历 + 天气建议 + AI诊断创建提醒
agent/agent_core.py      # Agent 核心引擎：规划 → 执行工具 → 合成回复
agent/tool_registry.py   # 工具注册、JSON Schema 参数校验、频率限制（每会话每工具5次/分钟）
agent/memory.py          # 会话记忆（滑动窗口）、用户画像管理器
agent/drug_enricher.py   # 后处理：正则提取药品名 → MySQL 查购买链接 → 内联插入按钮
agent/vision_service.py  # 视觉模型编排（自动/手动检测）
core/llm_factory.py      # LLM 单例工厂（DeepSeek / 豆包可切换）
core/llm_deepseek.py     # DeepSeek API 客户端
core/llm_wrapper.py      # 豆包（字节跳动）API 客户端
tools/agri_tools.py      # 核心农业工具实现（天气、病虫害预报、农事建议等）
tools/nongyao_search.py  # 农药信息网 (nongyao001.com) 爬虫
tools/custom_models.py   # YOLOv8 / ResNet / DeepLabV3 推理
tools/db_config.py       # MySQL 连接配置
tools/vector_db.py       # ChromaDB 向量知识库
config/settings.py       # 全局配置、LLM 初始化、Excel 加载（旧版）
utils/db.py              # MySQL 查询工具（query_all / query_one / execute / execute_last_id）
utils/cache.py           # 内存缓存（天气、农药、知识库）
```

### API 端点

| 方法 | 路径 | 功能 |
|------|------|------|
| POST | `/api/agent/chat` | Agent 主对话（LLM + 工具 + 药品链接增强） |
| POST | `/api/run` | 旧版简单对话 |
| POST | `/api/vision/detect` | 视觉模型手动调用 |
| POST | `/api/vision/crop_classify` | 作物分类 |
| GET | `/api/weather` | 天气查询 |
| GET | `/api/proxy/image?url=` | 图片代理（绕过微信域名白名单） |

### Agent 处理流程

`AgentCore.process()` 的执行顺序：问候快速通道 → 图片分析（如有图片数据）→ LLM 规划 → 工具执行（最多5步，带频率限制）→ 用户画像更新 → LLM 合成回复 → 药品链接增强（正则 + MySQL，不走 LLM）。

### 关键设计决策

- **大模型**：通过 `LLMFactory` 单例使用 DeepSeek (`deepseek-chat`)。修改 `config/settings.py` 中 `init_llm()` 调用即可切换供应商。
- **农药数据**：主数据源是 MySQL 表 `agri_pesticides_db.pesticides`（字段：`drug_name`、`image_url`、`purchase_url`）。`config/settings.py` 中的 Excel 文件是旧版/回退方案。`drug_enricher.py` 用正则从 LLM 回复中提取药品名，然后查 MySQL 插入 `[点击购买](url)` 购买按钮。
- **图片代理**：外部图片 URL（nongyao001.com、alicdn.com）在到达前端之前会被重写为 `/api/proxy/image?url=`，因为微信小程序会屏蔽非白名单域名的图片。
- **Agent 工具**：在 `tool_registry.py` 中注册，带有 JSON Schema 参数校验和每会话频率限制（每工具最多 5 次/分钟）。

### 数据库（MySQL）

- `agri_pesticides_db`：农药产品数据，用于用药推荐
- `agri_db`：应用数据（知识库、提醒、农事日志、用户画像）

连接凭据：`root` / `123456` @ `localhost:3306`

---

## 前端：`agri-uni-app/`（主前端 — 微信小程序）

Vue 3 Composition API (`<script setup>`) uni-app 项目。在 HBuilderX 中编译 → 微信开发者工具运行。

```
pages/
  home/index.vue       # 首页
  ai-chat/index.vue    # AI 对话（Agent 聊天 + 图片上传）
  result/index.vue     # 病虫害检测结果展示 + AI分析 + 创建提醒
  knowledge/           # 知识库（列表、详情、收藏、历史）
  weather/index.vue    # 农事天气
  reminder/            # 农事提醒（列表、添加、日历、病虫害预警）
  profile/index.vue    # 个人中心
utils/api.js           # 所有 API 调用封装、事件总线、图片处理
```

API 基础地址：`http://192.168.43.228:8000/api`（硬编码在 `utils/api.js` 中）。

微信小程序 AppID：`wxe8c4a191425defc1`

### 前端 Markdown 渲染

聊天页和结果页中的 `markdownToNodes()` 函数将 LLM 返回的 markdown 转为 `rich-text` 节点。会剥离原始 URL 以避免和 `[点击购买](url)` 按钮重复显示。图片使用 `<img>` 标签，必须经过代理端点（因为微信域名限制）。

购买链接的处理方式：不在 `rich-text` 中渲染 `<a>` 标签（微信小程序不支持外部导航），而是用 `parseSegments()` 按 `[点击购买](url)` 分割文本，在对应位置插入独立的 `<view>` 按钮，点击后调用 `uni.setClipboardData` 复制链接到剪贴板。

### 购买链接渲染机制

`parseSegments()` 函数负责：
1. 将回复文本按 `[点击购买](url)` 分割成段落（segments）
2. 每个段落要么是 `richtext` 类型（文字/图片/加粗），要么是 `purchase` 类型（购买按钮）
3. 模板遍历段落，`richtext` 用 `<rich-text>` 渲染，`purchase` 用独立 `<view>` 按钮渲染
4. 按钮点击执行 `copyPurchaseUrl(url)`，复制链接 + 弹出"请在浏览器中打开"提示

两个页面使用了相同机制：
- `ai-chat/index.vue`：每条消息存 `msg.segments` 数组
- `result/index.vue`：存在 `combinedSegments` ref 中

---

## 前端：`react/`（Web 端）

```bash
cd react
npm run dev      # Vite 开发服务器
npm run build    # 生产构建
npm run lint     # ESLint 检查
```

React 19 + React Router 7 + TypeScript + Vite 7。Web 端购买链接使用标准 `<a>` 标签，浏览器可直接跳转。

---

## 前端：`agri-miniapp/`（Taro 备选）

基于 Taro 的微信小程序。`npm run dev:weapp` 编译运行。
