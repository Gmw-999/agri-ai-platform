import { useNavigate } from "react-router";

interface EmptyStateProps {
  type?: "history" | "chat" | "search";
}

export default function EmptyState({ type = "history" }: EmptyStateProps) {
  const navigate = useNavigate();

  const config = {
    history: {
      title: "暂无识别记录",
      desc: "您还没有进行过病虫害识别\n快去拍照识别试试吧",
      btnText: "去拍照识别",
      icon: "camera0",
      path: "/ai-chat",
    },
    chat: {
      title: "还没有对话记录",
      desc: "向 AI 助手描述作物症状\n或上传病害照片开始识别",
      btnText: "开始识别",
      icon: "messagecircle0",
      path: "/ai-chat",
    },
    search: {
      title: "未找到相关病害",
      desc: "没有找到相关内容\n试试换个关键词搜索",
      btnText: "咨询 AI 助手",
      icon: "searchx",
      path: "/ai-chat",
    },
  };

  const cfg = config[type];

  return (
    <div className="empty-state-container">
      <img src={`/src/assets/images/${cfg.icon}.png`} alt="" className="empty-icon" />
      <p className="empty-title">{cfg.title}</p>
      <p className="empty-desc">{cfg.desc}</p>
      <button
        className="primary-btn"
        onClick={() => navigate(cfg.path)}
      >
        {cfg.btnText}
      </button>
    </div>
  );
}
