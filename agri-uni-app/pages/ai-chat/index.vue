<template>
  <view class="chat-page">
    <!-- 顶部导航栏 -->
    <view class="chat-header">
      <view class="header-back" @click="handleBack">
        <text class="back-icon">‹</text>
      </view>
      <view class="header-center">
        <image class="header-avatar" src="/static/assets/Frame_2_565.png" mode="aspectFit"></image>
        <view class="header-info">
          <text class="header-name">农业智能助理</text>
          <text class="header-status">在线 · 随时为您服务</text>
        </view>
      </view>
      <view class="header-action" @click="handleClear">
        <text class="action-text">清空</text>
      </view>
    </view>

    <!-- 消息列表 -->
    <scroll-view
      class="chat-body"
      scroll-y
      :scroll-into-view="scrollId"
      :scroll-with-animation="true"
      :enhanced="true"
      :show-scrollbar="false"
    >
      <!-- 欢迎区域 -->
      <view v-if="messages.length === 1 && messages[0].id === 'init'" class="welcome-area">
        <image class="welcome-icon" src="/static/assets/Frame_2_565.png" mode="aspectFit"></image>
        <text class="welcome-title">你好，我是农业 AI 助手</text>
        <text class="welcome-desc">可以帮你识别病虫害、推荐农药、查询天气</text>
        <view class="welcome-tips">
          <view class="tip-item">
            <view class="tip-icon">🐛</view>
            <text class="tip-text">拍照识别病虫害</text>
          </view>
          <view class="tip-item">
            <view class="tip-icon">💊</view>
            <text class="tip-text">推荐农药及购买</text>
          </view>
          <view class="tip-item">
            <view class="tip-icon">🌤️</view>
            <text class="tip-text">查询天气与农事建议</text>
          </view>
          <view class="tip-item">
            <view class="tip-icon">🌱</view>
            <text class="tip-text">作物种植知识问答</text>
          </view>
        </view>
      </view>

      <!-- 消息气泡 -->
      <view
        v-for="(msg, idx) in messages"
        :key="msg.id"
        :id="msg.id"
        :class="['msg-wrapper', msg.role === 'user' ? 'msg-right' : 'msg-left']"
      >
        <!-- 用户头像（放在气泡前面，row-reverse 反转后头像到最右边） -->
        <view v-if="msg.role === 'user'" class="msg-avatar user-avatar">
          <view class="avatar-placeholder">
            <text class="avatar-text">我</text>
          </view>
        </view>

        <!-- 助手头像 -->
        <view v-if="msg.role === 'assistant'" class="msg-avatar">
          <image src="/static/assets/Frame_2_565.png" mode="aspectFit"></image>
        </view>

        <!-- 气泡内容 -->
        <view :class="['msg-bubble', msg.role === 'user' ? 'bubble-user' : 'bubble-assistant']">
          <!-- 用户图片 -->
          <image
            v-if="msg.imagePath"
            :src="msg.imagePath"
            class="msg-image"
            mode="aspectFill"
            @click="handlePreviewImage(msg.imagePath)"
          ></image>
          <!-- 助手富文本（分段渲染：文本/图片 → 购买按钮穿插在正确位置） -->
          <view v-if="msg.role === 'assistant'" class="bubble-rich">
            <template v-for="(seg, si) in (msg.segments || [{ type: 'richtext', nodes: thinkingNodes }])" :key="si">
              <rich-text v-if="seg.type === 'richtext'" :nodes="seg.nodes"></rich-text>
              <view v-else-if="seg.type === 'purchase'" class="purchase-btn" @click="copyPurchaseUrl(seg.url)">
                <text style="color:#fff;font-size:13px;font-weight:600">🛒 点击购买</text>
              </view>
            </template>
          </view>
          <!-- 用户文字 -->
          <text v-else class="bubble-text">{{ msg.content || '' }}</text>
        </view>
      </view>

      <!-- 底部留白 -->
      <view class="chat-bottom-spacer"></view>
    </scroll-view>

    <!-- 底部输入区 -->
    <view class="chat-footer">
      <view class="footer-inner">
        <view class="footer-btn pic-btn" @click="handlePickImage">
          <text class="btn-icon">+</text>
        </view>
        <view class="footer-input-wrap">
          <input
            class="footer-input"
            placeholder="输入病虫害问题或描述症状..."
            :value="input"
            @input="onInput"
            @confirm="handleSend"
            :disabled="processing"
            confirm-type="send"
            placeholder-style="color:#b0b8c1;font-size:14px;"
          />
        </view>
        <view :class="['footer-btn send-btn', processing || !input.trim() ? 'btn-disabled' : '']" @click="handleSend">
          <text class="btn-icon send-icon">↑</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, nextTick } from 'vue';
