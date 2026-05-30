import { useNavigate, useLocation } from "react-router";

const tabs = [
  { path: "/home", label: "首页", icon: "home" },
  { path: "/ai-chat", label: "AI问答", icon: "messagecircle" },
  { path: "/knowledge", label: "知识库", icon: "bookopen" },
  { path: "/profile", label: "我的", icon: "user" },
];

export default function BottomNav() {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <div className="bottom-nav">
      <div className="bottom-nav-inner">
        {tabs.map((tab) => {
          const active = location.pathname.startsWith(tab.path);
          return (
            <button
              key={tab.path}
              className={`bottom-nav-item ${active ? "active" : ""}`}
              onClick={() => navigate(tab.path)}
            >
              <img
                src={`/src/assets/images/${tab.icon}${active ? "" : "0"}.png`}
                alt={tab.label}
                className="bottom-nav-icon"
              />
              <span className="bottom-nav-label">{tab.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
