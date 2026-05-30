<template>
  <view class="page-container">
    <view class="page-header">
      <view style="display:flex;align-items:center;justify-content:space-between">
        <view style="display:flex;align-items:center;gap:8px" @click="uni.navigateBack()">
          <text style="font-size:18px">‹</text>
          <text class="header-title">新建提醒</text>
        </view>
        <text style="font-size:14px;color:#27AE60;font-weight:500" @click="save">保存</text>
      </view>
    </view>
    <view class="page-content">
      <view class="form-group">
        <text class="form-label">提醒标题</text>
        <input class="form-input" placeholder="如：打药、施肥、浇水..." :value="title" @input="e => title = e.detail.value" />
      </view>
      <view class="form-group">
        <text class="form-label">日期</text>
        <picker mode="date" :value="date" @change="e => date = e.detail.value">
          <view class="form-input" style="display:flex;align-items:center;justify-content:space-between">
            <text>{{ date }}</text>
            <text style="color:#999">&gt;</text>
          </view>
        </picker>
      </view>
      <view class="form-group">
        <text class="form-label">时间</text>
        <picker mode="time" :value="time" @change="e => time = e.detail.value">
          <view class="form-input" style="display:flex;align-items:center;justify-content:space-between">
            <text>{{ time }}</text>
            <text style="color:#999">&gt;</text>
          </view>
        </picker>
      </view>
      <view class="form-group">
        <text class="form-label">提醒类型</text>
        <picker mode="selector" :range="typeLabels" :value="typeIndex" @change="e => typeIndex = Number(e.detail.value)">
          <view class="form-input" style="display:flex;align-items:center;justify-content:space-between">
            <text>{{ typeLabels[typeIndex] }}</text>
            <text style="color:#999">&gt;</text>
          </view>
        </picker>
      </view>
      <view class="form-group">
        <text class="form-label">关联作物（可选）</text>
        <input class="form-input" placeholder="如：水稻、小麦、番茄..." :value="cropType" @input="e => cropType = e.detail.value" />
      </view>
      <view class="form-group">
        <text class="form-label">备注说明</text>
        <textarea class="form-textarea" placeholder="输入提醒的具体内容..." :value="content" @input="e => content = e.detail.value" />
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue';
import { API } from '../../utils/api';

const TYPE_OPTIONS = [
  { value: 'custom', label: '自定义' },
  { value: 'weather', label: '天气农事' },
  { value: 'crop', label: '作物管理' },
  { value: 'pesticide', label: '植保防治' },
];

const title = ref('');
const content = ref('');
const date = ref(() => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`; });
const time = ref('08:00');
const typeIndex = ref(0);
const cropType = ref('');
const typeLabels = TYPE_OPTIONS.map(o => o.label);

// Initialize date
const now = new Date();
date.value = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;

function save() {
  if (!title.value.trim()) { uni.showToast({ title: '请输入提醒标题', icon: 'none' }); return; }
  const openid = uni.getStorageSync('openid') || 'anon';
  uni.request({
    url: API.reminderCreate,
    method: 'POST',
    data: {
      openid,
      title: title.value.trim(),
      content: content.value.trim(),
      remind_date: date.value,
      remind_time: time.value,
      remind_type: TYPE_OPTIONS[typeIndex.value].value,
      crop_type: cropType.value,
    },
  }).then((r) => {
    if (r.data?.success) {
      uni.showToast({ title: '创建成功', icon: 'none' });
      setTimeout(() => uni.navigateBack(), 1000);
    } else {
      uni.showToast({ title: '创建失败', icon: 'none' });
    }
  });
}
</script>