import { onShow } from '@dcloudio/uni-app';
import { agentChat, pickImage, genSessionId } from '../../utils/api';

const thinkingNodes = [{ type: 'text', text: '思考中...' }];

// 将纯文本/图片/加粗等转为 rich-text nodes（不处理购买链接）
function makeRichTextNodes(text) {
  if (!text) return [{ type: 'text', text: '' }];
  let t = text.replace(/```[a-z]*\n?/g, '').replace(/```/g, '');
  const stripUrls = (s) => s.replace(/https?:\/\/\S+/g, '').replace(/购买地址[：:]\s*/g, '').replace(/链接[：:]\s*/g, '');
  const nodes = [];
  const pattern = /!\[([^\]]*)\]\(([^)]+)\)|\[([^\]]+)\]\(([^)]+)\)|\*\*([^*]+)\*\*/g;
  let lastIndex = 0, match;
  while ((match = pattern.exec(t)) !== null) {
    if (match.index > lastIndex) {
      const txt = stripUrls(t.slice(lastIndex, match.index));
      if (txt.trim()) nodes.push({ type: 'text', text: txt });
    }
    if (match[1] !== undefined) {
      nodes.push({
        type: 'node', name: 'img',
        attrs: { src: match[2], style: 'max-width:100%;margin:8px 0;border-radius:10px;' }
      });
    } else if (match[2] !== undefined) {
      nodes.push({
        type: 'node', name: 'a',
        attrs: { href: match[3], style: 'color:#4A90D9;text-decoration:underline;' },
        children: [{ type: 'text', text: match[2] }]
      });
    } else if (match[4] !== undefined) {
      nodes.push({
        type: 'node', name: 'span',
        attrs: { style: 'font-weight:bold;color:#1a1a1a;' },
        children: [{ type: 'text', text: match[4] }]
      });
    }
    lastIndex = match.index + match[0].length;
  }
  if (lastIndex < t.length) {
    const txt = stripUrls(t.slice(lastIndex));
    if (txt.trim()) nodes.push({ type: 'text', text: txt });
  }
  return nodes.length ? nodes : [{ type: 'text', text: stripUrls(t) }];
}

// 按 [点击购买] 分割文本，购买按钮穿插在正确位置（图片下方）
function parseSegments(text) {
  if (!text) return [{ type: 'richtext', nodes: [{ type: 'text', text: '' }] }];
  const parts = text.split(/(\[点击购买\]\([^)]+\))/g);
  const segments = [];
  for (const part of parts) {
    const m = part.match(/^\[点击购买\]\(([^)]+)\)$/);
    if (m) {
      segments.push({ type: 'purchase', url: m[1] });
    } else if (part.trim()) {
      segments.push({ type: 'richtext', nodes: makeRichTextNodes(part) });
    }
  }
  return segments.length ? segments : [{ type: 'richtext', nodes: [{ type: 'text', text: '' }] }];
}

const defaultWelcome = '你好！我是农业 AI 助手，可以帮你识别病虫害、推荐农药、查询天气。输入问题或直接上传作物照片开始吧~';
const messages = ref([
  {
    id: 'init', role: 'assistant',
    content: defaultWelcome,
    segments: [{ type: 'richtext', nodes: [{ type: 'text', text: defaultWelcome }] }]
  }
]);
const input = ref('');
const processing = ref(false);
const scrollId = ref('');
const sessionId = ref(genSessionId());

function addMessage(msg) {
  messages.value = [...messages.value, msg];
  scrollToBottom();
}

function scrollToBottom() {
  nextTick(() => {
    const msgs = messages.value;
    if (msgs.length) scrollId.value = msgs[msgs.length - 1].id;
  });
}

function onInput(e) { input.value = e.detail.value; }

function handleBack() {
  uni.navigateBack({ delta: 1 }).catch(() => {});
}

function handlePreviewImage(url) {
  uni.previewImage({ urls: [url], current: url });
}

