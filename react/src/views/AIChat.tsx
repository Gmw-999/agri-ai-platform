import { useState, useEffect, useRef, useCallback, ReactNode } from "react";
import { useSearchParams } from "react-router";
import BottomNav from "../components/BottomNav";
import ImagePicker from "../components/ImagePicker";
import { agentChatStream, fileToBase64, AgentChatEvent } from "../api/client";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: number;
  imageBase64?: string;
  imagePreview?: string;
}

/** 渲染 AI 回复中的 markdown 图片和链接 */
function FormattedText({ text }: { text: string }) {
  if (!text) return null;

  // 拆分文本为段落，逐段处理
  const segments: ReactNode[] = [];
  const lines = text.split("\n");

  for (let li = 0; li < lines.length; li++) {
    const line = lines[li];
    if (!line.trim()) {
      segments.push(<br key={`br-${li}`} />);
      continue;
    }

    // 只处理带 `![` 或 `[` 的行
    if (!line.includes("![") && !line.includes("](")) {
      segments.push(<span key={`t-${li}`}>{line}</span>);
      if (li < lines.length - 1) segments.push(<br key={`br2-${li}`} />);
      continue;
    }

    // 用正则解析行内元素
    const parts: ReactNode[] = [];
    let remaining = line;
    let pi = 0;

    while (remaining.length > 0) {
      // 先找图片 ![alt](url)
      const imgMatch = remaining.match(/^!\[([^\]]*)\]\(([^)]+)\)/);
      if (imgMatch) {
        parts.push(
          <img
            key={`img-${li}-${pi}`}
            src={imgMatch[2]}
            alt={imgMatch[1]}
            className="drug-image"
            onError={(e) => {
              (e.target as HTMLImageElement).style.display = "none";
            }}
          />
        );
        remaining = remaining.slice(imgMatch[0].length);
        pi++;
        continue;
      }

      // 再找链接 [text](url)
      const linkMatch = remaining.match(/^\[([^\]]*)\]\(([^)]+)\)/);
      if (linkMatch) {
        parts.push(
          <a
            key={`link-${li}-${pi}`}
            href={linkMatch[2]}
            target="_blank"
            rel="noopener noreferrer"
            className="drug-link"
          >
            {linkMatch[1]}
          </a>
        );
        remaining = remaining.slice(linkMatch[0].length);
        pi++;
        continue;
      }

      // 普通文本直到下一个标记
      const nextImg = remaining.indexOf("![");
      const nextLink = remaining.indexOf("](");
      // ]( 只在前面有 [xxx 时才是链接标记
      let nextSpecial = remaining.length;
      if (nextImg >= 0) nextSpecial = Math.min(nextSpecial, nextImg);
      // 对于 ]( 往前找是否有 [
      if (nextLink >= 1 && remaining[nextLink - 1] === "]") {
        // 找到匹配的 [
        let searchStart = nextLink - 200;
        if (searchStart < 0) searchStart = 0;
        const before = remaining.slice(searchStart, nextLink);
        const bracketPos = before.lastIndexOf("[");
        if (bracketPos >= 0) {
          nextSpecial = Math.min(nextSpecial, searchStart + bracketPos);
        } else {
          nextSpecial = Math.min(nextSpecial, nextLink);
        }
      } else if (nextLink >= 0) {
        nextSpecial = Math.min(nextSpecial, nextLink);
      }

      const textPart = nextSpecial > 0 ? remaining.slice(0, nextSpecial) : remaining;
      if (textPart) parts.push(<span key={`t-${li}-${pi}`}>{textPart}</span>);
      remaining = remaining.slice(textPart.length);
      pi++;
    }

    segments.push(<div key={`line-${li}`} className="formatted-line">{parts}</div>);
  }

  return <>{segments}</>;
}

