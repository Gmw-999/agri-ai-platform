<template>
  <view class="page-container">
    <view v-if="loading" class="page-content">
      <text style="color:#999">加载中...</text>
    </view>
    <view v-else-if="!data" class="page-content">
      <text>条目不存在</text>
    </view>
    <view v-else>
      <scroll-view scroll-y style="height:100vh">
        <view style="padding:12px 16px;padding-bottom:80px">
          <!-- 标题 -->
          <view style="margin-bottom:16px">
            <view style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
              <text class="section-title" style="font-size:20px">{{ data.title }}</text>
              <text v-if="data.is_pest === 1" style="font-size:11px;color:#e74c3c;background:#fde8e8;padding:2px 8px;border-radius:4px">虫害</text>
              <text v-else style="font-size:11px;color:#27AE60;background:#e8f8e8;padding:2px 8px;border-radius:4px">病害</text>
            </view>
            <text style="font-size:12px;color:#999">{{ data.category_name }} · {{ data.view_count }}次浏览</text>
          </view>

          <!-- 概述 -->
          <view class="section-card" style="margin-bottom:12px;background:#f0faf0">
            <text style="font-size:14px;color:#333;line-height:1.7">{{ data.summary }}</text>
          </view>

          <view v-if="data.symptoms" class="section-card" style="margin-bottom:12px">
            <text class="section-title">症状特征</text>
            <text style="font-size:14px;color:#333;line-height:1.8;white-space:pre-wrap">{{ data.symptoms }}</text>
          </view>
          <view v-if="data.cause" class="section-card" style="margin-bottom:12px">
            <text class="section-title">发病原因</text>
            <text style="font-size:14px;color:#333;line-height:1.8;white-space:pre-wrap">{{ data.cause }}</text>
          </view>
          <view v-if="data.prevention" class="section-card" style="margin-bottom:12px">
            <text class="section-title">预防措施</text>
            <text style="font-size:14px;color:#333;line-height:1.8;white-space:pre-wrap">{{ data.prevention }}</text>
          </view>
          <view v-if="data.treatment" class="section-card" style="margin-bottom:12px">
            <text class="section-title">防治方法</text>
            <text style="font-size:14px;color:#333;line-height:1.8;white-space:pre-wrap">{{ data.treatment }}</text>
          </view>

          <!-- 用药 -->
          <view v-if="data.drugs && data.drugs.length" class="section-card" style="margin-bottom:12px">
            <text class="section-title">推荐用药</text>
            <view v-for="(d, i) in data.drugs" :key="i" style="padding:10px 0;border-bottom:1px solid #f0f0f0">
              <text style="font-size:14px;font-weight:500;color:#333">{{ d.name }}</text>
              <text style="font-size:12px;color:#666;margin-top:4px">用法：{{ d.usage }}</text>
              <text v-if="d.purchase_url" style="font-size:12px;color:#27AE60;margin-top:4px" @click="copyLink(d.purchase_url)">复制购买链接</text>
            </view>
          </view>

          <!-- 标签 -->
          <view v-if="data.tags" style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px">
            <text v-for="(tag, i) in data.tags.split(',')" :key="i"
              style="font-size:11px;color:#666;background:#f5f5f5;padding:3px 10px;border-radius:12px">{{ tag.trim() }}</text>
          </view>
        </view>
      </scroll-view>

      <!-- 底部栏 -->
      <view style="position:fixed;bottom:0;left:0;right:0;background:white;border-top:1px solid #f0f0f0;padding:10px 16px;display:flex;gap:10px;padding-bottom:env(safe-area-inset-bottom,10px);z-index:10">
        <view :style="{flex:1,padding:'10px 0',borderRadius:8,textAlign:'center',background: favorited ? '#f0faf0' : '#f5f5f5'}" @click="toggleFav">
          <text :style="{fontSize:14,color: favorited ? '#27AE60' : '#666'}">{{ favorited ? '已收藏' : '收藏' }}</text>
        </view>
        <view style="flex:2;padding:10px 0;border-radius:8px;text-align:center;background:#27AE60" @click="askAI">
          <text style="font-size:14px;color:white;font-weight:500">咨询 AI 防治</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue';
import { onLoad } from '@dcloudio/uni-app';
import { API } from '../../utils/api';

const id = ref(0);
const openid = ref('');
const data = ref(null);
const favorited = ref(false);
const loading = ref(true);

onLoad((query) => {
  id.value = Number(query?.id || 0);
  openid.value = query?.openid || '';

  if (!id.value) { loading.value = false; return; }

  uni.request({ url: API.knowledgeDetail, data: { id: id.value, openid: openid.value } }).then((r) => {
    if (r.data?.success) data.value = r.data.data;
  }).finally(() => { loading.value = false; });

  if (openid.value) {
    uni.request({ url: API.knowledgeFavCheck, data: { openid: openid.value, knowledge_id: id.value } }).then((r) => {
      if (r.data?.success) favorited.value = r.data.data.favorited;
    });
  }
});

function toggleFav() {
  if (!openid.value) { uni.showToast({ title: '请先登录', icon: 'none' }); return; }
  uni.request({
    url: API.knowledgeFavorite, method: 'POST',
    data: { openid: openid.value, knowledge_id: id.value },
  }).then((r) => {
    if (r.data?.success) {
      favorited.value = r.data.data.favorited;
      uni.showToast({ title: r.data.data.message, icon: 'none' });
    }
  });
}

function copyLink(url) { uni.setClipboardData({ data: url }); }
function askAI() { uni.switchTab({ url: '/pages/ai-chat/index' }); }
</script>