async function handleSend() {
  const textVal = input.value.trim();
  if (!textVal || processing.value) return;
  input.value = '';
  addMessage({ id: 'u_' + Date.now(), role: 'user', content: textVal });
  const assistantId = 'a_' + Date.now();
  addMessage({ id: assistantId, role: 'assistant', content: '', segments: [{ type: 'richtext', nodes: thinkingNodes }] });
  processing.value = true;
  try {
    const reply = await agentChat({ message: textVal, session_id: sessionId.value });
    const segments = parseSegments(reply || '未收到回复');
    messages.value = messages.value.map(m => m.id === assistantId ? { ...m, content: reply || '未收到回复', segments } : m);
  } catch (err) {
    const errMsg = '网络异常：' + (err.message || '请稍后重试');
    messages.value = messages.value.map(m => m.id === assistantId ? { ...m, content: errMsg, segments: [{ type: 'richtext', nodes: [{ type: 'text', text: errMsg }] }] } : m);
  } finally {
    processing.value = false;
    scrollToBottom();
  }
}

async function handlePickImage() {
  try {
    const { base64, tempPath } = await pickImage('album');
    addMessage({ id: 'u_' + Date.now(), role: 'user', content: '(上传了图片)', imagePath: tempPath });
    const assistantId = 'a_' + Date.now();
    addMessage({ id: assistantId, role: 'assistant', content: '', segments: [{ type: 'richtext', nodes: thinkingNodes }] });
    processing.value = true;
    const reply = await agentChat({ message: '(用户上传了图片，请根据图片分析病虫害)', session_id: sessionId.value, image_base64: base64 });
    const segments = parseSegments(reply || '未收到回复');
    messages.value = messages.value.map(m => m.id === assistantId ? { ...m, content: reply || '未收到回复', segments } : m);
  } catch (err) {
    uni.showToast({ title: '图片上传失败', icon: 'none' });
  } finally {
    processing.value = false;
    scrollToBottom();
  }
}

function copyPurchaseUrl(url) {
  uni.setClipboardData({
    data: url,
    success: () => { uni.showToast({ title: '链接已复制，请在浏览器中打开', icon: 'none', duration: 2000 }); }
  });
}

function handleClear() {
  messages.value = [
    {
      id: 'init', role: 'assistant',
      content: defaultWelcome,
      segments: [{ type: 'richtext', nodes: [{ type: 'text', text: defaultWelcome }] }]
    }
  ];
  sessionId.value = genSessionId();
}

onShow(() => {
  const pending = uni.getStorageSync('pendingImage');
  if (pending) {
    uni.removeStorageSync('pendingImage');
    if (processing.value) return;
    addMessage({ id: 'u_' + Date.now(), role: 'user', content: '(上传了图片)', imagePath: pending.tempPath });
    const assistantId = 'a_' + Date.now();
    addMessage({ id: assistantId, role: 'assistant', content: '', segments: [{ type: 'richtext', nodes: thinkingNodes }] });
    processing.value = true;
    agentChat({ message: '(用户上传了图片)', session_id: sessionId.value, image_base64: pending.base64 })
      .then(reply => {
        const segments = parseSegments(reply || '未收到回复');
        messages.value = messages.value.map(m => m.id === assistantId ? { ...m, content: reply || '未收到回复', segments } : m);
      })
      .catch(err => {
        const errMsg = '异常：' + (err.message || '重试');
        messages.value = messages.value.map(m => m.id === assistantId ? { ...m, content: errMsg, segments: [{ type: 'richtext', nodes: [{ type: 'text', text: errMsg }] }] } : m);
      })
      .finally(() => { processing.value = false; scrollToBottom(); });
  }
});
</script>

<style>
/* ========== 全局重置 ========== */
page {
  background: #f0f2f5;
  height: 100vh;
  overflow: hidden;
  -webkit-font-smoothing: antialiased;
}

.chat-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #f0f2f5;
}

/* ========== 顶部导航 ========== */
.chat-header {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  padding-top: calc(12px + env(safe-area-inset-top));
  background: #ffffff;
  border-bottom: 1px solid #eef0f4;
  flex-shrink: 0;
  z-index: 10;
}

