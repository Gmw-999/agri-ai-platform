// Taro 小程序/App API 配置
// 开发时用 127.0.0.1，手机测试时改成电脑局域网 IP（如 192.168.x.x）
const API_HOST = '192.168.43.228';
const API_PORT = '8000';
const API_BASE = `http://${API_HOST}:${API_PORT}/api`;

export const API = {
  agentChat: `${API_BASE}/agent/chat`,
  simpleChat: `${API_BASE}/run`,
  visionDetect: `${API_BASE}/vision/detect`,
  visionCropClassify: `${API_BASE}/vision/crop_classify`,
  weather: `${API_BASE}/weather`,

  // 知识库
  knowledgeCategories: `${API_BASE}/knowledge/categories`,
  knowledgeList: `${API_BASE}/knowledge/list`,
  knowledgeDetail: `${API_BASE}/knowledge/detail`,
  knowledgeFavorite: `${API_BASE}/knowledge/favorite`,
  knowledgeFavorites: `${API_BASE}/knowledge/favorites`,
  knowledgeFavIds: `${API_BASE}/knowledge/favorites/ids`,
  knowledgeFavCheck: `${API_BASE}/knowledge/favorite/check`,
  knowledgeHistory: `${API_BASE}/knowledge/history`,
  knowledgeClearHistory: `${API_BASE}/knowledge/history`,

  // 农事提醒
  reminderList: `${API_BASE}/reminder/list`,
  reminderCreate: `${API_BASE}/reminder/create`,
  reminderUpdate: `${API_BASE}/reminder/update`,
  reminderDelete: `${API_BASE}/reminder/delete`,
  reminderCalendar: `${API_BASE}/reminder/calendar`,
  reminderPestWarnings: `${API_BASE}/reminder/pest-warnings`,
  reminderWeatherAdvice: `${API_BASE}/reminder/weather-advice`,
  reminderCreateFromAdvice: `${API_BASE}/reminder/create-from-advice`,
};
