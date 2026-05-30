import Taro from '@tarojs/taro';
import { API } from './config';

/**
 * Simple event bus (cross-platform: works in H5 and weapp)
 */
const _listeners: Record<string, Function[]> = {};

export function on(event: string, fn: Function) {
  (_listeners[event] = _listeners[event] || []).push(fn);
}

export function off(event: string, fn: Function) {
  const arr = _listeners[event];
  if (arr) _listeners[event] = arr.filter(f => f !== fn);
}

export function emit(event: string, data: any) {
  (_listeners[event] || []).forEach(fn => fn(data));
}

/**
 * Staged image data for cross-page navigation (avoids race condition with event bus)
 * Module-level variable that persists across page mount/unmount within same session.
 */
interface StagedImage {
  base64?: string;
  tempPath?: string;
  autoAnalyze?: boolean;
  autoPick?: boolean;
}

let _stagedImage: StagedImage | null = null;

export function stageImage(data: StagedImage) {
  _stagedImage = data;
}

export function consumeImage(): StagedImage | null {
  const data = _stagedImage;
  _stagedImage = null;
  return data;
}

export interface AgentChatParams {
  message: string;
  session_id?: string;
  openid?: string;
  image_base64?: string;
}

export interface AgentChatEvent {
  type: 'meta' | 'reply' | 'done' | 'error';
  content?: string;
  intent?: string;
  tools_used?: string[];
  session_id?: string;
  has_vision?: boolean;
}

/**
 * Check if running in H5 browser environment (vs mini-program)
 */
function isH5(): boolean {
  return process.env.TARO_ENV === 'h5';
}

/**
 * Parse SSE JSON lines response text into full reply string
 */
function parseSSEResponse(raw: string): string {
  let fullReply = '';
  const lines = raw.split('\n');
  for (const line of lines) {
    if (!line.trim()) continue;
    try {
      const event: AgentChatEvent = JSON.parse(line.trim());
      if (event.type === 'reply' && event.content) {
        fullReply += event.content;
      }
      if (event.type === 'done') break;
    } catch {
      // skip malformed lines
    }
  }
  return fullReply || '抱歉，未获取到回复';
}

/**
 * Agent chat - returns full text reply
 * Uses native fetch in H5 (handles streaming/chunked responses correctly),
 * falls back to Taro.request in mini-program
 */
export async function agentChat(params: AgentChatParams): Promise<string> {
  if (isH5()) {
    const resp = await fetch(API.agentChat, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    });
    if (!resp.ok) {
      throw new Error(`请求失败: ${resp.status}`);
    }
    const raw = await resp.text();
    return parseSSEResponse(raw);
  }

  // Mini-program: use Taro.request
  const res = await Taro.request({
    url: API.agentChat,
    method: 'POST',
    data: params,
    dataType: 'text',
    timeout: 120000,
  });

  if (res.statusCode !== 200) {
    throw new Error(`请求失败: ${res.statusCode}`);
  }

  return parseSSEResponse((res.data as string) || '');
}

/**
 * Simple chat (non-agent) - uses native fetch in H5
 */
export async function simpleChat(message: string): Promise<string> {
  if (isH5()) {
    const resp = await fetch(API.simpleChat, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ func: 'chat', message }),
    });
    if (!resp.ok) throw new Error(`请求失败: ${resp.status}`);
    const raw = await resp.text();
    let reply = '';
    for (const line of raw.split('\n')) {
      if (!line.trim()) continue;
      try {
        const parsed = JSON.parse(line.trim());
        if (parsed.reply) reply += parsed.reply;
      } catch { /* skip */ }
    }
    return reply || '抱歉，未获取到回复';
  }

  const res = await Taro.request({
    url: API.simpleChat,
    method: 'POST',
    data: { func: 'chat', message },
    dataType: 'text',
    timeout: 120000,
  });

  if (res.statusCode !== 200) {
    throw new Error(`请求失败: ${res.statusCode}`);
  }

  const raw = (res.data as string) || '';
  let reply = '';
  const lines = raw.split('\n');
  for (const line of lines) {
    if (!line.trim()) continue;
    try {
      const parsed = JSON.parse(line.trim());
      if (parsed.reply) reply += parsed.reply;
    } catch {
      // skip
    }
  }
  return reply || '抱歉，未获取到回复';
}

/**
 * Read image file as base64 (cross-platform: H5 + mini-program)
 *
 * For H5, prefer passing the native File object as `fileObj` to avoid blob URL fetch issues.
 */
