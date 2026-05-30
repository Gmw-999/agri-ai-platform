const API_BASE = "http://localhost:8000/api";

export const API = {
  agentChat: `${API_BASE}/agent/chat`,
  simpleChat: `${API_BASE}/run`,
  visionDetect: `${API_BASE}/vision/detect`,
};

export default API;
