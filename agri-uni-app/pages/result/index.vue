<template>
  <view class="page-container" style="height:100vh;display:flex;flex-direction:column;">
    <view class="page-header">
      <view style="display:flex;align-items:center;gap:8px" @click="goBack">
        <text style="font-size:18px">‹</text>
        <text class="header-title">{{ autoMode ? 'AI 分析结果' : '识别结果' }}</text>
      </view>
    </view>

    <scroll-view scroll-y style="flex:1;">
      <view style="padding:12px 16px">

        <!-- 图片预览 -->
        <view style="margin-bottom:16px">
          <image v-if="tempPath" :src="tempPath" mode="aspectFit" style="width:100%;height:200px;border-radius:8px;background:#f5f5f5"></image>
          <view v-else class="image-placeholder" @click="handlePickImage">
            <text style="color:#999">点击选择图片</text>
          </view>
        </view>

        <!-- 自动分析模式 -->
        <view v-if="autoMode">
          <!-- 加载中 -->
          <view v-if="combinedLoading" style="padding:24px;align-items:center">
            <view class="loading-spinner"></view>
            <text style="font-size:15px;color:#333;font-weight:500;margin-bottom:8px">AI 分析中，请稍候...</text>
            <text style="font-size:13px;color:#999">{{ progressText }}</text>
          </view>

          <!-- 分析结果 -->
          <view v-if="combinedReply" class="result-diagnosis-card">
            <text style="font-size:16px;font-weight:600;color:#333;margin-bottom:12px">诊断与防治方案</text>
            <template v-for="(seg, si) in combinedSegments" :key="si">
              <rich-text v-if="seg.type === 'richtext'" :nodes="seg.nodes"></rich-text>
              <view v-else-if="seg.type === 'purchase'" style="display:inline-block;padding:7px 20px;background:linear-gradient(135deg,#ff6b35,#f7931e);border-radius:20px;box-shadow:0 2px 8px rgba(255,107,53,0.3);margin:6px 3px" @click="copyPurchaseUrl(seg.url)">
                <text style="color:#fff;font-size:13px;font-weight:600">🛒 点击购买</text>
              </view>
            </template>
          </view>

          <!-- 创建提醒 -->
          <view v-if="combinedReply && !reminderDismissed" class="reminder-card">
            <view v-if="reminderCreated" style="padding:16px;background:#e8f5e9;border-radius:8px;align-items:center">
              <text style="font-size:14px;font-weight:600;color:#2e8b57;margin-bottom:8px">农事提醒已创建！</text>
              <text style="font-size:13px;color:#555;margin-bottom:4px;text-align:center">{{ reminderCreated.title }}</text>
              <text style="font-size:12px;color:#999;margin-bottom:12px">提醒日期：{{ reminderCreated.remind_date }} {{ reminderCreated.remind_time }}</text>
              <view style="display:flex;gap:8px">
                <view class="btn-green" @click="goReminderList">查看提醒</view>
                <view class="btn-gray" @click="reminderDismissed = true">好的</view>
              </view>
            </view>
            <view v-else style="padding:16px;background:#f1f8e9;border-radius:8px">
              <text style="font-size:13px;font-weight:500;color:#333;margin-bottom:10px">需要根据此分析创建农事提醒吗？</text>
              <text style="font-size:12px;color:#888;margin-bottom:12px">系统将自动提取病虫害名称和防治日期，生成提醒推送</text>
              <view style="display:flex;gap:8px">
                <view class="btn-green" style="flex:1" @click="createReminder">
                  <text style="font-size:13px;color:#fff">{{ reminderCreating ? '创建中...' : '创建提醒' }}</text>
                </view>
                <view class="btn-gray" style="flex:1" @click="reminderDismissed = true">
                  <text style="font-size:13px;color:#666">不用，谢谢</text>
                </view>
              </view>
            </view>
          </view>
        </view>

        <!-- 手动模式 -->
        <view v-else>
          <!-- 模型按钮 -->
          <view style="display:flex;gap:8px;margin-bottom:16px">
            <view v-for="(info, key) in MODEL_NAMES" :key="key"
              :style="{flex:1,padding:'10px 4px',borderRadius:8,background: results[key].data ? '#e8f5e9' : '#f5f5f5',alignItems:'center'}"
              @click="runModel(key)">
              <text style="font-size:11px;color:#2e8b57;font-weight:600;margin-bottom:2px;display:block;text-align:center">{{ MODEL_TAGS[key] }}</text>
              <text style="font-size:10px;color:#666;text-align:center;display:block">{{ key === 'yolov8' ? '目标检测' : key === 'resnet' ? '病害分类' : '病斑分割' }}</text>
            </view>
          </view>

          <!-- 模型结果 -->
          <view v-for="(info, key) in MODEL_NAMES" :key="key" style="margin-bottom:12px;padding:12px;background:#fafafa;border-radius:8px">
            <view style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
              <text style="font-size:14px;font-weight:500;color:#333">{{ info }}</text>
              <text v-if="results[key].data" style="font-size:11px;color:#2e8b57">识别成功</text>
            </view>
            <view v-if="results[key].loading"><text style="color:#999">分析中...</text></view>
            <view v-else-if="results[key].error"><text style="color:#e74c3c;font-size:13px">{{ results[key].error }}</text></view>
            <view v-else-if="!results[key].data"><text style="color:#ccc">点击上方按钮开始识别</text></view>
            <view v-else>
              <template v-if="key === 'yolov8'">
                <text v-if="!results[key].data.detections?.length" style="color:#999">未检测到目标</text>
                <view v-else>
                  <text style="font-size:13px;color:#2e8b57;font-weight:500;margin-bottom:8px;display:block">检测到 {{ results[key].data.detection_count }} 个目标</text>
                  <view v-for="(d, i) in results[key].data.detections" :key="i" style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid #f0f0f0">
                    <text style="font-size:13px;color:#333">{{ d.label }}</text>
                    <text style="font-size:12px;color:#2e8b57">{{ (d.confidence * 100).toFixed(1) }}%</text>
                  </view>
                </view>
              </template>
              <template v-else-if="key === 'resnet'">
                <text v-if="!results[key].data.top_predictions?.length" style="color:#999">未识别到病害</text>
                <view v-else>
                  <text style="font-size:13px;color:#2e8b57;font-weight:500;margin-bottom:8px;display:block">识别结果 Top {{ Math.min(results[key].data.top_predictions.length, 5) }}</text>
                  <view v-for="(p, i) in results[key].data.top_predictions.slice(0, 5)" :key="i" style="margin-bottom:8px">
                    <view style="display:flex;justify-content:space-between;margin-bottom:2px">
                      <text style="font-size:13px;color:#333">{{ p.class_cn || p.class }}</text>
                      <text style="font-size:12px;color:#2e8b57">{{ (p.confidence * 100).toFixed(1) }}%</text>
                    </view>
                    <view style="height:4px;background:#f0f0f0;border-radius:2px;overflow:hidden">
                      <view :style="{width: (p.confidence * 100).toFixed(1) + '%', height:'100%', background:'#2e8b57'}"></view>
                    </view>
                  </view>
                </view>
              </template>
              <template v-else-if="key === 'deeplabv3'">
                <text v-if="!results[key].data.segmentation" style="color:#999">分割结果为空</text>
                <view v-else>
                  <view style="margin-bottom:12px">
                    <view style="display:flex;justify-content:space-between;margin-bottom:4px">
                      <text style="font-size:13px;color:#333">病害面积占比</text>
                      <text :style="{fontSize:13,fontWeight:600,color: levelColor(results[key].data.segmentation.disease_area_ratio)}">
                        {{ (results[key].data.segmentation.disease_area_ratio * 100).toFixed(1) }}% — {{ levelText(results[key].data.segmentation.disease_area_ratio) }}
                      </text>
                    </view>
                    <view style="height:8px;background:#f0f0f0;border-radius:4px;overflow:hidden">
                      <view :style="{width: (results[key].data.segmentation.disease_area_ratio * 100).toFixed(1) + '%', height:'100%', background: levelColor(results[key].data.segmentation.disease_area_ratio), borderRadius:4}"></view>
                    </view>
                  </view>
                  <view style="display:flex;justify-content:space-around;padding:8px 0">
                    <view style="align-items:center">
                      <view style="width:12px;height:12px;background:#e74c3c;border-radius:2px;margin-bottom:2px"></view>
                      <text style="font-size:11px;color:#999">病斑区</text>
                    </view>
                    <view style="align-items:center">
                      <view style="width:12px;height:12px;background:#2e8b57;border-radius:2px;margin-bottom:2px"></view>
                      <text style="font-size:11px;color:#999">健康区</text>
                    </view>
                  </view>
                </view>
              </template>
            </view>
          </view>

          <!-- 综合分析 -->
          <view :style="{padding:12,borderRadius:8,background: combinedReply || combinedLoading ? '#fff8e1' : '#f5f5f5',marginBottom:24}">
            <view style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px" @click="runCombined()">
              <text style="font-size:14px;font-weight:500;color:#333">综合病虫害分析</text>
              <text v-if="combinedLoading" style="font-size:12px;color:#f39c12">分析中...</text>
              <text v-else style="font-size:12px;color:#2e8b57">{{ combinedReply ? '重新分析' : '开始分析 >>' }}</text>
            </view>
            <text v-if="combinedLoading" style="color:#999;font-size:13px">正在调用视觉模型并生成 AI 分析...</text>
            <template v-else-if="combinedReply" v-for="(seg, si) in combinedSegments" :key="'s2_' + si">
              <rich-text v-if="seg.type === 'richtext'" :nodes="seg.nodes"></rich-text>
              <view v-else-if="seg.type === 'purchase'" style="display:inline-block;padding:7px 20px;background:linear-gradient(135deg,#ff6b35,#f7931e);border-radius:20px;box-shadow:0 2px 8px rgba(255,107,53,0.3);margin:6px 3px" @click="copyPurchaseUrl(seg.url)">
                <text style="color:#fff;font-size:13px;font-weight:600">🛒 点击购买</text>
              </view>
            </template>
            <text v-else style="color:#ccc;font-size:13px">运行三个模型后，由 AI 综合分析给出诊断</text>
          </view>
        </view>

      </view>
    </scroll-view>
  </view>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { visionDetect, visionCropClassify, agentChat, genSessionId, consumeImage, reminderCreateFromAdvice, fileToBase64 } from '../../utils/api';