export default function AIChat() {
  const [searchParams] = useSearchParams();
  const [messages, setMessages] = useState<Message[]>(() => {
    // Initial greeting
    const initialQuery = searchParams.get("q");
    const msgs: Message[] = [
      {
        id: "init",
        role: "assistant",
        content:
          "您好！我是农智 AI 助手，您可以向我描述作物症状，或直接上传病害照片，我来帮您分析诊断。",
        timestamp: Date.now(),
      },
    ];
    if (initialQuery) {
      msgs.push({
        id: `q_${Date.now()}`,
        role: "user",
        content: initialQuery,
        timestamp: Date.now(),
      });
    }
    return msgs;
  });

  const [input, setInput] = useState(searchParams.get("q") || "");
  const [processing, setProcessing] = useState(false);
  const [showPicker, setShowPicker] = useState(false);
  const [showQuickActions, setShowQuickActions] = useState(true);
  const [streamingId, setStreamingId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const sessionIdRef = useRef(`session_${Date.now()}`);

  const scrollToBottom = useCallback(() => {
    setTimeout(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, 50);
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // Auto-send initial query
  useEffect(() => {
    const q = searchParams.get("q");
    if (q) {
      const timer = setTimeout(() => handleSend(q), 300);
      return () => clearTimeout(timer);
    }
  }, []);

  const addMessage = (msg: Message) => {
    setMessages((prev) => [...prev, msg]);
  };

  const updateLastMessage = (content: string) => {
    setMessages((prev) => {
      const msgs = [...prev];
      if (msgs.length > 0) {
        const last = msgs[msgs.length - 1];
        msgs[msgs.length - 1] = { ...last, content: last.content + content };
      }
      return msgs;
    });
  };

  const handleSend = async (text?: string, imageBase64?: string, imagePreview?: string) => {
    const msgText = text || input.trim();
    if (!msgText && !imageBase64) return;
    if (processing) return;

    setShowQuickActions(false);
    setInput("");

    // Add user message
    const userMsg: Message = {
      id: `u_${Date.now()}`,
      role: "user",
      content: msgText || "(上传了图片)",
      timestamp: Date.now(),
      imageBase64,
      imagePreview,
    };
    addMessage(userMsg);

    // Add placeholder assistant message
    const assistantId = `a_${Date.now()}`;
    addMessage({
      id: assistantId,
      role: "assistant",
      content: "",
      timestamp: Date.now(),
    });

    setProcessing(true);
    setStreamingId(assistantId);

    try {
      const stream = agentChatStream({
        message: msgText || "(用户上传了图片)",
        session_id: sessionIdRef.current,
        image_base64: imageBase64,
      });

      for await (const event of stream) {
        if (event.type === "error") {
          updateLastMessage(`抱歉，服务异常：${event.content}`);
          break;
        }
        if (event.type === "reply" && event.content) {
          updateLastMessage(event.content);
        }
        if (event.type === "done") {
          break;
        }
      }
    } catch (e) {
      updateLastMessage(
        "网络连接异常，请检查网络后重试。"
      );
    } finally {
      setProcessing(false);
      setStreamingId(null);
    }
  };

  const handleImagePick = async (base64: string, file: File) => {
    setShowPicker(false);
    const preview = URL.createObjectURL(file);
    await handleSend("", base64, preview);
  };

  const handleClearChat = () => {
    setMessages([
      {
        id: "init",
        role: "assistant",
        content:
          "您好！我是农智 AI 助手，您可以向我描述作物症状，或直接上传病害照片，我来帮您分析诊断。",
        timestamp: Date.now(),
      },
    ]);
    sessionIdRef.current = `session_${Date.now()}`;
    setShowQuickActions(true);
  };

  const quickActions = [
    { label: "YOLO检测", desc: "目标检测" },
    { label: "ResNet识别", desc: "图像分类" },
    { label: "DeepLab测算", desc: "病斑分割" },
    { label: "AI全自动分析", desc: "自动选择模型" },
  ];

  return (
    <div className="page-container">
      {/* Header */}
      <div className="page-header">
        <div className="header-left">
          <h1 className="header-title">AI 农业智能助手</h1>
        </div>
        <button className="header-action" onClick={handleClearChat}>
          清空会话
        </button>
      </div>

      <div className="chat-content">
        {/* Messages */}
        <div className="chat-messages">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`chat-bubble ${msg.role === "user" ? "user" : "assistant"}`}
            >
              {msg.role === "assistant" && (
                <div className="assistant-avatar">
                  <img src="/src/assets/images/Frame_2_565.png" alt="AI" />
                </div>
              )}
              <div className="bubble-content">
                {msg.imagePreview && msg.role === "user" && (
                  <img
                    src={msg.imagePreview}
                    alt="上传的图片"
                    className="bubble-image"
                  />
                )}
                <div className="bubble-text">
                  <FormattedText text={msg.content || ""} />
                  {streamingId === msg.id && msg.content && (
                    <span className="cursor-blink">|</span>
                  )}
                </div>
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Quick Actions */}
        {showQuickActions && !processing && (
          <div className="quick-actions-row">
            {quickActions.map((action) => (
              <button
                key={action.label}
                className="qa-chip"
                onClick={() => {
                  setInput(`使用${action.label}分析`);
                }}
              >
                {action.label}
              </button>
            ))}
          </div>
        )}

        {/* Input Area */}
        <div className="chat-input-area">
          <button
            className="input-btn upload-btn"
            onClick={() => setShowPicker(true)}
          >
            <img src="/src/assets/images/Frame_2_414.png" alt="上传" />
          </button>
          <div className="input-wrapper">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="输入问题或描述症状…"
              className="chat-input"
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              disabled={processing}
            />
          </div>
          <button
            className={`input-btn send-btn ${processing ? "disabled" : ""}`}
            onClick={() => handleSend()}
            disabled={processing}
          >
            <img src="/src/assets/images/send.png" alt="发送" />
          </button>
        </div>
      </div>

      {showPicker && (
        <ImagePicker
          onImage={handleImagePick}
          onClose={() => setShowPicker(false)}
        />
      )}

      <BottomNav />
    </div>
  );
}
