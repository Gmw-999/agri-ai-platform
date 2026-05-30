<template>
  <view class="page-container">
    <view class="page-content">
      <!-- 拍照识病 -->
      <view class="home-cta-card" @click="handlePhotoIdentify">
        <view class="cta-icon">
          <image src="/static/assets/camera.png" mode="aspectFit"></image>
        </view>
        <view>
          <text class="cta-title">拍照识病</text>
          <text class="cta-sub">拍照 / 相册上传 AI 智能分析病虫害</text>
        </view>
      </view>

      <!-- 快捷入口 -->
      <view class="quick-actions-grid">
        <view v-for="action in quickActions" :key="action.label" class="quick-action-card" @click="handleQuickAction(action)">
          <view class="qa-icon">
            <image :src="'/static/assets/' + action.icon" mode="aspectFit"></image>
          </view>
          <text class="qa-label">{{ action.label }}</text>
        </view>
      </view>

      <!-- 病虫害预警 -->
      <view class="section-card">
        <view class="section-header">
          <view class="section-title-row">
            <image src="/static/assets/trianglealert.png" mode="aspectFit" style="width:18px;height:18px"></image>
            <text class="section-title">本地病虫害预警</text>
          </view>
          <text class="section-more" @click="navigate('/pages/reminder/pest-warning')">查看全部 &gt;</text>
        </view>
        <view class="alert-item">
          <text class="alert-tag high">高风险</text>
          <text class="alert-text">水稻稻瘟病 — 近7日感染风险极高，建议提前防治</text>
        </view>
        <view class="alert-item">
          <text class="alert-tag mid">中风险</text>
          <text class="alert-text">玉米蚜虫 — 气温升高，注意田间监测</text>
        </view>
      </view>

      <!-- 当季推荐 -->
      <view class="section-card">
        <view class="section-header">
          <view class="section-title-row">
            <text class="section-title">当季作物管理推荐</text>
          </view>
          <text class="section-more" @click="navigate('/pages/ai-chat/index')">查看更多 &gt;</text>
        </view>
        <view class="crop-item">
          <image src="/static/assets/sprout.png" mode="aspectFit" style="width:36px;height:36px"></image>
          <view>
            <text class="crop-name">水稻 — 分蘖期管理</text>
            <text class="crop-desc">注意水位控制，适时追施氮肥</text>
          </view>
        </view>
        <view class="crop-item">
          <image src="/static/assets/leaf.png" mode="aspectFit" style="width:36px;height:36px"></image>
          <view>
            <text class="crop-name">蔬菜 — 梅雨季节防病指南</text>
            <text class="crop-desc">通风透气，减少叶面湿度</text>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue';
import { fileToBase64, stageImage } from '../../utils/api';

const quickActions = [
  { label: '病虫害识别', icon: 'bug.png', path: '/pages/result/index' },
  { label: '农事天气', icon: 'cloudsun.png', path: '/pages/weather/index' },
  { label: '农技知识库', icon: 'bookopen.png', path: '/pages/knowledge/index' },
  { label: '农事提醒', icon: 'bell.png', path: '/pages/reminder/index' },
];

function navigate(path) {
  const tabPages = ['/pages/home/index', '/pages/ai-chat/index', '/pages/knowledge/index', '/pages/profile/index'];
  if (tabPages.includes(path)) {
    uni.switchTab({ url: path });
  } else {
    uni.navigateTo({ url: path });
  }
}

async function pickPhoto(source, autoAnalyze) {
  try {
    let base64, tempPath;
    const res = await uni.chooseImage({
      count: 1,
      sourceType: [source],
      sizeType: ['compressed'],
    });
    if (!res.tempFilePaths.length) return;
    tempPath = res.tempFilePaths[0];
    base64 = await fileToBase64(tempPath);

    stageImage({ base64, tempPath, autoAnalyze });
    uni.navigateTo({ url: '/pages/result/index' });
  } catch (e) {
    const msg = (e && e.errMsg) ? e.errMsg.slice(0, 20) : '操作取消';
    uni.showToast({ title: msg, icon: 'none' });
  }
}

function handlePhotoIdentify() {
  uni.showActionSheet({
    itemList: ['拍照', '从相册选择'],
    success: (res) => {
      pickPhoto(res.tapIndex === 0 ? 'camera' : 'album', true);
    }
  });
}

function handleQuickAction(action) {
  if (action.label === '病虫害识别') {
    uni.showActionSheet({
      itemList: ['拍照', '从相册选择'],
      success: (res) => {
        pickPhoto(res.tapIndex === 0 ? 'camera' : 'album', false);
      }
    });
  } else if (action.path) {
    navigate(action.path);
  }
}
</script>
