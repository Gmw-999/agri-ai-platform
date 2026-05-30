<template>
  <view class="page-container">
    <view class="profile-header">
      <view class="profile-avatar">
        <image src="/static/assets/user.png" mode="aspectFit"></image>
      </view>
      <view style="flex:1">
        <text class="profile-name">张大农</text>
        <text class="profile-location">湖南省长沙市 · 种植大户</text>
        <view class="profile-tags">
          <text class="profile-tag">水稻</text>
          <text class="profile-tag">蔬菜</text>
          <text class="profile-tag">玉米</text>
        </view>
      </view>
    </view>

    <view class="profile-stats">
      <view>
        <text class="stat-value">128</text>
        <text class="stat-label">识别次数</text>
      </view>
      <view class="stat-divider"></view>
      <view>
        <text class="stat-value">36</text>
        <text class="stat-label">已收藏</text>
      </view>
      <view class="stat-divider"></view>
      <view>
        <text class="stat-value">15</text>
        <text class="stat-label">咨询记录</text>
      </view>
    </view>

    <view>
      <view v-for="item in menuItems" :key="item.label" class="profile-menu-item" @click="navigate(item.path)">
        <view class="menu-item-left">
          <image :src="'/static/assets/' + item.icon" mode="aspectFit"></image>
          <text>{{ item.label }}</text>
        </view>
        <image v-if="item.path" src="/static/assets/chevronright.png" mode="aspectFit" style="width:16px;height:16px"></image>
      </view>
    </view>
  </view>
</template>

<script setup>
const menuItems = [
  { icon: 'heart.png', label: '我的收藏', path: '/pages/knowledge/favorites' },
  { icon: 'bell.png', label: '浏览历史', path: '/pages/knowledge/history' },
  { icon: 'bell.png', label: '农事提醒', path: '/pages/reminder/index' },
  { icon: 'bell.png', label: '农事日历', path: '/pages/reminder/calendar' },
  { icon: 'bell.png', label: '病虫预警', path: '/pages/reminder/pest-warning' },
  { icon: 'chat.png', label: '咨询记录', path: '' },
  { icon: 'settings.png', label: '记忆设置', path: '' },
  { icon: 'info.png', label: '帮助反馈', path: '' },
  { icon: 'share2.png', label: '关于我们', path: '' },
];

function navigate(path) {
  if (!path) {
    uni.showToast({ title: '功能开发中', icon: 'none' });
    return;
  }
  const tabPages = ['/pages/home/index', '/pages/ai-chat/index', '/pages/knowledge/index', '/pages/profile/index'];
  if (tabPages.includes(path)) {
    uni.switchTab({ url: path });
  } else {
    uni.navigateTo({ url: path });
  }
}
</script>
