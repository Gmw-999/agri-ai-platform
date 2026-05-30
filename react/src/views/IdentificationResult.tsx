import { useNavigate, useLocation } from "react-router";
import { useState } from "react";

interface DetectionResult {
  diseaseName: string;
  confidence: string;
  riskLevel: string;
  affectedParts: string;
  description: string;
  matches: Array<{ name: string; similarity: string }>;
}

export default function IdentificationResult() {
  const navigate = useNavigate();
  const location = useLocation();
  const result = (location.state as DetectionResult) || null;

  const [activeTab, setActiveTab] = useState(0);
  const tabs = ["病害特征", "发病原因", "防治方法", "用药建议"];

  const tabContent = [
    "病斑初期为椭圆形水渍状，后扩大成云纹状，边缘褐色，中部灰白色。病斑多从基部叶鞘开始发病，逐渐向上扩展，造成叶片枯死。湿度大时，叶面可见白色菌丝体。",
    "高温高湿环境易发病，种植密度过大、氮肥施用过量、田间通风透光差均可加重病害发生。连作地块发病较重。",
    "1、农业防治：合理密植，增施硅钾肥，控制氮肥用量。\n2、物理防治：及时清除病叶、病株，带出田外销毁。\n3、化学防治：发病初期使用三环唑、稻瘟灵等进行防治。",
    "推荐使用吡唑醚菌酯、三环唑、稻瘟灵等药剂。注意轮换用药，避免产生抗药性。施药时应选择无风天气，早晚进行，注意喷洒均匀。",
  ];

  if (!result) {
    return (
      <div className="page-container">
        <div className="page-header">
          <div className="header-left">
            <button className="header-back" onClick={() => navigate(-1)}>
              <img src="/src/assets/images/chevronleft.png" alt="返回" />
            </button>
            <h1 className="header-title">识别结果</h1>
          </div>
        </div>
        <div className="empty-state">
          <p>暂无识别结果</p>
          <button className="primary-btn" onClick={() => navigate("/ai-chat")}>
            去拍照识别
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      {/* Header */}
      <div className="page-header">
        <div className="header-left">
          <button className="header-back" onClick={() => navigate(-1)}>
            <img src="/src/assets/images/chevronleft.png" alt="返回" />
          </button>
          <h1 className="header-title">识别结果</h1>
        </div>
      </div>

      <div className="result-content">
        {/* Result Header */}
        <div className="result-header">
          <div className="result-image">
            <img src="/src/assets/images/CropImage.png" alt="识别图片" />
          </div>
          <div className="result-basic-info">
            <div className="result-name-row">
              <h2 className="result-disease-name">{result.diseaseName}</h2>
              <span className={`risk-badge ${result.riskLevel === "高风险" ? "high" : "mid"}`}>
                {result.riskLevel}
              </span>
            </div>
            <p className="result-match">匹配度 {result.confidence}</p>
            <p className="result-part">危害部位：{result.affectedParts}</p>
            <p className="result-desc">{result.description}</p>
          </div>
        </div>

        {/* Tabs */}
        <div className="result-tabs">
          {tabs.map((tab, i) => (
            <button
              key={tab}
              className={`result-tab ${activeTab === i ? "active" : ""}`}
              onClick={() => setActiveTab(i)}
            >
              {tab}
            </button>
          ))}
        </div>
        <div className="result-tab-content">
          <p>{tabContent[activeTab]}</p>
        </div>

        {/* Actions */}
        <div className="result-actions">
          <button className="result-action-btn">
            <img src="/src/assets/images/bookmark.png" alt="" />
            <span>收藏</span>
          </button>
          <button className="result-action-btn">
            <img src="/src/assets/images/share2.png" alt="" />
            <span>分享</span>
          </button>
          <button
            className="result-action-btn primary"
            onClick={() => navigate("/ai-chat")}
          >
            <img src="/src/assets/images/messagecircle.png" alt="" />
            <span>咨询专家</span>
          </button>
        </div>

        {/* Similar Diseases */}
        <div className="similar-section">
          <div className="similar-header">
            <span>相似病害</span>
            <span className="similar-more">查看更多</span>
          </div>
          <div className="similar-list">
            <div className="similar-item">
              <img src="/src/assets/images/Frame_2_183.png" alt="" />
              <div className="similar-info">
                <p className="similar-name">稻瘟病</p>
                <p className="similar-match">相似度 78%</p>
              </div>
            </div>
            <div className="similar-item">
              <img src="/src/assets/images/Frame_2_188.png" alt="" />
              <div className="similar-info">
                <p className="similar-name">白叶枯病</p>
                <p className="similar-match">相似度 65%</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
