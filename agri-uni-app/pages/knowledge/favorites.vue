<template>
  <view class="page-container">
    <view class="page-header">
      <view style="display:flex;align-items:center;gap:8px" @click="uni.navigateBack()">
        <text style="font-size:18px">‹</text>
        <text class="header-title">我的收藏</text>
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
        <text class="empty-title">暂无收藏</text>
        <text class="empty-desc">浏览知识库时收藏喜欢的条目</text>
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
  uni.request({ url: API.knowledgeFavorites, data: { openid, page: 1, page_size: 50 } }).then((r) => {
    if (r.data?.success) list.value = r.data.data;
  }).finally(() => { loading.value = false; });
});

function goDetail(id) {
  const openid = uni.getStorageSync('openid') || '';
  uni.navigateTo({ url: `/pages/knowledge/detail?id=${id}&openid=${openid}` });
}
</script>