const MODEL_NAMES = { yolov8: 'YOLOv8 目标检测', resnet: 'ResNet 病害分类', deeplabv3: 'DeepLabV3 病斑分割' };
const MODEL_TAGS = { yolov8: '检测', resnet: '分类', deeplabv3: '分割' };

const imageBase64 = ref('');
const tempPath = ref('');
const autoMode = ref(false);
const results = ref({ yolov8: { loading: false, data: null, error: '' }, resnet: { loading: false, data: null, error: '' }, deeplabv3: { loading: false, data: null, error: '' } });
const combinedLoading = ref(false);
const combinedReply = ref('');
const combinedSegments = ref([{ type: 'richtext', nodes: [{ type: 'text', text: '' }] }]);
const reminderCreated = ref(null);
const reminderCreating = ref(false);
const reminderDismissed = ref(false);
const progressText = ref('');

function levelColor(ratio) {
  return ratio > 0.3 ? '#e74c3c' : ratio > 0.1 ? '#f39c12' : '#2e8b57';
}
function levelText(ratio) {
  return ratio > 0.3 ? '严重' : ratio > 0.1 ? '中等' : '轻度';
}

// 将纯文本/图片/加粗等转为 rich-text nodes（不处理购买链接）
function makeRichTextNodes(text) {
  if (!text) return [{ type: 'text', text: '' }];
  let t = text.replace(/```[a-z]*\n?/g, '').replace(/```/g, '');
  const stripUrls = (s) => s.replace(/https?:\/\/\S+/g, '').replace(/购买地址[：:]\s*/g, '').replace(/链接[：:]\s*/g, '');
  const nodes = [];
  const pattern = /!\[([^\]]*)\]\(([^)]+)\)|\[([^\]]+)\]\(([^)]+)\)|\*\*([^*]+)\*\*/g;
  let lastIndex = 0, match;
  while ((match = pattern.exec(t)) !== null) {
    if (match.index > lastIndex) {
      const txt = stripUrls(t.slice(lastIndex, match.index));
      if (txt.trim()) nodes.push({ type: 'text', text: txt });
    }
    if (match[1] !== undefined) {
      nodes.push({
        type: 'node', name: 'img',
        attrs: { src: match[2], style: 'max-width:100%;margin:8px 0;border-radius:10px;' }
      });
    } else if (match[2] !== undefined) {
      nodes.push({
        type: 'node', name: 'a',
        attrs: { href: match[3], style: 'color:#4A90D9;text-decoration:underline;' },
        children: [{ type: 'text', text: match[2] }]
      });
    } else if (match[4] !== undefined) {
      nodes.push({
        type: 'node', name: 'span',
        attrs: { style: 'font-weight:bold;color:#1a1a1a;' },
        children: [{ type: 'text', text: match[4] }]
      });
    }
    lastIndex = match.index + match[0].length;
  }
  if (lastIndex < t.length) {
    const txt = stripUrls(t.slice(lastIndex));
    if (txt.trim()) nodes.push({ type: 'text', text: txt });
  }
  return nodes.length ? nodes : [{ type: 'text', text: stripUrls(t) }];
}

