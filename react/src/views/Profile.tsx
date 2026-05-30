import { useNavigate } from "react-router";
import BottomNav from "../components/BottomNav";

const menuItems = [
  { icon: "camera", label: "识别历史", path: "/history" },
  { icon: "heart", label: "我的收藏", path: "" },
  { icon: "messagecircle", label: "咨询记录", path: "" },
  { icon: "settings", label: "记忆设置", path: "" },
  { icon: "bell", label: "消息订阅", path: "" },
  { icon: "info", label: "帮助反馈", path: "" },
  { icon: "share2", label: "关于我们", path: "" },
];

export default function Profile() {
  const navigate = useNavigate();

  return (
    <div className="page-container">
      {/* Profile Header */}
      <div className="profile-header">
        <div className="profile-avatar">
          <img src="/src/assets/images/user.png" alt="头像" />
        </div>
        <div className="profile-info">
          <h2 className="profile-name">张大农</h2>
          <p className="profile-location">湖南省长沙市 · 种植大户</p>
          <div className="profile-tags">
            <span className="profile-tag">水稻</span>
            <span className="profile-tag">蔬菜</span>
            <span className="profile-tag">玉米</span>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="profile-stats">
        <div className="stat-item">
          <p className="stat-value">128</p>
          <p className="stat-label">识别次数</p>
        </div>
        <div className="stat-divider" />
        <div className="stat-item">
          <p className="stat-value">36</p>
          <p className="stat-label">已收藏</p>
        </div>
        <div className="stat-divider" />
        <div className="stat-item">
          <p className="stat-value">15</p>
          <p className="stat-label">咨询记录</p>
        </div>
      </div>

      {/* Menu */}
      <div className="profile-menu">
        {menuItems.map((item) => (
          <button
            key={item.label}
            className="profile-menu-item"
            onClick={() => item.path && navigate(item.path)}
          >
            <div className="menu-item-left">
              <img
                src={`/src/assets/images/${item.icon}.png`}
                alt={item.label}
                className="menu-item-icon"
              />
              <span>{item.label}</span>
            </div>
            <img
              src="/src/assets/images/chevronright.png"
              alt=""
              className="menu-item-arrow"
            />
          </button>
        ))}
      </div>

      <BottomNav />
    </div>
  );
}
