<template>
  <view class="page-container">
    <view class="page-content">
      <!-- 搜索 -->
      <view class="kb-search">
        <image src="/static/assets/search.png" mode="aspectFit" style="width:18px;height:18px"></image>
        <input class="kb-search-input" placeholder="搜索作物/病害名称" :value="search" @input="handleSearch" confirm-type="search" />
        <text style="font-size:13px;color:#27AE60;flex-shrink:0" @click="toFavorites">收藏</text>
        <text style="font-size:13px;color:#27AE60;flex-shrink:0" @click="toHistory">历史</text>
      </view>

      <!-- 分类 -->
      <scroll-view v-if="!search" class="kb-categories" scroll-x show-scrollbar="false">
        <view v-for="cat in categories" :key="cat.id"
          :class="'kb-cat-tab ' + (activeCat === cat.id ? 'active' : '')"
          @click="selectCategory(cat.id)">
          <text>{{ cat.name }}</text>
        </view>
      </scroll-view>

      <!-- 列表 -->
      <view class="kb-list">
        <view v-for="item in list" :key="item.id" class="kb-list-item" @click="goDetail(item.id)">
          <image :src="item.cover_image || '/static/assets/sprout.png'" mode="aspectFit" style="width:40px;height:40px;border-radius:8px"></image>
          <view style="flex:1">
            <text class="kb-item-name">
              {{ item.title }}
              <text v-if="item.is_pest === 1" style="font-size:10px;color:#e74c3c;background:#fde8e8;padding:1px 6px;border-radius:4px;margin-left:6px">虫害</text>
            </text>
            <text class="kb-item-desc">{{ (item.summary || '').slice(0, 40) }}...</text>
          </view>
          <image src="/static/assets/chevronright.png" mode="aspectFit" style="width:16px;height:16px"></image>
        </view>
      </view>

      <!-- 空状态 -->
      <view v-if="!loading && list.length === 0" class="empty-state" style="margin-top:60px">
        <image src="/static/assets/searchx.png" mode="aspectFit" style="width:64px;height:64px;margin-bottom:16px"></image>
        <text class="empty-title">未找到相关病虫害</text>
        <text class="empty-desc">试试换个关键词</text>
        <view class="primary-btn" @click="goAIChat">
          <text>咨询 AI 助手</text>
        </view>
      </view>

      <!-- 加载更多 -->
      <view v-if="list.length < total" class="load-more" @click="loadMore">
        <text style="color:#27AE60;font-size:14px">加载更多</text>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue';
import { API } from '../../utils/api';

const categories = ref([]);
const activeCat = ref(null);
const list = ref([]);
const search = ref('');
const total = ref(0);
const page = ref(1);
const loading = ref(false);

onMounted(() => {
  uni.request({ url: API.knowledgeCategories }).then((r) => {
    if (r.data?.success) {
      const cats = r.data.data;
      categories.value = cats;
      if (cats.length) activeCat.value = cats[0].id;
    }
  });
});

watch([activeCat, search], () => { fetchList(); });

function fetchList(pg = 1) {
  loading.value = true;
  uni.request({
    url: API.knowledgeList,
    data: {
      category_id: search.value ? undefined : activeCat.value,
      keyword: search.value || '',
      page: pg,
      page_size: 20,
    },
  }).then((r) => {
    if (r.data?.success) {
      list.value = pg === 1 ? r.data.data : [...list.value, ...r.data.data];
      total.value = r.data.total;
      page.value = pg;
    }
  }).finally(() => { loading.value = false; });
}

function handleSearch(e) {
  search.value = e.detail.value;
  page.value = 1;
}

function selectCategory(id) {
  activeCat.value = id;
  page.value = 1;
}

function goDetail(id) {
  const openid = uni.getStorageSync('openid') || '';
  uni.navigateTo({ url: `/pages/knowledge/detail?id=${id}&openid=${openid}` });
}

function loadMore() { fetchList(page.value + 1); }
function toFavorites() { uni.navigateTo({ url: '/pages/knowledge/favorites' }); }
function toHistory() { uni.navigateTo({ url: '/pages/knowledge/history' }); }
function goAIChat() { uni.switchTab({ url: '/pages/ai-chat/index' }); }
</script>