export async function fileToBase64(
  filePath: string,
  fileObj?: File
): Promise<string> {
  // H5 with native File object (preferred, avoids blob URL fetch)
  if (isH5() && fileObj) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => {
        const result = reader.result as string;
        resolve(result.includes(',') ? result.split(',')[1] : result);
      };
      reader.onerror = reject;
      reader.readAsDataURL(fileObj);
    });
  }

  // H5 blob/http URL
  if (isH5() && (filePath.startsWith('blob:') || filePath.startsWith('http'))) {
    // Try fetch first
    try {
      const resp = await fetch(filePath);
      const blob = await resp.blob();
      return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onloadend = () => {
          const result = reader.result as string;
          const base64 = result.includes(',') ? result.split(',')[1] : result;
          resolve(base64);
        };
        reader.onerror = reject;
        reader.readAsDataURL(blob);
      });
    } catch {
      // Fallback: XMLHttpRequest for blob URLs that fetch can't handle
      return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open('GET', filePath, true);
        xhr.responseType = 'blob';
        xhr.onload = () => {
          const reader = new FileReader();
          reader.onloadend = () => {
            const result = reader.result as string;
            resolve(result.includes(',') ? result.split(',')[1] : result);
          };
          reader.onerror = reject;
          reader.readAsDataURL(xhr.response);
        };
        xhr.onerror = reject;
        xhr.send();
      });
    }
  }

  // Mini-program
  const fs = Taro.getFileSystemManager();
  return fs.readFileSync(filePath, 'base64');
}

/**
 * Pick image from camera or album (cross-platform: H5 + mini-program)
 */
export async function pickImage(source: 'camera' | 'album'): Promise<{
  base64: string;
  tempPath: string;
}> {
  const res = await Taro.chooseImage({
    count: 1,
    sourceType: [source],
    sizeType: ['compressed'],
  });

  if (!res.tempFilePaths.length) {
    throw new Error('未选择图片');
  }

  const tempPath = res.tempFilePaths[0];
  // H5: pass native File object to avoid blob URL fetch issues
  const fileObj = res.tempFiles?.[0]?.originalFileObj;
  const base64 = await fileToBase64(tempPath, fileObj);

  return { base64, tempPath };
}

/**
 * Call a single vision model (YOLOv8 / ResNet / DeepLabV3)
 */
export async function visionDetect(modelName: string, imageBase64: string): Promise<any> {
  if (isH5()) {
    const resp = await fetch(API.visionDetect, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model_name: modelName, image_base64: imageBase64 }),
    });
    return resp.json();
  }

  const res = await Taro.request({
    url: API.visionDetect,
    method: 'POST',
    header: { 'Content-Type': 'application/json' },
    data: { model_name: modelName, image_base64: imageBase64 },
    dataType: 'text',
    timeout: 120000,
  });

  if (res.statusCode !== 200) {
    throw new Error(`视觉模型调用失败: ${res.statusCode}`);
  }

  return typeof res.data === 'string' ? JSON.parse(res.data) : res.data;
}

/**
 * Crop-then-classify: DeepLab segmentation → crop disease region → ResNet classify
 * Removes background interference for better accuracy.
 */
export async function visionCropClassify(imageBase64: string): Promise<any> {
  if (isH5()) {
    const resp = await fetch(API.visionCropClassify, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model_name: 'crop_classify', image_base64: imageBase64 }),
    });
    return resp.json();
  }

  const res = await Taro.request({
    url: API.visionCropClassify,
    method: 'POST',
    header: { 'Content-Type': 'application/json' },
    data: { model_name: 'crop_classify', image_base64: imageBase64 },
    dataType: 'text',
    timeout: 120000,
  });

  if (res.statusCode !== 200) {
    throw new Error(`病斑裁剪分类调用失败: ${res.statusCode}`);
  }

  return typeof res.data === 'string' ? JSON.parse(res.data) : res.data;
}

/**
 * Run all three vision models and return combined results
 */
export async function runAllModels(imageBase64: string): Promise<{
  yolov8: any;
  resnet: any;
  deeplabv3: any;
}> {
  const [yolov8, resnet, deeplabv3] = await Promise.all([
    visionDetect('yolov8', imageBase64).catch(e => ({ success: false, error: e.message })),
    visionDetect('resnet', imageBase64).catch(e => ({ success: false, error: e.message })),
    visionDetect('deeplabv3', imageBase64).catch(e => ({ success: false, error: e.message })),
  ]);
  return { yolov8, resnet, deeplabv3 };
}

/**
 * Generate session ID
 */
export function genSessionId(): string {
  return `session_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

/**
 * Create a farming reminder from AI diagnosis results
 */
export async function reminderCreateFromAdvice(params: {
  openid: string;
  diagnosis: string;
  drugs_info?: string;
  image_base64?: string;
}): Promise<any> {
  if (isH5()) {
    const resp = await fetch(API.reminderCreateFromAdvice, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    });
    return resp.json();
  }

  const res = await Taro.request({
    url: API.reminderCreateFromAdvice,
    method: 'POST',
    header: { 'Content-Type': 'application/json' },
    data: params,
    dataType: 'text',
    timeout: 30000,
  });

  if (res.statusCode !== 200) {
    throw new Error(`创建提醒失败: ${res.statusCode}`);
  }

  return typeof res.data === 'string' ? JSON.parse(res.data) : res.data;
}

/**
 * Generate anonymous openid
 */
export function genOpenId(): string {
  const stored = Taro.getStorageSync('openid');
  if (stored) return stored;
  const id = `anon_${Date.now().toString(36)}`;
  Taro.setStorageSync('openid', id);
  return id;
}
