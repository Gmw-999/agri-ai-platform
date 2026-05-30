<template>
  <view class="page-container">
    <view class="page-header">
      <view style="display:flex;align-items:center;gap:8px" @click="uni.navigateBack()">
        <text style="font-size:18px">‹</text>
        <text class="header-title">病虫害预警</text>
      </view>
    </view>
    <view class="page-content" style="padding-bottom:40px">
      <!-- 图例 -->
      <view style="display:flex;gap:12px;margin-bottom:16px;flex-wrap:wrap">
        <view v-for="(cfg, key) in LEVEL_CONFIG" :key="key" style="display:flex;align-items:center;gap:4px">
          <view :style="{width:'10px',height:'10px',borderRadius:'3px',background: cfg.bg}"></view>
          <text style="font-size:11px;color:#666">{{ cfg.label }}</text>
        </view>
      </view>

      <!-- 加载 -->
      <view v-if="loading" style="color:#999;text-align:center;padding:40px">加载中...</view>

      <!-- 空 -->
      <view v-else-if="list.length === 0" class="empty-state" style="margin-top:40px">
        <text class="empty-title">暂无预警信息</text>
        <text class="empty-desc">当前地区暂无病虫害预警</text>
      </view>

      <!-- 列表 -->
      <view v-for="item in list" :key="item.id" class="section-card" :style="'margin-bottom:12px;border-left:4px solid ' + getLevelConf(item.warning_level).bg">
        <view style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">
          <text style="font-size:15px;font-weight:600;color:#333">{{ item.pest_name }}</text>
          <view :style="{padding:'2px 10px',borderRadius:'4px',background: getLevelConf(item.warning_level).bg}">
            <text :style="{fontSize:11,fontWeight:600,color: getLevelConf(item.warning_level).color}">{{ getLevelConf(item.warning_level).label }}</text>
          </view>
        </view>
        <text style="font-size:12px;color:#666;margin-bottom:6px">{{ item.crop }} · {{ item.region }} · {{ item.start_date }}~{{ item.end_date }}</text>
        <text style="font-size:13px;color:#333;line-height:1.6;margin-bottom:8px">{{ item.description }}</text>
        <view v-if="item.prevention_measures" style="background:#f8f9fa;border-radius:8px;padding:10px">
          <text style="font-size:12px;font-weight:500;color:#27AE60;margin-bottom:4px">防治措施</text>
          <text style="font-size:13px;color:#333;line-height:1.7;white-space:pre-wrap">{{ item.prevention_measures }}</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { API } from '../../utils/api';

const LEVEL_CONFIG = {
  extreme: { label: '特急', color: '#fff', bg: '#e74c3c' },
  high: { label: '高危', color: '#fff', bg: '#f39c12' },
  medium: { label: '预警', color: '#333', bg: '#f1c40f' },
  low: { label: '注意', color: '#666', bg: '#ecf0f1' },
};

const list = ref([]);
const loading = ref(true);

function getLevelConf(level) { return LEVEL_CONFIG[level] || LEVEL_CONFIG.low; }

onMounted(() => {
  uni.request({ url: API.reminderPestWarnings, data: { region: '', limit: 50 } }).then((r) => {
    if (r.data?.success) list.value = r.data.data;
  }).finally(() => { loading.value = false; });
});
</script>
