import { useRef } from "react";

interface ImagePickerProps {
  onImage: (base64: string, file: File) => void;
  onClose: () => void;
}

export default function ImagePicker({ onImage, onClose }: ImagePickerProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);

  const handleFile = (file: File | undefined) => {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result as string;
      const base64 = result.split(",")[1] || result;
      onImage(base64, file);
    };
    reader.readAsDataURL(file);
  };

  return (
    <div className="image-picker-overlay" onClick={onClose}>
      <div className="image-picker-modal" onClick={(e) => e.stopPropagation()}>
        <p className="image-picker-title">选择识别方式</p>

        <button
          className="image-picker-btn"
          onClick={() => cameraInputRef.current?.click()}
        >
          <div className="picker-icon camera-icon" />
          <span>拍照识别</span>
        </button>

        <button
          className="image-picker-btn"
          onClick={() => fileInputRef.current?.click()}
        >
          <div className="picker-icon gallery-icon" />
          <span>从相册选择</span>
        </button>

        <button className="image-picker-cancel" onClick={onClose}>
          取消
        </button>
      </div>

      <input
        ref={cameraInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        style={{ display: "none" }}
        onChange={(e) => handleFile(e.target.files?.[0])}
      />
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        style={{ display: "none" }}
        onChange={(e) => handleFile(e.target.files?.[0])}
      />
    </div>
  );
}