// 按 [点击购买] 分割文本，购买按钮穿插在正确位置（图片下方）
function parseSegments(text) {
  if (!text) return [{ type: 'richtext', nodes: [{ type: 'text', text: '' }] }];
  const parts = text.split(/(\[点击购买\]\([^)]+\))/g);
  const segments = [];
  for (const part of parts) {
    const m = part.match(/^\[点击购买\]\(([^)]+)\)$/);
    if (m) {
      segments.push({ type: 'purchase', url: m[1] });
    } else if (part.trim()) {
      segments.push({ type: 'richtext', nodes: makeRichTextNodes(part) });
    }
  }
  return segments.length ? segments : [{ type: 'richtext', nodes: [{ type: 'text', text: '' }] }];
}

function setCombinedReply(text) {
  combinedReply.value = text;
  combinedSegments.value = parseSegments(text);
}

onMounted(() => {
  const pending = consumeImage();
  if (pending && pending.base64) {
    imageBase64.value = pending.base64;
    tempPath.value = pending.tempPath || '';
    if (pending.autoAnalyze) {
      autoMode.value = true;
      autoAnalyze(pending.base64);
    }
  }
});

function copyPurchaseUrl(url) {
  uni.setClipboardData({
    data: url,
    success: () => { uni.showToast({ title: '链接已复制，请在浏览器中打开', icon: 'none', duration: 2000 }); }
  });
}

