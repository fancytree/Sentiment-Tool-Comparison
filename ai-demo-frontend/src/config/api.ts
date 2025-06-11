// API 配置
const getApiBaseUrl = () => {
  // 检查是否在开发环境
  const isDevelopment = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
  
  if (isDevelopment) {
    // 开发环境：使用本地地址
    return 'http://localhost:8001';
  }
  
  // 生产环境：使用相对路径，让浏览器自动使用当前域名
  return '';
};

export const API_BASE_URL = getApiBaseUrl();

// API 端点
export const API_ENDPOINTS = {
  // LLM 情感分析
  LLM_SENTIMENT: `${API_BASE_URL}/api/llm-sentiment/`,
  LLM_SENTIMENT_UPLOAD: `${API_BASE_URL}/api/llm-sentiment/upload`,
  LLM_SENTIMENT_CHAT: `${API_BASE_URL}/api/llm-sentiment/chat`,
  LLM_SENTIMENT_DOWNLOAD: (filename: string) => `${API_BASE_URL}/api/llm-sentiment/download/${filename}`,
  
  // Transformer 情感分析
  TRANSFORMER_SENTIMENT: `${API_BASE_URL}/api/transformer-sentiment/`,
  TRANSFORMER_SENTIMENT_UPLOAD: `${API_BASE_URL}/api/transformer-sentiment/upload`,
  TRANSFORMER_SENTIMENT_DOWNLOAD: (filename: string) => `${API_BASE_URL}/api/transformer-sentiment/download/${filename}`,
  
  // 通用分析
  GENERAL_ANALYZE: `${API_BASE_URL}/api/general/analyze`,
  GENERAL_UPLOAD: `${API_BASE_URL}/api/general/upload`,
  GENERAL_DOWNLOAD: (filename: string) => `${API_BASE_URL}/api/general/download/${filename}`,
};

// 通用的 fetch 配置
export const DEFAULT_FETCH_OPTIONS = {
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  },
}; 