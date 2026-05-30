export default function LoadingOverlay({
  message = "AI 正在分析中…",
  subMessage = "多模型联合检测病害特征，请稍候",
  showModels = false,
}: {
  message?: string;
  subMessage?: string;
  showModels?: boolean;
}) {
  return (
    <div className="loading-overlay">
      <div className="loading-content">
        <div className="loading-spinner">
          <div className="spinner-ring" />
        </div>
        <p className="loading-message">{message}</p>
        <p className="loading-sub">{subMessage}</p>

        {showModels && (
          <div className="model-badges">
            <span className="model-badge">YOLO v8</span>
            <span className="model-badge">ResNet</span>
            <span className="model-badge">DeepLab</span>
          </div>
        )}

        <p className="loading-footer">识别中 · 农智 AI 助手</p>
      </div>
    </div>
  );
}