function goBack() { uni.navigateBack(); }
function goReminderList() { uni.navigateTo({ url: '/pages/reminder/index' }); }

async function autoAnalyze(base64) {
  combinedLoading.value = true;
  setCombinedReply('');
  reminderCreated.value = null;
  reminderDismissed.value = false;

  const modelResults = {};
  progressText.value = 'YOLOv8 目标检测中...';
  try { modelResults.yolov8 = await visionDetect('yolov8', base64); } catch { modelResults.yolov8 = null; }

  progressText.value = '病斑裁剪 + ResNet 分类中...';
  try { modelResults.crop_classify = await visionCropClassify(base64); } catch { modelResults.crop_classify = null; }

  progressText.value = 'AI 综合分析中...';
  let summary = '【视觉模型检测结果】\n';
  if (modelResults.yolov8?.detections) {
    summary += `\nYOLOv8目标检测到${modelResults.yolov8.detection_count}个目标：\n`;
    modelResults.yolov8.detections.forEach(d => { summary += `- ${d.label} (置信度: ${(d.confidence * 100).toFixed(1)}%)\n`; });
  }
  const cc = modelResults.crop_classify;
  if (cc?.resnet?.top_predictions) {
    const cropNote = cc.crop_info?.cropped ? '（病斑裁剪后分类）' : '（全图分类）';
    summary += `\nResNet分类结果${cropNote}（Top3）：\n`;
    cc.resnet.top_predictions.slice(0, 3).forEach(p => { summary += `- ${p.class_cn || p.class}: ${(p.confidence * 100).toFixed(1)}%\n`; });
  }
  if (cc?.deeplab) {
    summary += `\nDeepLabV3病斑分割：病害面积占比 ${(cc.deeplab.disease_area_ratio * 100).toFixed(1)}%\n`;
  }
  try {
    const reply = await agentChat({ message: `请根据以下视觉模型检测结果，对作物病害进行分析，给出诊断结论、发病原因和防治建议（包含推荐用药和防治方法）：\n\n${summary}`, session_id: genSessionId(), image_base64: base64 });
    setCombinedReply(reply);
  } catch (e) {
    setCombinedReply(`分析失败：${e.message || '请检查网络后重试'}`);
  } finally {
    combinedLoading.value = false;
    progressText.value = '';
  }
}

