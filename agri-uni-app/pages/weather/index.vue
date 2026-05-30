<template>
  <view class="page-container">
    <view class="page-content">
      <!-- 地点 -->
      <view v-if="showInput" style="display:flex;gap:8px;align-items:center;margin-bottom:12px">
        <input style="flex:1;padding:8px 12px;background:white;border-radius:8px;font-size:14px;border:1px solid #e8e8e8"
          placeholder="输入地区名称" :value="locInput" @input="e => locInput = e.detail.value" @confirm="handleLocChange" />
        <view style="padding:8px 16px;background:#2e8b57;color:white;border-radius:8px;font-size:14px" @click="handleLocChange">
          <text>确定</text>
        </view>
      </view>
      <view v-else class="location-bar" @click="showInput = true">
        <image src="/static/assets/mappin.png" mode="aspectFit"></image>
        <text>{{ weather?.city || location }}</text>
        <image src="/static/assets/chevrondown.png" mode="aspectFit"></image>
      </view>

      <!-- 当前天气 -->
      <view class="current-weather">
        <view class="temp-display">
          <view>
            <text class="temp-value">{{ now ? now.temp + '°C' : '--°C' }}</text>
            <text class="temp-desc">{{ now?.text || '加载中' }}</text>
          </view>
          <image :src="now?.text ? getIcon(now.text) : '/static/assets/sun.png'" mode="aspectFit" style="width:64px;height:64px"></image>
        </view>
        <view class="weather-details">
          <view class="wd-item">
            <image src="/static/assets/wind.png" mode="aspectFit"></image>
            <text>{{ now ? now.windSpeed + 'km/h' : '--' }}</text>
          </view>
          <view class="wd-item">
            <image src="/static/assets/droplets.png" mode="aspectFit"></image>
            <text>{{ now ? now.humidity + '%' : '--%' }}</text>
          </view>
        </view>
        <view class="farm-status">
          <image src="/static/assets/checkcircle.png" mode="aspectFit" style="width:18px;height:18px"></image>
          <text>{{ now ? '体感 ' + (now.feelsLike || now.temp) + '°C · ' + (weather?.update_time || '') : '查询中...' }}</text>
        </view>
      </view>

      <!-- 预警 -->
      <view v-if="warning" class="section-card" :style="'border-left:4px solid ' + warning.color + ';margin-bottom:12px'">
        <view class="section-title-row">
          <image src="/static/assets/trianglealert.png" mode="aspectFit" style="width:18px;height:18px"></image>
          <text class="section-title">{{ warning.title }}</text>
        </view>
        <text style="font-size:12px;color:#666;margin-top:4px">{{ warning.text.slice(0, 100) }}...</text>
      </view>

      <!-- 预报 -->
      <view class="section-card">
        <text class="section-title">未来7天预报</text>
        <view class="forecast-grid">
          <view v-for="(d, i) in dailyList" :key="i" class="forecast-day">
            <text class="fd-label">{{ dayLabels[i] || (i + 1 + '') }}</text>
            <image :src="getIcon(d?.textDay)" mode="aspectFit" style="width:24px;height:24px"></image>
            <text class="fd-temp">{{ d ? d.tempMax + '°' : '--°' }}</text>
            <text v-if="d" style="font-size:10px;color:#999;margin-top:2px">{{ getDayDesc(d.textDay) }}</text>
          </view>
        </view>
      </view>

      <!-- 农事建议 -->
      <view v-if="loading" style="text-align:center;padding:24px">
        <text style="color:#999">正在获取农事建议...</text>
      </view>
      <view v-if="advice" class="section-card">
        <view class="advice-header">
          <image src="/static/assets/leaf0.png" mode="aspectFit"></image>
          <text>农事操作建议</text>
        </view>
        <view>
          <view v-for="(point, i) in advicePoints" :key="i" class="advice-item">
            <view class="advice-bullet"></view>
            <text>{{ point }}</text>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { agentChat } from '../../utils/api';
import { API } from '../../utils/api';

const loading = ref(false);
const advice = ref('');
const weather = ref(null);
const location = ref('湖南省长沙市');
const showInput = ref(false);
const locInput = ref(location.value);
const dayLabels = ['今', '明', '三', '四', '五', '六', '日'];

const now = computed(() => weather.value?.now || null);
const dailyList = computed(() => {
  const d = weather.value?.daily || [];
  return d.length > 0 ? d : Array(7).fill(null);
});
const advicePoints = computed(() => {
  if (!advice.value) return [];
  return advice.value.split(/\d\./).filter(Boolean);
});

function getIcon(text) {
  if (!text) return '/static/assets/sun.png';
  if (text.includes('晴')) return '/static/assets/sun.png';
  if (text.includes('多云') || text.includes('阴')) return '/static/assets/cloudsun.png';
  if (text.includes('雨') || text.includes('雷') || text.includes('阵')) return '/static/assets/cloudrain.png';
  return '/static/assets/sun.png';
}
function getDayDesc(text) {
  const m = { '晴': '晴', '多云': '多云', '阴': '阴', '小雨': '小雨', '中雨': '中雨', '大雨': '大雨', '暴雨': '暴雨', '雷阵雨': '雷雨', '阵雨': '阵雨' };
  for (const [k, v] of Object.entries(m)) { if (text.includes(k)) return v; }
  return text.slice(0, 2);
}

const warning = computed(() => {
  if (!weather.value?.warning?.length) return null;
  const w = weather.value.warning[0];
  const isRed = w.level === '红色' || w.severity === 'Extreme';
  const isOrange = w.level === '橙色' || w.severity === 'Severe';
  const isYellow = w.level === '黄色' || w.severity === 'Moderate';
  return {
    title: w.title || '',
    text: w.text || '',
    color: isRed ? '#e74c3c' : isOrange ? '#f39c12' : isYellow ? '#f1c40f' : '#3498db',
  };
});

async function fetchWeatherData(loc) {
  try {
    const res = await uni.request({ url: `${API.weather}?region=${encodeURIComponent(loc)}`, method: 'GET', timeout: 60000 });
    if (res.data?.success) weather.value = res.data.data;
  } catch (e) { console.warn('[天气] 请求异常:', e); }
}

async function fetchAdvice(loc) {
  loading.value = true;
  advice.value = '';
  try {
    const reply = await agentChat({ message: `${loc}今天天气怎么样，适合打药吗`, session_id: `weather_${Date.now()}` });
    advice.value = reply;
  } catch { uni.showToast({ title: '获取农事建议失败', icon: 'none' }); }
  finally { loading.value = false; }
}

async function fetchAll(loc) {
  await Promise.all([fetchWeatherData(loc), fetchAdvice(loc)]);
}

function handleLocChange() {
  const loc = locInput.value.trim() || '湖南省长沙市';
  location.value = loc;
  showInput.value = false;
  fetchAll(loc);
}

onMounted(() => { fetchAll(location.value); });
</script>
