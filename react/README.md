# 农智 AI 助手

农业智能问答小程序前端，配合 `agri_ai_service` 后端使用。

## 功能页面

- **首页** — 快捷入口（拍照识病、病虫害识别、农事天气、知识库、农事提醒）、病虫害预警、当季作物管理推荐
- **AI问答** — 流式对话界面（SSE），支持上传图片识别、清空会话
- **知识库** — 病害分类浏览（粮食作物/蔬菜/水果/花卉/经济作物）、搜索、详情查看
- **农事天气** — 实时天气展示、7天预报、农事操作建议、病虫害预警
- **我的** — 用户信息、识别统计、功能菜单

## 快速开始

```bash
# 安装依赖
npm install

# 开发模式
npm run dev

# 构建生产版本
npm run build

# 预览构建结果
npm run preview
```

## 后端接口

默认连接 `http://127.0.0.1:8000/api`，可在 `src/api/config.ts` 中修改。

- `POST /api/agent/chat` — Agent 智能对话（SSE 流式）
- `POST /api/run` — 简单对话
- `POST /api/vision/detect` — 视觉模型检测

## 技术栈

- React 19 + TypeScript
- Vite 7
- React Router 7
- SSE 流式响应