async function runModel(key) {
  if (!imageBase64.value) { uni.showToast({ title: '请先选择图片', icon: 'none' }); return; }
  results.value[key] = { loading: true, data: null, error: '' };
  try {
    const raw = key === 'resnet' ? await visionCropClassify(imageBase64.value) : await visionDetect(key, imageBase64.value);
    const data = key === 'resnet' ? raw?.resnet : raw;
    console.log('[DEBUG] runModel', key, 'raw=', JSON.stringify(raw).slice(0, 200));
    if (data) {
      results.value[key] = { loading: false, data, error: '' };
    } else {
      results.value[key] = { loading: false, data: null, error: raw?.error || '调用失败' };
    }
  } catch (e) {
    results.value[key] = { loading: false, data: null, error: e.message || '网络异常' };
    console.error('[DEBUG] runModel error', key, e);
  }
}

async function runCombined() {
  const base64 = imageBase64.value;
  if (!base64) return;
  combinedLoading.value = true;
  setCombinedReply('');
  reminderCreated.value = null;
  reminderDismissed.value = false;

  const modelResults = {};
  results.value.yolov8 = { loading: true, data: null, error: '' };
  try { const data = await visionDetect('yolov8', base64); modelResults.yolov8 = data; results.value.yolov8 = { loading: false, data: data || null, error: '' }; }
  catch { results.value.yolov8 = { loading: false, data: null, error: '调用失败' }; }

  results.value.resnet = { loading: true, data: null, error: '' };
  results.value.deeplabv3 = { loading: true, data: null, error: '' };
  try {
    const ccData = await visionCropClassify(base64);
    modelResults.crop_classify = ccData;
    results.value.resnet = { loading: false, data: ccData?.resnet || null, error: '' };
    results.value.deeplabv3 = { loading: false, data: ccData?.deeplab || null, error: '' };
  } catch {
    results.value.resnet = { loading: false, data: null, error: '调用失败' };
    results.value.deeplabv3 = { loading: false, data: null, error: '调用失败' };
  }

  let summary = '【视觉模型检测结果】\n';
  if (modelResults.yolov8?.detections) {
    summary += `\nYOLOv8目标检测到${modelResults.yolov8.detection_count}个目标：\n`;
    modelResults.yolov8.detections.forEach(d => { summary += `- ${d.label} (置信度: ${(d.confidence * 100).toFixed(1)}%)\n`; });
  }
  const cc = modelResults.crop_classify;
  if (cc?.resnet?.top_predictions) {
    summary += `\nResNet分类结果（Top3）：\n`;
    cc.resnet.top_predictions.slice(0, 3).forEach(p => { summary += `- ${p.class_cn || p.class}: ${(p.confidence * 100).toFixed(1)}%\n`; });
  }
  if (cc?.deeplab) {
    summary += `\nDeepLabV3病斑分割：病害面积占比 ${(cc.deeplab.disease_area_ratio * 100).toFixed(1)}%\n`;
  }
  try {
    const reply = await agentChat({ message: `请根据视觉模型检测结果，给出诊断结论、发病原因和防治建议：\n\n${summary}`, session_id: genSessionId(), image_base64: base64 });
    setCombinedReply(reply);
  } catch (e) {
    setCombinedReply(`分析失败：${e.message || '请检查网络后重试'}`);
  } finally {
    combinedLoading.value = false;
  }
}

