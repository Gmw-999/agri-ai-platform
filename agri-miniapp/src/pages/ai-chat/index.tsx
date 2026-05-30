import { View, Text, Image, Input, ScrollView } from '@tarojs/components';
import Taro from '@tarojs/taro';
import { useState, useEffect, useRef } from 'react';
import { agentChat, pickImage, genSessionId, on, off } from '../../api';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  imagePath?: string;
}

/**
 * Parse markdown links and images into renderable segments
 */
function parseRichText(text: string): Array<{ type: 'text' | 'link' | 'image'; content: string; url?: string }> {
  const segments: Array<{ type: 'text' | 'link' | 'image'; content: string; url?: string }> = [];
  // Match ![alt](url) images and [text](url) links
  const pattern = /!\[([^\]]*)\]\(([^)]+)\)|\[([^\]]+)\]\(([^)]+)\)/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = pattern.exec(text)) !== null) {
    // Plain text before this match
    if (match.index > lastIndex) {
      segments.push({ type: 'text', content: text.slice(lastIndex, match.index) });
    }

    if (match[1] !== undefined) {
      // Image: ![alt](url)
      segments.push({ type: 'image', content: match[1], url: match[2] });
    } else {
      // Link: [text](url)
      segments.push({ type: 'link', content: match[3], url: match[4] });
    }
    lastIndex = match.index + match[0].length;
  }

  // Remaining text
  if (lastIndex < text.length) {
    segments.push({ type: 'text', content: text.slice(lastIndex) });
  }

  return segments.length ? segments : [{ type: 'text', content: text }];
}

function RichText({ content }: { content: string }) {
  const segments = parseRichText(content);

  return (
    <View>
      {segments.map((seg, i) => {
        if (seg.type === 'link') {
          return (
            <Text
              key={i}
              style='color:#4A90D9;text-decoration:underline;word-break:break-all;'
              onClick={() => window.open(seg.url, '_blank')}
            >
              {seg.content}
            </Text>
          );
        }
        if (seg.type === 'image') {
          return (
            <Image
              key={i}
              src={seg.url}
              mode='widthFix'
              style='max-width:100%;margin:4px 0;border-radius:6px;'
              onClick={() => window.open(seg.url, '_blank')}
            />
          );
        }
        // Plain text
        return <Text key={i}>{seg.content}</Text>;
      })}
    </View>
  );
}

