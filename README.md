# 农智 AI 助手 (Agri AI Assistant)

多端农业智能平台，集成大模型 Agent 对话、计算机视觉识别（YOLOv8/ResNet/DeepLabV3）、农药数据库查询、农技知识库、农事提醒管理。

## 项目结构

```
├── claude code+doubao/agri_ai_service/   # Python 后端 (FastAPI + Agent 引擎)
├── agri-uni-app/                         # uni-app (Vue 3) → 微信小程序（主前端）
├── agri-miniapp/                         # Taro (React) → 微信小程序（备选）
├── react/                                # React + Vite + TypeScript → Web 前端
├── yolo-weights/                         # YOLOv8 模型权重
├── resnet-weights/                       # ResNet 模型权重
├── deeplabv3_best.pth                    # DeepLabV3 模型权重
└── CLAUDE.md                             # AI 辅助开发文档
```

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI + Uvicorn |
| 大模型 | DeepSeek API / 豆包（字节跳动） |
| 视觉模型 | YOLOv8（目标检测）、ResNet（病害分类）、DeepLabV3（病斑分割） |
| 数据库 | MySQL (PyMySQL) + ChromaDB（向量检索） |
| 小程序（主） | uni-app（Vue 3 Composition API）→ 微信小程序 |
| 小程序（备） | Taro 4.x（React 18）→ 微信小程序 |
| Web 端 | React 19 + React Router 7 + TypeScript + Vite 7 |

## 快速开始

### 环境要求

- Python 3.10+（推荐 Anaconda）
- MySQL 8.0+
- Node.js 18+（前端）
- HBuilderX（编译 uni-app）
- 微信开发者工具

### 1. 启动后端

```bash
cd "claude code+doubao/agri_ai_service"

# Windows 一键启动
run_server.bat

# 或命令行启动
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

服务运行在 `http://localhost:8000`，API 交互文档自动生成在 `http://localhost:8000/docs`。

### 2. 初始化数据库

```sql
-- 创建数据库
CREATE DATABASE IF NOT EXISTS agri_db DEFAULT CHARSET utf8mb4;
CREATE DATABASE IF NOT EXISTS agri_pesticides_db DEFAULT CHARSET utf8mb4;

-- 导入表结构（在 agri_db 库中执行）
SOURCE data/agri_knowledge.sql;
```

MySQL 默认连接：`root / 123456 @ localhost:3306`，可在 `utils/db.py` 中修改。

### 3. 前端启动

**uni-app 小程序（主前端）**

用 HBuilderX 打开 `agri-uni-app/` 目录 → 运行 → 运行到小程序模拟器 → 微信开发者工具。

API 地址在 `agri-uni-app/utils/api.js` 中配置（`API_HOST` 和 `API_PORT`）。

**React Web 端**

```bash
cd react
npm install
npm run dev      # 开发模式
npm run build    # 生产打包
```

**Taro 小程序（备选前端）**

```bash
cd agri-miniapp
npm install
npm run dev:weapp   # 开发模式
```

### 4. 模型权重

将训练好的权重文件放到项目根目录：
- `yolo-weights/` — YOLOv8 检测模型
- `resnet-weights/` — ResNet 分类模型
- `deeplabv3_best.pth` — DeepLabV3 分割模型

---

## 后端架构

```
api/
  main.py                  # FastAPI 入口，全局初始化，注册所有 /api/* 路由
  routers/
    knowledge.py            # /api/knowledge/*   知识库增删改查
    reminder.py             # /api/reminder/*    农事提醒 + 日历 + 天气建议

agent/
  agent_core.py             # Agent 核心：规划 → 执行工具 → 合成回复
  tool_registry.py          # 工具注册 / JSON Schema 参数校验 / 频率限制
  memory.py                 # 会话记忆（滑动窗口）/ 用户画像管理
  drug_enricher.py          # 后处理：正则提取药品名 → MySQL 查购买链接 → 内联插入
  vision_service.py         # 视觉模型编排（自动/手动检测）

core/
  llm_factory.py            # LLM 单例工厂（DeepSeek / 豆包可切换）
  llm_deepseek.py           # DeepSeek API 客户端
  llm_wrapper.py            # 豆包（ByteDance）API 客户端

tools/
  agri_tools.py             # 核心工具：天气、病虫害预报、农事建议、知识检索
  nongyao_search.py         # 农药信息网爬虫
  custom_models.py          # YOLOv8 / ResNet / DeepLabV3 推理
  db_config.py              # MySQL 连接配置
  vector_db.py              # ChromaDB 向量知识库

config/settings.py          # 全局配置 / LLM初始化
utils/
  db.py                     # MySQL 查询工具（query_all / query_one / execute）
  cache.py                  # 内存缓存（天气 / 农药 / 知识库）
```

### Agent 处理流程

```
用户消息 → 问候快速通道 → 图片分析（如有图片）
→ LLM 规划 → 执行工具（最多 5 步，带频率限制）
→ 更新用户画像 → LLM 合成回复
→ 药品链接增强（正则 + MySQL，不走 LLM）
```

---

## API 接口一览