async function createReminder() {
  reminderCreating.value = true;
  try {
    const openid = uni.getStorageSync('openid') || 'anon';
    const res = await reminderCreateFromAdvice({ openid, diagnosis: combinedReply.value, image_base64: imageBase64.value });
    if (res.success && res.data) {
      reminderCreated.value = res.data;
    } else {
      uni.showToast({ title: res.error || '创建失败', icon: 'none' });
    }
  } catch (e) {
    uni.showToast({ title: e.message || '网络异常', icon: 'none' });
  } finally {
    reminderCreating.value = false;
  }
}

function handlePickImage() {
  uni.showActionSheet({
    itemList: ['拍照', '从相册选择'],
    success: (res) => {
      const source = res.tapIndex === 0 ? 'camera' : 'album';
      uni.chooseImage({ count: 1, sourceType: [source], sizeType: ['compressed'] })
        .then(async (res) => {
          if (!res.tempFilePaths.length) return;
          const path = res.tempFilePaths[0];
          try {
            const base64 = await fileToBase64(path);
            imageBase64.value = base64;
            tempPath.value = path;
            results.value = { yolov8: { loading: false, data: null, error: '' }, resnet: { loading: false, data: null, error: '' }, deeplabv3: { loading: false, data: null, error: '' } };
            setCombinedReply('');
            reminderCreated.value = null;
            reminderDismissed.value = false;
          } catch (e) {
            uni.showToast({ title: '图片读取失败', icon: 'none' });
          }
        }).catch(() => {});
    }
  });
}
</script>

<style scoped>
.image-placeholder {
  width: 100%;
  height: 160px;
  border-radius: 8px;
  background: #f5f5f5;
  display: flex;
  align-items: center;
  justify-content: center;
}
.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #e8e8e8;
  border-top: 3px solid #2e8b57;
  border-radius: 50%;
  margin: 0 auto 16px;
  animation: spin 1s linear infinite;
}
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
.result-diagnosis-card {
  padding: 16px;
  border-radius: 8px;
  background: #fff8e1;
  margin-bottom: 24px;
}
.reminder-card {
  margin-bottom: 24px;
  border-radius: 8px;
  border: 1px solid #81c784;
  overflow: hidden;
}
.btn-green {
  padding: 8px 20px;
  border-radius: 6px;
  background: #2e8b57;
  color: #fff;
  font-size: 13px;
  text-align: center;
}
.btn-gray {
  padding: 8px 20px;
  border-radius: 6px;
  background: #e0e0e0;
  color: #666;
  font-size: 13px;
  text-align: center;
}
</style>
