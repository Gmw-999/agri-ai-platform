<template>
  <view class="page-container">
    <view class="page-header">
      <view style="display:flex;align-items:center;justify-content:space-between">
        <view style="display:flex;align-items:center;gap:8px" @click="uni.navigateBack()">
          <text style="font-size:18px">‹</text>
          <text class="header-title">浏览历史</text>
        </view>
        <text v-if="list.length > 0" style="font-size:13px;color:#999" @click="clearHistory">清空</text>
      </view>
    </view>
    <view class="page-content">
      <view v-for="item in list" :key="item.id" class="kb-list-item" @click="goDetail(item.id)">
        <image src="/static/assets/sprout.png" mode="aspectFit" style="width:36px;height:36px"></image>
        <view style="flex:1">
          <text class="kb-item-name">{{ item.title }}</text>
          <text class="kb-item-desc">{{ (item.summary || '').slice(0, 30) }}...</text>
        </view>
        <image src="/static/assets/chevronright.png" mode="aspectFit" style="width:16px;height:16px"></image>
      </view>
      <view v-if="!loading && list.length === 0" class="empty-state" style="margin-top:60px">
        <text class="empty-title">暂无浏览历史</text>
        <text class="empty-desc">查看知识库详情会自动记录</text>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { API } from '../../utils/api';

const list = ref([]);
const loading = ref(true);

onMounted(() => {
  const openid = uni.getStorageSync('openid') || '';
  if (!openid) { loading.value = false; return; }
  uni.request({ url: API.knowledgeHistory, data: { openid, page: 1, page_size: 50 } }).then((r) => {
    if (r.data?.success) list.value = r.data.data;
  }).finally(() => { loading.value = false; });
});

function clearHistory() {
  const openid = uni.getStorageSync('openid') || '';
  uni.showModal({
    title: '确认清空',
    content: '确定要清空浏览历史吗？',
    success: (res) => {
      if (res.confirm) {
        uni.request({ url: API.knowledgeClearHistory, method: 'DELETE', data: { openid } }).then(() => {
          list.value = [];
          uni.showToast({ title: '已清空', icon: 'none' });
        });
      }
    },
  });
}

function goDetail(id) {
  const openid = uni.getStorageSync('openid') || '';
  uni.navigateTo({ url: `/pages/knowledge/detail?id=${id}&openid=${openid}` });
}
</script>
