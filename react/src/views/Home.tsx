import { useNavigate } from "react-router";
import BottomNav from "../components/BottomNav";

const quickActions = [
  { label: "病虫害识别", icon: "bug", path: "/ai-chat" },
  { label: "农事天气", icon: "cloudsun", path: "/weather" },
  { label: "农技知识库", icon: "bookopen", path: "/knowledge" },
  { label: "农事提醒", icon: "bell", path: "/weather" },
];

export default function Home() {
  const navigate = useNavigate();

  return (
    <div className="page-container">
      {/* Header */}
      <div className="page-header">
        <div className="header-left">
          <div className="header-logo" />
          <h1 className="header-title">农智 AI 助手</h1>
        </div>
        <button className="header-notif" onClick={() => navigate("/weather")}>
          <img src="/src/assets/images/bell0.png" alt="通知" />
        </button>
      </div>

      <div className="home-content">
        {/* Photo Identify CTA */}
        <div className="home-cta-card" onClick={() => navigate("/ai-chat")}>
          <div className="cta-icon">
            <img src="/src/assets/images/camera.png" alt="拍照识病" />
          </div>
          <div className="cta-text">
            <p className="cta-title">拍照识病</p>
            <p className="cta-sub">拍照 / 相册上传 AI 智能分析病虫害</p>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="quick-actions-grid">
          {quickActions.map((action) => (
            <button
              key={action.label}
              className="quick-action-card"
              onClick={() => navigate(action.path)}
            >
              <div className="qa-icon">
                <img
                  src={`/src/assets/images/${action.icon}.png`}
                  alt={action.label}
                />
              </div>
              <span className="qa-label">{action.label}</span>
            </button>
          ))}
        </div>

        {/* Pest Alert */}
        <div className="section-card">
          <div className="section-header">
            <div className="section-title-row">
              <img src="/src/assets/images/trianglealert.png" alt="" />
              <span className="section-title">本地病虫害预警</span>
            </div>
          </div>

          <div className="alert-item warning">
            <span className="alert-tag high">高风险</span>
            <p className="alert-text">
              水稻稻瘟病 — 近7日感染风险极高，建议提前防治
            </p>
          </div>
          <div className="alert-item">
            <span className="alert-tag mid">中风险</span>
            <p className="alert-text">
              玉米蚜虫 — 气温升高，注意田间监测
            </p>
          </div>
        </div>

        {/* Seasonal Crop Management */}
        <div className="section-card">
          <div className="section-header">
            <div className="section-title-row">
              <span className="section-title">当季作物管理推荐</span>
            </div>
            <button
              className="section-more"
              onClick={() => navigate("/ai-chat")}
            >
              查看更多 &gt;
            </button>
          </div>

          <div className="crop-item">
            <img
              src="/src/assets/images/sprout.png"
              alt=""
              className="crop-icon"
            />
            <div className="crop-info">
              <p className="crop-name">水稻 — 分蘖期管理</p>
              <p className="crop-desc">注意水位控制，适时追施氮肥</p>
            </div>
          </div>
          <div className="crop-item">
            <img
              src="/src/assets/images/leaf.png"
              alt=""
              className="crop-icon"
            />
            <div className="crop-info">
              <p className="crop-name">蔬菜 — 梅雨季节防病指南</p>
              <p className="crop-desc">通风透气，减少叶面湿度</p>
            </div>
          </div>
        </div>
      </div>

      <BottomNav />
    </div>
  );
}