.header-back {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.back-icon {
  font-size: 20px;
  color: #333;
  font-weight: 300;
}

.header-center {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: 2px solid #e8f4fd;
  flex-shrink: 0;
}

.header-info {
  display: flex;
  flex-direction: column;
}

.header-name {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a1a;
  line-height: 1.3;
}

.header-status {
  font-size: 11px;
  color: #52c41a;
  line-height: 1.3;
}

.header-action {
  padding: 6px 14px;
  flex-shrink: 0;
}

.action-text {
  font-size: 14px;
  color: #8c9198;
}

/* ========== 聊天主体 ========== */
.chat-body {
  flex: 1;
  padding: 16px 14px;
  overflow-y: auto;
}

/* ========== 欢迎区域 ========== */
.welcome-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px 20px 30px;
}

.welcome-icon {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  margin-bottom: 16px;
  box-shadow: 0 4px 16px rgba(45, 140, 242, 0.15);
}

.welcome-title {
  font-size: 18px;
  font-weight: 600;
  color: #1a1a1a;
  margin-bottom: 6px;
}

.welcome-desc {
  font-size: 13px;
  color: #8c9198;
  margin-bottom: 24px;
}

.welcome-tips {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: center;
  width: 100%;
}

.tip-item {
  display: flex;
  align-items: center;
  gap: 6px;
  background: #ffffff;
  padding: 10px 16px;
  border-radius: 20px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}

.tip-icon {
  font-size: 16px;
}

.tip-text {
  font-size: 13px;
  color: #555;
}

/* ========== 消息行 ========== */
.msg-wrapper {
  display: flex;
  align-items: flex-start;
  margin-bottom: 18px;
  gap: 10px;
}

.msg-left {
  flex-direction: row;
}

.msg-right {
  flex-direction: row-reverse;
}

/* ========== 头像 ========== */
.msg-avatar {
  flex-shrink: 0;
  width: 38px;
  height: 38px;
  margin-top: 2px;
}

.msg-avatar image {
  width: 38px;
  height: 38px;
  border-radius: 50%;
}

.user-avatar {
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar-placeholder {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: linear-gradient(135deg, #2d8cf2, #4da3f5);
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar-text {
  color: #fff;
  font-size: 14px;
  font-weight: 600;
}

/* ========== 气泡 ========== */
.msg-bubble {
  max-width: 72%;
  padding: 12px 16px;
  border-radius: 18px;
  position: relative;
  word-break: break-word;
}

.bubble-assistant {
  background: #ffffff;
  border-top-left-radius: 6px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}

.bubble-user {
  background: linear-gradient(135deg, #2d8cf2, #3d9af5);
  border-top-right-radius: 6px;
  box-shadow: 0 2px 8px rgba(45, 140, 242, 0.25);
}

.bubble-rich {
  font-size: 15px;
  line-height: 1.7;
  color: #333;
}

.purchase-btn {
  display: inline-block;
  padding: 7px 20px;
  background: linear-gradient(135deg, #ff6b35, #f7931e);
  border-radius: 20px;
  box-shadow: 0 2px 8px rgba(255, 107, 53, 0.3);
}

.bubble-text {
  font-size: 15px;
  line-height: 1.7;
  color: #ffffff;
}

/* ========== 消息图片 ========== */
.msg-image {
  max-width: 180px;
  max-height: 180px;
  border-radius: 12px;
  margin-bottom: 8px;
}

/* ========== 底部留白 ========== */
.chat-bottom-spacer {
  height: 8px;
}

/* ========== 底部输入区 ========== */
.chat-footer {
  flex-shrink: 0;
  background: #ffffff;
  padding: 10px 12px;
  padding-bottom: calc(10px + env(safe-area-inset-bottom));
  border-top: 1px solid #eef0f4;
}

.footer-inner {
  display: flex;
  align-items: flex-end;
  gap: 10px;
}

.footer-btn {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.2s;
}

.pic-btn {
  background: #f5f6fa;
  border: 1px solid #e8eaef;
}

.pic-btn .btn-icon {
  font-size: 24px;
  color: #666;
  font-weight: 300;
  line-height: 1;
}

.send-btn {
  background: linear-gradient(135deg, #2d8cf2, #3d9af5);
  box-shadow: 0 2px 8px rgba(45, 140, 242, 0.3);
}

.send-btn .send-icon {
  font-size: 18px;
  color: #fff;
  font-weight: 600;
}

.btn-disabled {
  opacity: 0.4;
  box-shadow: none;
}

.footer-input-wrap {
  flex: 1;
  background: #f5f6fa;
  border-radius: 22px;
  padding: 2px 18px;
  border: 1px solid #eef0f4;
}

.footer-input {
  height: 40px;
  font-size: 15px;
  color: #333;
  width: 100%;
}
</style>
