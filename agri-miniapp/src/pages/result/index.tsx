import { View, Text, Image, ScrollView } from '@tarojs/components';
import Taro from '@tarojs/taro';
import { useState, useEffect } from 'react';
import { visionDetect, visionCropClassify, agentChat, genSessionId, consumeImage, reminderCreateFromAdvice } from '../../api';

type ModelResult = {
  loading: boolean;
  data: any;
  error: string;
};

type ModelKey = 'yolov8' | 'resnet' | 'deeplabv3';

const MODEL_NAMES: Record<ModelKey, string> = {
  yolov8: 'YOLOv8 目标检测',
  resnet: 'ResNet 病害分类',
  deeplabv3: 'DeepLabV3 病斑分割',
};

const MODEL_TAGS: Record<ModelKey, string> = {
  yolov8: '检测',
  resnet: '分类',
  deeplabv3: '分割',
};

export default function IdentificationResult() {
  const [imageBase64, setImageBase64] = useState('');
  const [tempPath, setTempPath] = useState('');
  const [autoMode, setAutoMode] = useState(false); // true = 拍照识病, false = 病虫害识别
  const [results, setResults] = useState<Record<ModelKey, ModelResult>>({
    yolov8: { loading: false, data: null, error: '' },
    resnet: { loading: false, data: null, error: '' },
    deeplabv3: { loading: false, data: null, error: '' },
  });
  const [combinedLoading, setCombinedLoading] = useState(false);
  const [combinedReply, setCombinedReply] = useState('');
  const [reminderCreated, setReminderCreated] = useState<{id: number; title: string; remind_date: string; remind_time: string} | null>(null);
  const [reminderCreating, setReminderCreating] = useState(false);
  const [reminderDismissed, setReminderDismissed] = useState(false);
  const [progressText, setProgressText] = useState('');

  // On mount, check for staged image from home page
  useEffect(() => {
    const pending = consumeImage();
    if (pending && pending.base64) {
      setImageBase64(pending.base64);
      setTempPath(pending.tempPath || '');
      if (pending.autoAnalyze) {
        setAutoMode(true);
        autoAnalyze(pending.base64);
      } else {
        setAutoMode(false);
      }
    }
  }, []);

  const autoAnalyze = async (base64: string) => {
    setCombinedLoading(true);
    setCombinedReply('');
    setReminderCreated(null);
    setReminderDismissed(false);

    // Run all three models sequentially
    const modelResults: Record<string, any> = {};

    setProgressText('YOLOv8 目标检测中...');
    try {
      modelResults.yolov8 = await visionDetect('yolov8', base64);
    } catch { modelResults.yolov8 = null; }

    setProgressText('病斑裁剪 + ResNet 分类中...');
    try {
      modelResults.crop_classify = await visionCropClassify(base64);
    } catch { modelResults.crop_classify = null; }

    // Build summary text for LLM
    setProgressText('AI 综合分析中...');
    let summary = '【视觉模型检测结果】\n';
    if (modelResults.yolov8?.detections) {
      summary += `\nYOLOv8目标检测到${modelResults.yolov8.detection_count}个目标：\n`;
      modelResults.yolov8.detections.forEach((d: any) => {
        summary += `- ${d.label} (置信度: ${(d.confidence * 100).toFixed(1)}%)\n`;
      });
    }

    const cc = modelResults.crop_classify;
    if (cc?.resnet?.top_predictions) {
      const cropNote = cc.crop_info?.cropped ? '（病斑裁剪后分类）' : '（全图分类）';
      summary += `\nResNet分类结果${cropNote}（Top3）：\n`;
      cc.resnet.top_predictions.slice(0, 3).forEach((p: any) => {
        summary += `- ${p.class_cn || p.class}: ${(p.confidence * 100).toFixed(1)}%\n`;
      });
    }
    if (cc?.deeplab) {
      const modeNote = cc.crop_info?.cropped ? '（裁剪源）' : '';
      summary += `\nDeepLabV3病斑分割${modeNote}：病害面积占比 ${(cc.deeplab.disease_area_ratio * 100).toFixed(1)}%\n`;
    }

    // Send to LLM
    try {
      const reply = await agentChat({
        message: `请根据以下视觉模型检测结果，对作物病害进行分析，给出诊断结论、发病原因和防治建议（包含推荐用药和防治方法）：\n\n${summary}`,
        session_id: genSessionId(),
        image_base64: base64,
      });
      setCombinedReply(reply);
    } catch (e: any) {
      setCombinedReply(`分析失败：${e.message || '请检查网络后重试'}`);
    } finally {
      setCombinedLoading(false);
      setProgressText('');
    }
  };

  const runModel = async (key: ModelKey) => {
    if (!imageBase64) {
      Taro.showToast({ title: '请先选择图片', icon: 'none' });
      return;
    }

    setResults(prev => ({
      ...prev,
      [key]: { loading: true, data: null, error: '' },
    }));

    try {
      // ResNet 使用病斑裁剪后分类（DeepLab 分割 → 裁剪 → ResNet），去除背景干扰
      const raw = key === 'resnet'
        ? await visionCropClassify(imageBase64)
        : await visionDetect(key, imageBase64);

      const data = key === 'resnet'
        ? raw?.resnet  // crop_classify 返回 { resnet: {...}, deeplab: {...} }
        : raw;

      setResults(prev => ({
        ...prev,
        [key]: {
          loading: false,
          data: data?.success ? data : null,
          error: data?.success ? '' : (data?.error || raw?.error || '调用失败'),
        },
      }));
    } catch (e: any) {
      setResults(prev => ({
        ...prev,
        [key]: { loading: false, data: null, error: e.message || '网络异常' },
      }));
    }
  };

  const runCombined = async (base64Override?: string) => {
    const base64 = base64Override || imageBase64;
    if (!base64) return;
    setCombinedLoading(true);
    setCombinedReply('');
    setReminderCreated(null);
    setReminderDismissed(false);

    const modelResults: Record<string, any> = {};

    // Run YOLO (standalone)
    setResults(prev => ({ ...prev, yolov8: { loading: true, data: null, error: '' } }));
    try {
      const data = await visionDetect('yolov8', base64);
      modelResults.yolov8 = data.success ? data : null;
      setResults(prev => ({ ...prev, yolov8: { loading: false, data: data.success ? data : null, error: '' } }));
    } catch {
      setResults(prev => ({ ...prev, yolov8: { loading: false, data: null, error: '调用失败' } }));
    }

    // Run crop_classify (replaces standalone ResNet + DeepLab)
    setResults(prev => ({ ...prev,
      resnet: { loading: true, data: null, error: '' },
      deeplabv3: { loading: true, data: null, error: '' },
    }));
    try {
      const ccData = await visionCropClassify(base64);
      modelResults.crop_classify = ccData;

      // Transform for ResNet card
      const resnetCardData = ccData.resnet?.success ? {
        success: true,
        model: 'resnet',
        top_predictions: ccData.resnet.top_predictions || [],
        image_info: ccData.resnet.image_info,
      } : null;

      // Transform for DeepLab card
      const deeplabCardData = ccData.deeplab ? {
        success: true,
        model: 'deeplabv3',
        segmentation: {
          disease_area_ratio: ccData.deeplab.disease_area_ratio,
          disease_pixels: ccData.deeplab.disease_pixels || 0,
        },
        image_info: ccData.resnet?.image_info,
      } : null;

      setResults(prev => ({ ...prev,
        resnet: { loading: false, data: resnetCardData, error: '' },
        deeplabv3: { loading: false, data: deeplabCardData, error: '' },
      }));
    } catch {
      setResults(prev => ({ ...prev,
        resnet: { loading: false, data: null, error: '调用失败' },
        deeplabv3: { loading: false, data: null, error: '调用失败' },
      }));
    }

    let summary = '【视觉模型检测结果】\n';
    if (modelResults.yolov8?.detections) {
      summary += `\nYOLOv8目标检测到${modelResults.yolov8.detection_count}个目标：\n`;
      modelResults.yolov8.detections.forEach((d: any) => {
        summary += `- ${d.label} (置信度: ${(d.confidence * 100).toFixed(1)}%)\n`;
      });
    }

    const cc = modelResults.crop_classify;
    if (cc?.resnet?.top_predictions) {
      const cropNote = cc.crop_info?.cropped ? '（病斑裁剪后分类）' : '（全图分类）';
      summary += `\nResNet分类结果${cropNote}（Top3）：\n`;
      cc.resnet.top_predictions.slice(0, 3).forEach((p: any) => {
        summary += `- ${p.class_cn || p.class}: ${(p.confidence * 100).toFixed(1)}%\n`;
      });
    }
    if (cc?.deeplab) {
      const modeNote = cc.crop_info?.cropped ? '（裁剪源）' : '';
      summary += `\nDeepLabV3病斑分割${modeNote}：病害面积占比 ${(cc.deeplab.disease_area_ratio * 100).toFixed(1)}%\n`;
    }

    try {
      const reply = await agentChat({
        message: `请根据以下视觉模型检测结果，对作物病害进行分析，给出诊断结论、发病原因和防治建议：\n\n${summary}`,
        session_id: genSessionId(),
        image_base64: base64,
      });
      setCombinedReply(reply);
    } catch (e: any) {
      setCombinedReply(`分析失败：${e.message || '请检查网络后重试'}`);
    } finally {
      setCombinedLoading(false);
    }
  };

  const createReminder = async () => {
    setReminderCreating(true);
    try {
      const openid = Taro.getStorageSync('openid') || 'anon';
      const res = await reminderCreateFromAdvice({
        openid,
        diagnosis: combinedReply,
        image_base64: imageBase64,
      });
      if (res.success && res.data) {
        setReminderCreated(res.data);
      } else {
        Taro.showToast({ title: res.error || '创建失败', icon: 'none' });
      }
    } catch (e: any) {
      Taro.showToast({ title: e.message || '网络异常', icon: 'none' });
    } finally {
      setReminderCreating(false);
    }
  };

  const renderYOLOResult = (data: any) => {
    if (!data?.detections?.length) {
      return <Text style='color:#999'>未检测到目标</Text>;
    }
    return (
      <View>
        <Text style='font-size:13px;color:#2e8b57;font-weight:500;margin-bottom:8px;display:block'>
          检测到 {data.detection_count} 个目标
        </Text>
        {data.detections.map((d: any, i: number) => (
          <View key={i} style='display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid #f0f0f0'>
            <Text style='font-size:13px;color:#333'>{d.label}</Text>
            <Text style='font-size:12px;color:#2e8b57'>{(d.confidence * 100).toFixed(1)}%</Text>
          </View>
        ))}
      </View>
    );
  };

  const renderResNetResult = (data: any) => {
    if (!data?.top_predictions?.length) {
      return <Text style='color:#999'>未识别到病害</Text>;
    }
    return (
      <View>
        <Text style='font-size:13px;color:#2e8b57;font-weight:500;margin-bottom:8px;display:block'>
          识别结果 Top {Math.min(data.top_predictions.length, 5)}
        </Text>
        {data.top_predictions.slice(0, 5).map((p: any, i: number) => (
          <View key={i} style={{ marginBottom: 8 }}>
            <View style='display:flex;justify-content:space-between;margin-bottom:2px'>
              <Text style='font-size:13px;color:#333'>{p.class_cn || p.class}</Text>
              <Text style='font-size:12px;color:#2e8b57'>{(p.confidence * 100).toFixed(1)}%</Text>
            </View>
            <View style={{ height: 4, background: '#f0f0f0', borderRadius: 2, overflow: 'hidden' }}>
              <View style={{ width: `${(p.confidence * 100).toFixed(1)}%`, height: '100%', background: '#2e8b57' }} />
            </View>
          </View>
        ))}
      </View>
    );
  };

  const renderDeepLabResult = (data: any) => {
    if (!data?.segmentation) {
      return <Text style='color:#999'>分割结果为空</Text>;
    }
    const ratio = data.segmentation.disease_area_ratio || 0;
    const levelText = ratio > 0.3 ? '严重' : ratio > 0.1 ? '中等' : '轻度';
    const levelColor = ratio > 0.3 ? '#e74c3c' : ratio > 0.1 ? '#f39c12' : '#2e8b57';
    return (
      <View>
        <View style={{ marginBottom: 12 }}>
          <View style='display:flex;justify-content:space-between;margin-bottom:4px'>
            <Text style='font-size:13px;color:#333'>病害面积占比</Text>
            <Text style={{ fontSize: 13, fontWeight: 600, color: levelColor }}>
              {(ratio * 100).toFixed(1)}% — {levelText}
            </Text>
          </View>
          <View style={{ height: 8, background: '#f0f0f0', borderRadius: 4, overflow: 'hidden' }}>
            <View style={{ width: `${(ratio * 100).toFixed(1)}%`, height: '100%', background: levelColor, borderRadius: 4 }} />
          </View>
        </View>
        <View style='display:flex;justify-content:space-around;padding:8px 0'>
          <View style='align-items:center'>
            <View style={{ width: 12, height: 12, background: '#e74c3c', borderRadius: 2, marginBottom: 2 }} />
            <Text style='font-size:11px;color:#999'>病斑区</Text>
          </View>
          <View style='align-items:center'>
            <View style={{ width: 12, height: 12, background: '#2e8b57', borderRadius: 2, marginBottom: 2 }} />
            <Text style='font-size:11px;color:#999'>健康区</Text>
          </View>
        </View>
      </View>
    );
  };

  const renderModelResult = (key: ModelKey) => {
    const r = results[key];
    if (r.loading) {
      return <Text style='color:#999'>分析中...</Text>;
    }
    if (r.error) {
      return <Text style='color:#e74c3c;font-size:13px'>{r.error}</Text>;
    }
    if (!r.data) {
      return <Text style='color:#ccc'>点击上方按钮开始识别</Text>;
    }
    switch (key) {
      case 'yolov8':
        return renderYOLOResult(r.data);
      case 'resnet':
        return renderResNetResult(r.data);
      case 'deeplabv3':
        return renderDeepLabResult(r.data);
    }
  };

  // Pick image from album
  const handlePickImage = () => {
    Taro.showActionSheet({
      itemList: ['拍照', '从相册选择'],
    }).then((res) => {
      const source = res.tapIndex === 0 ? 'camera' : 'album';
      Taro.chooseImage({
        count: 1,
        sourceType: [source],
        sizeType: ['compressed'],
      }).then(async (res) => {
        if (!res.tempFilePaths.length) return;
        const path = res.tempFilePaths[0];
        const fileObj = res.tempFiles?.[0]?.originalFileObj as File | undefined;
        try {
          const { fileToBase64 } = await import('../../api');
          const base64 = await fileToBase64(path, fileObj);
          setImageBase64(base64);
          setTempPath(path);
          setResults({
            yolov8: { loading: false, data: null, error: '' },
            resnet: { loading: false, data: null, error: '' },
            deeplabv3: { loading: false, data: null, error: '' },
          });
          setCombinedReply('');
          setReminderCreated(null);
          setReminderDismissed(false);
        } catch (e: any) {
          Taro.showToast({ title: '图片读取失败', icon: 'none' });
        }
      }).catch(() => {});
    }).catch(() => {});
  };

  return (
    <View className='page-container' style='height:100vh;display:flex;flex-direction:column;'>
      <View className='page-header'>
        <View style='display:flex;align-items:center;gap:8px' onClick={() => Taro.navigateBack()}>
          <Text style='font-size:18px'>{'‹'}</Text>
          <Text className='header-title'>{autoMode ? 'AI 分析结果' : '识别结果'}</Text>
        </View>
      </View>

      <ScrollView scrollY style='flex:1;'>
        <View style='padding:12px 16px'>

        {/* Image preview */}
        <View style={{ marginBottom: 16 }}>
          {tempPath ? (
            <Image src={tempPath} mode='aspectFit' style='width:100%;height:200px;border-radius:8px;background:#f5f5f5' />
          ) : (
            <View
              style='width:100%;height:160px;border-radius:8px;background:#f5f5f5;display:flex;align-items:center;justify-content:center'
              onClick={handlePickImage}
            >
              <Text style='color:#999'>点击选择图片</Text>
            </View>
          )}
        </View>

        {autoMode ? (
          /* ====== 拍照识病：自动分析模式 ====== */
          <View>
            {combinedLoading && (
              <View style={{ padding: 24, alignItems: 'center' }}>
                <View style={{
                  width: 40, height: 40, borderWidth: 3, borderColor: '#2e8b57',
                  borderTopColor: 'transparent', borderRadius: 20,
                  marginBottom: 16,
                  animation: 'spin 1s linear infinite',
                }} />
                <Text style='font-size:15px;color:#333;font-weight:500;margin-bottom:8px'>AI 分析中，请稍候...</Text>
                <Text style='font-size:13px;color:#999'>{progressText}</Text>
              </View>
            )}

            {combinedReply && (
              <View style={{
                padding: 16, borderRadius: 8, background: '#fff8e1',
                marginBottom: 24,
              }}>
                <Text style='font-size:16px;font-weight:600;color:#333;margin-bottom:12px'>诊断与防治方案</Text>
                <Text style='font-size:14px;color:#333;line-height:1.8;white-space:pre-wrap'>{combinedReply}</Text>
              </View>
            )}

            {/* 创建农事提醒 */}
            {combinedReply && !reminderDismissed && (
              <View style={{
                marginBottom: 24, borderRadius: 8,
                borderWidth: 1, borderColor: '#81c784', borderStyle: 'solid',
                overflow: 'hidden',
              }}>
                {reminderCreated ? (
                  <View style={{
                    padding: 16, background: '#e8f5e9', borderRadius: 8, alignItems: 'center',
                  }}>
                    <Text style='font-size:14px;font-weight:600;color:#2e8b57;margin-bottom:8px'>
                      农事提醒已创建！
                    </Text>
                    <Text style='font-size:13px;color:#555;margin-bottom:4px;text-align:center'>
                      {reminderCreated.title}
                    </Text>
                    <Text style='font-size:12px;color:#999;margin-bottom:12px'>
                      提醒日期：{reminderCreated.remind_date} {reminderCreated.remind_time}
                    </Text>
                    <View style='display:flex;gap:8'>
                      <View
                        style={{
                          padding: '8px 20px', borderRadius: 6, background: '#2e8b57',
                          display:'inline-block',
                        }}
                        onClick={() => Taro.navigateTo({ url: '/pages/reminder/index' })}
                      >
                        <Text style='font-size:13px;color:#fff'>查看提醒</Text>
                      </View>
                      <View
                        style={{
                          padding: '8px 20px', borderRadius: 6, background: '#f5f5f5',
                          display:'inline-block',
                        }}
                        onClick={() => setReminderDismissed(true)}
                      >
                        <Text style='font-size:13px;color:#666'>好的</Text>
                      </View>
                    </View>
                  </View>
                ) : (
                  <View style={{
                    padding: 16, background: '#f1f8e9', borderRadius: 8,
                  }}>
                    <Text style='font-size:13px;font-weight:500;color:#333;margin-bottom:10px'>
                      需要根据此分析创建农事提醒吗？
                    </Text>
                    <Text style='font-size:12px;color:#888;margin-bottom:12px'>
                      系统将自动提取病虫害名称和防治日期，生成提醒推送
                    </Text>
                    <View style='display:flex;gap:8'>
                      <View
                        style={{
                          flex: 1, padding: '8px 0', borderRadius: 6, background: '#2e8b57', alignItems: 'center',
                        }}
                        onClick={createReminder}
                      >
                        <Text style='font-size:13px;color:#fff'>
                          {reminderCreating ? '创建中...' : '创建提醒'}
                        </Text>
                      </View>
                      <View
                        style={{
                          flex: 1, padding: '8px 0', borderRadius: 6, background: '#e0e0e0', alignItems: 'center',
                        }}
                        onClick={() => setReminderDismissed(true)}
                      >
                        <Text style='font-size:13px;color:#666'>不用，谢谢</Text>
                      </View>
                    </View>
                  </View>
                )}
              </View>
            )}

          </View>
        ) : (
          /* ====== 病虫害识别：手动选择模型模式 ====== */
          <View>
            {/* Model buttons */}
            <View style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
              {(Object.keys(MODEL_NAMES) as ModelKey[]).map((key) => (
                <View
                  key={key}
                  style={{
                    flex: 1,
                    padding: '10px 4px',
                    borderRadius: 8,
                    background: results[key].data ? '#e8f5e9' : '#f5f5f5',
                    alignItems: 'center',
                  }}
                  onClick={() => runModel(key)}
                >
                  <Text style={{ fontSize: 11, color: '#2e8b57', fontWeight: 600, marginBottom: 2 }}>
                    {MODEL_TAGS[key]}
                  </Text>
                  <Text style={{ fontSize: 10, color: '#666', textAlign: 'center' }}>
                    {key === 'yolov8' ? '目标检测' : key === 'resnet' ? '病害分类' : '病斑分割'}
                  </Text>
                </View>
              ))}
            </View>

            {/* Model results */}
            {(Object.keys(MODEL_NAMES) as ModelKey[]).map((key) => (
              <View key={key} style={{ marginBottom: 12, padding: 12, background: '#fafafa', borderRadius: 8 }}>
                <View style='display:flex;justify-content:space-between;align-items:center;margin-bottom:8px'>
                  <Text style='font-size:14px;font-weight:500;color:#333'>{MODEL_NAMES[key]}</Text>
                  {results[key].data && (
                    <Text style='font-size:11px;color:#2e8b57'>识别成功</Text>
                  )}
                </View>
                {renderModelResult(key)}
              </View>
            ))}

            {/* Combined analysis */}
            <View
              style={{
                padding: 12,
                borderRadius: 8,
                background: combinedReply || combinedLoading ? '#fff8e1' : '#f5f5f5',
                marginBottom: 24,
              }}
            >
              <View
                style='display:flex;justify-content:space-between;align-items:center;margin-bottom:8px'
                onClick={() => runCombined()}
              >
                <Text style='font-size:14px;font-weight:500;color:#333'>综合病虫害分析</Text>
                {combinedLoading ? (
                  <Text style='font-size:12px;color:#f39c12'>分析中...</Text>
                ) : (
                  <Text style='font-size:12px;color:#2e8b57'>{combinedReply ? '重新分析' : '开始分析 >>'}</Text>
                )}
              </View>
              {combinedLoading && (
                <Text style='color:#999;font-size:13px'>正在调用视觉模型并生成 AI 分析...</Text>
              )}
              {combinedReply && (
                <Text style='font-size:13px;color:#333;line-height:1.6'>{combinedReply}</Text>
              )}
              {!combinedReply && !combinedLoading && (
                <Text style='color:#ccc;font-size:13px'>运行三个模型后，由 AI 综合分析给出诊断</Text>
              )}
            </View>
          </View>
        )}

        </View>
      </ScrollView>
    </View>
  );
}