### Agent 对话 & 视觉

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/agent/chat` | Agent 主对话（LLM + 工具 + 药品增强） |
| POST | `/api/run` | 旧版简单对话 |
| POST | `/api/vision/detect` | 视觉模型手动调用 |
| POST | `/api/vision/crop_classify` | 作物分类 |
| GET | `/api/weather` | 天气查询 |
| GET | `/api/proxy/image?url=` | 图片代理（绕过微信域名限制） |

### 农事提醒

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/reminder/list` | 提醒列表（支持状态/日期筛选） |
| POST | `/api/reminder/create` | 手动创建提醒 |
| POST | `/api/reminder/create-from-advice` | 从 AI 诊断结果自动创建提醒 |
| PUT | `/api/reminder/update` | 更新提醒 |
| DELETE | `/api/reminder/delete` | 删除提醒 |
| GET | `/api/reminder/calendar` | 农事日历（按月查询） |
| GET | `/api/reminder/weather-advice` | 天气农事建议 |
| GET | `/api/reminder/pest-warnings` | 病虫害预警 |

### 知识库

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/knowledge/categories` | 知识分类列表 |
| GET | `/api/knowledge/list` | 知识条目列表（支持分类/搜索/分页） |
| GET | `/api/knowledge/detail` | 知识详情 |
| POST | `/api/knowledge/favorite` | 收藏 / 取消收藏 |
| GET | `/api/knowledge/favorites` | 我的收藏 |
| GET | `/api/knowledge/history` | 浏览历史 |

---

## 数据库

### agri_db（业务数据库）

| 表名 | 说明 |
|------|------|
| `agri_knowledge_categories` | 知识分类（作物类别） |
| `agri_knowledge` | 知识条目（病害/虫害详情、防治方法、推荐用药） |
| `user_favorites` | 用户收藏 |
| `user_browse_history` | 浏览历史 |
| `agri_reminders` | 农事提醒 |
| `pest_warnings` | 病虫害预警 |
| `agri_advice_logs` | AI 诊断日志备份 |

### agri_pesticides_db（农药商品库）

| 表名 | 说明 |
|------|------|
| `pesticides` | 农药产品数据（drug_name, image_url, purchase_url） |

数据来源：[农药信息网 (nongyao001.com)](https://www.nongyao001.com)

---

## 小程序页面

| 页面 | 路径 | 说明 |
|------|------|------|
| 首页 | `pages/home/index` | 功能入口 |
| AI 问答 | `pages/ai-chat/index` | Agent 对话 + 拍照上传 |
| 识别结果 | `pages/result/index` | 模型检测结果 + AI 综合分析 + 创建提醒 |
| 知识库 | `pages/knowledge/index` | 病虫害知识浏览 |
| 知识详情 | `pages/knowledge/detail` | 病害详情 + 防治方法 |
| 我的收藏 | `pages/knowledge/favorites` | 收藏列表 |
| 浏览历史 | `pages/knowledge/history` | 历史记录 |
| 农事天气 | `pages/weather/index` | 天气查询 |
| 农事提醒 | `pages/reminder/index` | 提醒列表 |
| 新建提醒 | `pages/reminder/add` | 手动创建提醒 |
| 农事日历 | `pages/reminder/calendar` | 月度日历视图 |
| 病虫预警 | `pages/reminder/pest-warning` | 病虫害高发预警 |
| 个人中心 | `pages/profile/index` | 用户中心 |

小程序 AppID：`wxe8c4a191425defc1`

---

## 关键设计说明

- **LLM 切换**：在 `config/settings.py` 中修改 `init_llm()` 调用即可切换 DeepSeek / 豆包
- **药品链接增强**：后端 `drug_enricher.py` 用正则从 LLM 回复中提取药品名 → MySQL 查购买链接 → 插入 `[点击购买](url)` 按钮。不走 LLM，避免幻觉
- **图片代理**：`nongyao001.com` 和 `alicdn.com` 等外部图片 URL 会被重写为 `/api/proxy/image?url=`，因为微信小程序会屏蔽非白名单域名的图片
- **购买链接**：微信小程序的 `rich-text` 组件不支持 `<a>` 标签导航，所以购买按钮改为独立 `<view>` 组件，点击后复制链接到剪贴板
- **Agent 工具**：注册在 `tool_registry.py`，每个工具都有 JSON Schema 参数校验，每个会话每工具限 5 次/分钟

---

## 环境变量

在 `agri_ai_service/` 目录下创建 `.env` 文件：

```env
# 大模型 API 密钥
DEEPSEEK_API_KEY=你的密钥
DOUBAO_API_KEY=你的密钥

# 服务器
API_SERVER_HOST=192.168.43.228
API_SERVER_PORT=8000

# 百度 AI（OCR）
BAIDU_API_KEY=你的密钥
BAIDU_SECRET_KEY=你的密钥

# 和风天气 API
QWEATHER_API_KEY=你的密钥
```

---

## 开发参考

更详细的技术文档见 [CLAUDE.md](./CLAUDE.md)，包含每个模块的职责说明和代码架构细节。
