// 农业 AI 助手 - 通用 API 工具 (uni-app)

const API_HOST = '192.168.43.228';
const API_PORT = '8000';
const API_BASE = 'http://' + API_HOST + ':' + API_PORT + '/api';

export const API = {
  agentChat: API_BASE + '/agent/chat',
  simpleChat: API_BASE + '/run',
  visionDetect: API_BASE + '/vision/detect',
  visionCropClassify: API_BASE + '/vision/crop_classify',
  weather: API_BASE + '/weather',
  knowledgeCategories: API_BASE + '/knowledge/categories',
  knowledgeList: API_BASE + '/knowledge/list',
  knowledgeDetail: API_BASE + '/knowledge/detail',
  knowledgeFavorite: API_BASE + '/knowledge/favorite',
  knowledgeFavorites: API_BASE + '/knowledge/favorites',
  knowledgeFavIds: API_BASE + '/knowledge/favorites/ids',
  knowledgeFavCheck: API_BASE + '/knowledge/favorite/check',
  knowledgeHistory: API_BASE + '/knowledge/history',
  knowledgeClearHistory: API_BASE + '/knowledge/history',
  reminderList: API_BASE + '/reminder/list',
  reminderCreate: API_BASE + '/reminder/create',
  reminderUpdate: API_BASE + '/reminder/update',
  reminderDelete: API_BASE + '/reminder/delete',
  reminderCalendar: API_BASE + '/reminder/calendar',
  reminderPestWarnings: API_BASE + '/reminder/pest-warnings',
  reminderWeatherAdvice: API_BASE + '/reminder/weather-advice',
  reminderCreateFromAdvice: API_BASE + '/reminder/create-from-advice',
};

// 通用 request 封装
function request(options) {
  return new Promise((resolve, reject) => {
    uni.request({
      ...options,
      success: (res) => resolve(res),
      fail: (err) => reject(err),
    });
  });
}

// Event bus
const _listeners = {};

export function on(event, fn) {
  (_listeners[event] = _listeners[event] || []).push(fn);
}

export function off(event, fn) {
  const arr = _listeners[event];
  if (arr) _listeners[event] = arr.filter(f => f !== fn);
}

export function emit(event, data) {
  (_listeners[event] || []).forEach(fn => fn(data));
}

// Staged image
let _stagedImage = null;

export function stageImage(data) {
  _stagedImage = data;
}

export function consumeImage() {
  const data = _stagedImage;
  _stagedImage = null;
  return data;
}

// 解析 Agent NDJSON 响应（meta / reply / done）
function parseSSEResponse(raw) {
  let fullReply = '';
  // 确保是字符串
  const text = typeof raw === 'string' ? raw : JSON.stringify(raw);
  const lines = text.split('\n');
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    try {
      const event = JSON.parse(trimmed);
      if (event.type === 'reply' && event.content) {
        fullReply += event.content;
      }
      if (event.type === 'done') break;
    } catch (e) {
      // 跳过非 JSON 行
    }
  }
  return fullReply || '抱歉，未获取到回复，请重试';
}

// Agent 聊天
export async function agentChat(params) {
  try {
    const res = await uni.request({
      url: API.agentChat,
      method: 'POST',
      data: params,
      dataType: 'text',
      timeout: 120000,
    });
    if (res.statusCode !== 200) {
      throw new Error('请求失败: ' + res.statusCode);
    }
    return parseSSEResponse(res.data || '');
  } catch (e) {
    // 如果是 uni.request 的 fail 回调抛出的对象
    if (e && e.errMsg) {
      throw new Error(e.errMsg);
    }
    throw e;
  }
}

// 简单聊天 (旧 API)
export async function simpleChat(message) {
  const res = await uni.request({
    url: API.simpleChat,
    method: 'POST',
    data: { func: 'chat', message: message },
    dataType: 'text',
    timeout: 120000,
  });
  if (res.statusCode !== 200) throw new Error('请求失败: ' + res.statusCode);
  const raw = res.data || '';
  let reply = '';
  const lines = (typeof raw === 'string' ? raw : JSON.stringify(raw)).split('\n');
  for (const line of lines) {
    if (!line.trim()) continue;
    try {
      const parsed = JSON.parse(line.trim());
      if (parsed.reply) reply += parsed.reply;
    } catch (e) {}
  }
  return reply || '抱歉，未获取到回复';
}

// File to base64
export function fileToBase64(filePath) {
  return new Promise((resolve, reject) => {
    uni.getFileSystemManager().readFile({
      filePath,
      encoding: 'base64',
      success: (res) => resolve(res.data),
      fail: (err) => reject(err),
    });
  });
}

// Pick image
export async function pickImage(source) {
  const res = await uni.chooseImage({
    count: 1,
    sourceType: [source],
    sizeType: ['compressed'],
  });
  if (!res.tempFilePaths.length) {
    throw new Error('未选择图片');
  }
  const tempPath = res.tempFilePaths[0];
  const base64 = await fileToBase64(tempPath);
  return { base64, tempPath };
}

// Vision detect
export async function visionDetect(modelName, imageBase64) {
  const res = await uni.request({
    url: API.visionDetect,
    method: 'POST',
    data: { model_name: modelName, image_base64: imageBase64 },
    dataType: 'text',
    timeout: 120000,
  });
  if (res.statusCode !== 200) throw new Error('请求失败: ' + res.statusCode);
  return typeof res.data === 'string' ? JSON.parse(res.data) : res.data;
}

// Vision crop classify
export async function visionCropClassify(imageBase64) {
  const res = await uni.request({
    url: API.visionCropClassify,
    method: 'POST',
    data: { model_name: 'crop_classify', image_base64: imageBase64 },
    dataType: 'text',
    timeout: 120000,
  });
  if (res.statusCode !== 200) throw new Error('请求失败: ' + res.statusCode);
  return typeof res.data === 'string' ? JSON.parse(res.data) : res.data;
}

// Run all models
export async function runAllModels(imageBase64) {
  const [yolov8, resnet, deeplabv3] = await Promise.all([
    visionDetect('yolov8', imageBase64).catch(e => ({ success: false, error: e.message })),
    visionDetect('resnet', imageBase64).catch(e => ({ success: false, error: e.message })),
    visionDetect('deeplabv3', imageBase64).catch(e => ({ success: false, error: e.message })),
  ]);
  return { yolov8, resnet, deeplabv3 };
}

// Session ID
export function genSessionId() {
  return 'session_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8);
}

// Reminder from advice
export async function reminderCreateFromAdvice(params) {
  const res = await uni.request({
    url: API.reminderCreateFromAdvice,
    method: 'POST',
    data: params,
    dataType: 'text',
    timeout: 30000,
  });
  if (res.statusCode !== 200) throw new Error('请求失败: ' + res.statusCode);
  return typeof res.data === 'string' ? JSON.parse(res.data) : res.data;
}

// OpenID
export function genOpenId() {
  const stored = uni.getStorageSync('openid');
  if (stored) return stored;
  const id = 'anon_' + Date.now().toString(36);
  uni.setStorageSync('openid', id);
  return id;
}