export default function AIChat() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'init',
      role: 'assistant',
      content: '您好！我是农智 AI 助手，您可以向我描述作物症状，或直接上传病害照片，我来帮您分析诊断。',
    },
  ]);
  const [input, setInput] = useState('');
  const [processing, setProcessing] = useState(false);
  const processingRef = useRef(false);
  const sessionId = useRef(genSessionId());
  const scrollRef = useRef<any>(null);

  const addMessage = (msg: Message) => {
    setMessages((prev) => [...prev, msg]);
  };

  const updateLastAssistant = (content: string) => {
    setMessages((prev) => {
      const msgs = [...prev];
      for (let i = msgs.length - 1; i >= 0; i--) {
        if (msgs[i].role === 'assistant') {
          msgs[i] = { ...msgs[i], content: msgs[i].content + content };
          break;
        }
      }
      return msgs;
    });
  };

  useEffect(() => {
    setTimeout(() => {
      Taro.pageScrollTo({ scrollTop: 99999, duration: 100 });
    }, 100);
  }, [messages]);

  // Listen for pending image from home page (拍照识病 → 自动分析)
  useEffect(() => {
    const handler = (pending: { base64: string; tempPath: string }) => {
      if (processingRef.current) return;

      const { base64, tempPath } = pending;

      addMessage({
        id: `u_${Date.now()}`,
        role: 'user',
        content: '(上传了图片)',
        imagePath: tempPath,
      });

      const assistantId = `a_${Date.now()}`;
      addMessage({
        id: assistantId,
        role: 'assistant',
        content: '正在分析图片 (YOLOv8 目标检测 → ResNet 分类 → DeepLabV3 分割)...',
      });
      processingRef.current = true;
      setProcessing(true);

      agentChat({
        message: '(用户上传了图片)',
        session_id: sessionId.current,
        image_base64: base64,
      }).then((reply) => {
        setMessages((prev) =>
          prev.map((m) => (m.id === assistantId ? { ...m, content: reply } : m))
        );
      }).catch((e: any) => {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? { ...m, content: `网络异常：${e.message || '请检查网络后重试'}` }
              : m
          )
        );
      }).finally(() => {
        processingRef.current = false;
        setProcessing(false);
      });
    };

    on('pendingImage', handler);
    return () => { off('pendingImage', handler); };
  }, []);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || processingRef.current) return;
    setInput('');

    addMessage({ id: `u_${Date.now()}`, role: 'user', content: text });
    const assistantId = `a_${Date.now()}`;
    addMessage({ id: assistantId, role: 'assistant', content: '' });
    processingRef.current = true;
    setProcessing(true);

    try {
      const reply = await agentChat({
        message: text,
        session_id: sessionId.current,
      });
      setMessages((prev) =>
        prev.map((m) => (m.id === assistantId ? { ...m, content: reply } : m))
      );
    } catch (e: any) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? { ...m, content: `网络异常：${e.message || '请检查网络后重试'}` }
            : m
        )
      );
    } finally {
      processingRef.current = false;
      setProcessing(false);
    }
  };

  const handlePickImage = async () => {
    try {
      const { base64, tempPath } = await pickImage('album');
      addMessage({
        id: `u_${Date.now()}`,
        role: 'user',
        content: '(上传了图片)',
        imagePath: tempPath,
      });

      const assistantId = `a_${Date.now()}`;
      addMessage({
        id: assistantId,
        role: 'assistant',
        content: '正在分析图片 (YOLOv8 目标检测 → ResNet 分类 → DeepLabV3 分割)...',
      });
      processingRef.current = true;
      setProcessing(true);

      const reply = await agentChat({
        message: '(用户上传了图片)',
        session_id: sessionId.current,
        image_base64: base64,
      });

      setMessages((prev) =>
        prev.map((m) => (m.id === assistantId ? { ...m, content: reply } : m))
      );
    } catch (e: any) {
      Taro.showToast({ title: '图片选择失败', icon: 'none' });
    } finally {
      processingRef.current = false;
      setProcessing(false);
    }
  };

  const handleClear = () => {
    setMessages([
      {
        id: 'init',
        role: 'assistant',
        content: '您好！我是农智 AI 助手，您可以向我描述作物症状，或直接上传病害照片，我来帮您分析诊断。',
      },
    ]);
    sessionId.current = genSessionId();
  };

  // Keyboard enter handler
  const handleInputConfirm = () => {
    handleSend();
  };

  return (
    <View className='page-container' style='height:100vh;display:flex;flex-direction:column;'>
      {/* Header */}
      <View className='page-header'>
        <Text className='header-title'>AI 农业智能助手</Text>
        <View className='header-action' onClick={handleClear}>
          <Text>清空会话</Text>
        </View>
      </View>

      {/* Messages */}
      <ScrollView
        ref={scrollRef}
        className='chat-messages'
        scrollY
        enhanced
        enableFlex
        style='flex:1'
      >
        {messages.map((msg) => (
          <View key={msg.id} className={`chat-bubble ${msg.role}`}>
            {msg.role === 'assistant' && (
              <View className='assistant-avatar'>
                <Image src='../../assets/Frame_2_565.png' mode='aspectFit' />
              </View>
            )}
            <View>
              {msg.imagePath && (
                <Image src={msg.imagePath} className='bubble-image' mode='aspectFill' />
              )}
              <View className='bubble-text'>
                {msg.role === 'assistant' ? (
                  <RichText content={msg.content || (processing ? '思考中...' : '')} />
                ) : (
                  <Text>{msg.content || ''}</Text>
                )}
              </View>
            </View>
          </View>
        ))}
      </ScrollView>

      {/* Input Area */}
      <View className='chat-input-area'>
        <View className='input-btn upload-btn' onClick={handlePickImage}>
          <Image src='../../assets/Ellipse_2_414.png' mode='aspectFit' />
        </View>
        <View className='input-wrapper'>
          <Input
            className='chat-input'
            placeholder='输入问题或描述症状…'
            value={input}
            onInput={(e) => setInput(e.detail.value)}
            onConfirm={handleInputConfirm}
            disabled={processing}
            confirmType='send'
          />
        </View>
        <View className='input-btn send-btn' onClick={handleSend}>
          <Image src='../../assets/send.png' mode='aspectFit' />
        </View>
      </View>
    </View>
  );
}
