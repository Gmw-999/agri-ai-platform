<template>
  <view class="page-container">
    <view class="page-header">
      <view style="display:flex;align-items:center;gap:8px" @click="uni.navigateBack()">
        <text style="font-size:18px">‹</text>
        <text class="header-title">农事日历</text>
      </view>
    </view>
    <view class="page-content">
      <!-- 月份切换 -->
      <view style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px">
        <text style="font-size:20px;font-weight:600;color:#333" @click="prevMonth">‹</text>
        <text style="font-size:18px;font-weight:600;color:#333">{{ year }}年{{ month }}月</text>
        <text style="font-size:20px;font-weight:600;color:#333" @click="nextMonth">&gt;</text>
      </view>

      <!-- 日历 -->
      <view class="section-card" style="padding:12px">
        <view style="display:flex;flex-wrap:wrap;text-align:center;margin-bottom:8px">
          <view v-for="(w, i) in weekHeaders" :key="i" style="width:14.28%;font-size:12px;color:#999;padding:4px 0">{{ w }}</view>
        </view>
        <view style="display:flex;flex-wrap:wrap;text-align:center">
          <view v-for="i in firstDayWeek" :key="'e' + i" style="width:14.28%;padding:6px 0"></view>
          <view v-for="(d, i) in days" :key="i"
            :style="{width:'14.28%',padding:'6px 0',alignItems:'center',borderRadius:'8px',background: getDayBg(d.date)}"
            @click="fetchDayReminders(d.date)">
            <text :style="{fontSize:14,textAlign:'center',color: getDayTextColor(d.date)}">{{ parseInt(d.date.split('-')[2], 10) }}</text>
            <view v-if="d.count > 0" style="width:6px;height:6px;border-radius:3px;background:#27AE60;margin:2px auto 0"></view>
          </view>
        </view>
      </view>

      <!-- 日提醒 -->
      <view v-if="selectedDate" style="margin-top:12px">
        <text style="font-size:14px;font-weight:500;color:#333;margin-bottom:8px">{{ selectedDate }} 的农事安排</text>
        <view v-if="dayReminders.length === 0" style="font-size:13px;color:#999;text-align:center;padding:20px">当天无农事安排</view>
        <view v-for="item in dayReminders" :key="item.id" class="section-card" style="margin-bottom:8px;padding:12px">
          <text style="font-size:14px;font-weight:500;color:#333">{{ item.title }}</text>
          <text v-if="item.content" style="font-size:12px;color:#666;margin-top:4px">{{ item.content }}</text>
          <text style="font-size:11px;color:#999;margin-top:4px">{{ (item.remind_time || '').slice(0, 5) }} · {{ item.remind_type }}</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { API } from '../../utils/api';

const now = new Date();
const year = ref(now.getFullYear());
const month = ref(now.getMonth() + 1);
const days = ref([]);
const dayReminders = ref([]);
const selectedDate = ref('');
const openid = uni.getStorageSync('openid') || 'anon';
const weekHeaders = ['日', '一', '二', '三', '四', '五', '六'];

const firstDayWeek = computed(() => new Date(year.value, month.value - 1, 1).getDay());

function getTodayStr() {
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
}

function getDayBg(dateStr) {
  if (dateStr === selectedDate.value) return '#27AE60';
  if (dateStr === getTodayStr()) return '#e8f8e8';
  return 'transparent';
}
function getDayTextColor(dateStr) {
  if (dateStr === selectedDate.value) return 'white;font-weight:600';
  if (dateStr === getTodayStr()) return '#27AE60;font-weight:600';
  return '#333';
}

function fetchCalendar(y, m) {
  uni.request({ url: API.reminderCalendar, data: { openid, year: y, month: m } }).then((r) => {
    if (r.data?.success) days.value = r.data.data;
  });
}

function fetchDayReminders(date) {
  uni.request({ url: API.reminderList, data: { openid, date_from: date, date_to: date, page_size: 50 } }).then((r) => {
    if (r.data?.success) {
      dayReminders.value = r.data.data;
      selectedDate.value = date;
    }
  });
}

function prevMonth() {
  if (month.value === 1) { year.value--; month.value = 12; }
  else month.value--;
}
function nextMonth() {
  if (month.value === 12) { year.value++; month.value = 1; }
  else month.value++;
}

onMounted(() => {
  fetchCalendar(year.value, month.value);
  const firstDay = `${year.value}-${String(month.value).padStart(2, '0')}-01`;
  fetchDayReminders(firstDay);
});
</script>
