import { useNavigate } from "react-router";

export default function ErrorPage() {
  const navigate = useNavigate();

  const handleRetry = () => {
    window.location.reload();
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <div className="header-left">
          <button className="header-back" onClick={() => navigate(-1)}>
            <img src="/src/assets/images/chevronleft.png" alt="返回" />
          </button>
          <h1 className="header-title">网络异常</h1>
        </div>
      </div>

      <div className="error-content">
        <div className="error-icon">
          <img src="/src/assets/images/wifioff.png" alt="网络断开" />
        </div>
        <h2 className="error-title">网络连接已断开</h2>
        <p className="error-desc">
          请检查您的网络设置后重试
          <br />
          农业识别功能需要网络连接
        </p>

        <div className="error-actions">
          <button className="primary-btn" onClick={handleRetry}>
            <img src="/src/assets/images/refreshcw.png" alt="" />
            重新连接
          </button>
          <button className="secondary-btn" onClick={() => navigate("/home")}>
            返回首页
          </button>
        </div>

        <div className="error-tips">
          <p className="tips-title">排查建议</p>
          <div className="tip-item">
            <div className="tip-dot" />
            <span>检查 Wi-Fi 或移动数据是否开启</span>
          </div>
          <div className="tip-item">
            <div className="tip-dot" />
            <span>尝试关闭再开启飞行模式</span>
          </div>
          <div className="tip-item">
            <div className="tip-dot" />
            <span>离线时可查看已缓存知识库内容</span>
          </div>
        </div>
      </div>
    </div>
  );
}
