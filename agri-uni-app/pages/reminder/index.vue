<template>
  <view class="page-container">
    <view class="page-content" style="padding-bottom:80px">
      <!-- 天气建议 -->
      <view v-if="weatherAdvice" class="section-card" style="margin-bottom:12px;background:#f0faf0;border-left:3px solid #27AE60">
        <view class="section-title-row">
          <image src="/static/assets/sun.png" mode="aspectFit" style="width:20px;height:20px"></image>
          <text class="section-title">今日农事建议</text>
        </view>
        <text style="font-size:13px;color:#333;line-height:1.7;margin-top:6px">{{ weatherAdvice.slice(0, 200) }}</text>
      </view>

      <!-- 快捷操作 -->
      <view style="display:flex;gap:10px;margin-bottom:16px">
        <view class="quick-action-btn" @click="toAdd">
          <image src="/static/assets/checkcircle.png" mode="aspectFit" style="width:24px;height:24px;margin-bottom:4px"></image>
          <text style="font-size:12px;color:#333">新建提醒</text>
        </view>
        <view class="quick-action-btn" @click="toCalendar">
          <image src="/static/assets/sprout.png" mode="aspectFit" style="width:24px;height:24px;margin-bottom:4px"></image>
          <text style="font-size:12px;color:#333">农事日历</text>
        </view>
        <view class="quick-action-btn" @click="toPestWarning">
          <image src="/static/assets/leaf0.png" mode="aspectFit" style="width:24px;height:24px;margin-bottom:4px"></image>
          <text style="font-size:12px;color:#333">病虫预警</text>
        </view>
      </view>

      <!-- 提醒列表 -->
      <view style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px">
        <text class="section-title" style="margin-bottom:0">待办提醒</text>
        <text v-if="reminders.length > 0" style="font-size:12px;color:#999">{{ reminders.length }}条待办</text>
      </view>

      <view v-if="reminders.length === 0" class="empty-state" style="margin-top:20px">
        <text class="empty-title">暂无待办提醒</text>
        <text class="empty-desc">点击上方新建提醒</text>
      </view>

      <view v-for="item in reminders" :key="item.id" class="section-card" style="margin-bottom:8px;padding:12px">
        <view style="display:flex;align-items:flex-start;gap:10px">
          <view :style="{width:'4px',height:'36px',borderRadius:'2px',background: TYPE_COLORS[item.remind_type] || '#999',flexShrink:0}"></view>
          <view style="flex:1">
            <view style="display:flex;align-items:center;gap:6px;margin-bottom:4px">
              <text style="font-size:12px;color:#666;background:#f5f5f5;padding:1px 8px;border-radius:4px">{{ TYPE_LABELS[item.remind_type] || '自定义' }}</text>
              <text style="font-size:12px;color:#999">{{ item.remind_date }} {{ String(item.remind_time || '').slice(0, 5) }}</text>
            </view>
            <text style="font-size:14px;font-weight:500;color:#333">{{ item.title }}</text>
            <text v-if="item.content" style="font-size:12px;color:#666;margin-top:4px">{{ item.content.slice(0, 50) }}</text>
          </view>
          <view style="display:flex;flex-direction:column;gap:4px">
            <text style="font-size:18px;color:#27AE60" @click="completeReminder(item.id)">✓</text>
            <text style="font-size:14px;color:#ccc" @click="deleteReminder(item.id)">✕</text>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, onMounted, onShow } from 'vue';
import { API } from '../../utils/api';

const TYPE_LABELS = { weather: '天气', crop: '农事', pesticide: '植保', custom: '自定义' };
const TYPE_COLORS = { weather: '#3498db', crop: '#27AE60', pesticide: '#e74c3c', custom: '#f39c12' };

const reminders = ref([]);
const weatherAdvice = ref('');
const loading = ref(true);
const openid = uni.getStorageSync('openid') || 'anon';

function fetchReminders() {
  if (!openid) return;
  uni.request({ url: API.reminderList, data: { openid, status: 'pending', page_size: 50 } }).then((r) => {
    if (r.data?.success) reminders.value = r.data.data;
  });
}

function fetchWeatherAdvice() {
  uni.request({ url: API.reminderWeatherAdvice, data: { region: '长沙' } })
    .then((r) => { if (r.data?.success) weatherAdvice.value = r.data.data.advice || ''; })
    .catch(() => {})
    .finally(() => { loading.value = false; });
}

onMounted(() => {
  fetchReminders();
  fetchWeatherAdvice();
});

onShow(() => {
  fetchReminders();
});

function completeReminder(id) {
  uni.request({ url: API.reminderUpdate, method: 'PUT', data: { id, status: 'completed' } }).then(() => {
    reminders.value = reminders.value.filter(r => r.id !== id);
    uni.showToast({ title: '已完成', icon: 'none' });
  });
}

function deleteReminder(id) {
  uni.showModal({
    title: '删除提醒', content: '确定删除？',
    success: (res) => {
      if (res.confirm) {
        uni.request({ url: API.reminderDelete, method: 'DELETE', data: { id } }).then(() => {
          reminders.value = reminders.value.filter(r => r.id !== id);
          uni.showToast({ title: '已删除', icon: 'none' });
        });
      }
    },
  });
}

function toAdd() { uni.navigateTo({ url: '/pages/reminder/add' }); }
function toCalendar() { uni.navigateTo({ url: '/pages/reminder/calendar' }); }
function toPestWarning() { uni.navigateTo({ url: '/pages/reminder/pest-warning' }); }
</script>
