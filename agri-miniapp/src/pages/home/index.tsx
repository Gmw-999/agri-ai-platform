import { View, Text, Image } from '@tarojs/components';
import Taro from '@tarojs/taro';
import { fileToBase64, stageImage } from '../../api';

const quickActions = [
  { label: '病虫害识别', icon: 'bug.png', path: '/pages/result/index' },
  { label: '农事天气', icon: 'cloudsun.png', path: '/pages/weather/index' },
  { label: '农技知识库', icon: 'bookopen.png', path: '/pages/knowledge/index' },
  { label: '农事提醒', icon: 'bell.png', path: '/pages/reminder/index' },
];

export default function Home() {
  const navigate = (path: string) => {
    const tabPages = ['/pages/home/index', '/pages/ai-chat/index', '/pages/knowledge/index', '/pages/profile/index'];
    if (tabPages.includes(path)) {
      Taro.switchTab({ url: path });
    } else {
      Taro.navigateTo({ url: path });
    }
  };

  const handlePhotoIdentify = () => {
    Taro.showActionSheet({
      itemList: ['拍照', '从相册选择'],
    }).then((res) => {
      pickPhoto(res.tapIndex === 0 ? 'camera' : 'album', true);
    }).catch(() => {});
  };

  const pickPhoto = async (source: 'camera' | 'album', autoAnalyze: boolean) => {
    try {
      let base64: string;
      let tempPath = '';

      if (process.env.TARO_ENV === 'h5') {
        base64 = await new Promise((resolve, reject) => {
          const input = document.createElement('input');
          input.type = 'file';
          input.accept = 'image/*';
          if (source === 'camera') input.capture = 'environment';
          input.style.display = 'none';
          document.body.appendChild(input);

          const timeoutId = setTimeout(() => {
            document.body.removeChild(input);
            reject(new Error('操作超时'));
          }, 120000);

          input.addEventListener('change', () => {
            clearTimeout(timeoutId);
            const file = input.files?.[0];
            document.body.removeChild(input);
            if (!file) return reject(new Error('未选择文件'));

            tempPath = URL.createObjectURL(file);

            const reader = new FileReader();
            reader.onloadend = () => {
              const result = reader.result as string;
              resolve(result.includes(',') ? result.split(',')[1] : result);
            };
            reader.onerror = () => reject(new Error('文件读取失败'));
            reader.readAsDataURL(file);
          });

          input.click();
        });
      } else {
        const res = await Taro.chooseImage({
          count: 1,
          sourceType: [source],
          sizeType: ['compressed'],
        });
        if (!res.tempFilePaths.length) return;

        tempPath = res.tempFilePaths[0];
        const fileObj = res.tempFiles?.[0]?.originalFileObj;
        base64 = await fileToBase64(tempPath, fileObj);
      }

      stageImage({ base64, tempPath, autoAnalyze });
      Taro.navigateTo({ url: '/pages/result/index' });
    } catch (e: any) {
      console.error('pickPhoto error:', e);
      const msg = (e && e.message) ? e.message.slice(0, 20) : '操作取消';
      Taro.showToast({ title: msg, icon: 'none' });
    }
  };

  const handleQuickAction = (action: { label: string; icon: string; path?: string }) => {
    if (action.label === '病虫害识别') {
      Taro.showActionSheet({
        itemList: ['拍照', '从相册选择'],
      }).then((res) => {
        pickPhoto(res.tapIndex === 0 ? 'camera' : 'album', false);
      }).catch(() => {});
    } else if (action.path) {
      navigate(action.path);
    }
  };

  return (
    <View className='page-container'>
      <View className='page-content'>
        {/* Photo Identify CTA */}
        <View className='home-cta-card' onClick={handlePhotoIdentify}>
          <View className='cta-icon'>
            <Image src='../../assets/camera.png' mode='aspectFit' />
          </View>
          <View>
            <Text className='cta-title'>拍照识病</Text>
            <Text className='cta-sub'>拍照 / 相册上传 AI 智能分析病虫害</Text>
          </View>
        </View>

        {/* Quick Actions */}
        <View className='quick-actions-grid'>
          {quickActions.map((action) => (
            <View key={action.label} className='quick-action-card' onClick={() => handleQuickAction(action)}>
              <View className='qa-icon'>
                <Image src={`../../assets/${action.icon}`} mode='aspectFit' />
              </View>
              <Text className='qa-label'>{action.label}</Text>
            </View>
          ))}
        </View>

        {/* Pest Alert */}
        <View className='section-card'>
          <View className='section-header'>
            <View className='section-title-row'>
              <Image src='../../assets/trianglealert.png' mode='aspectFit' style='width:18px;height:18px' />
              <Text className='section-title'>本地病虫害预警</Text>
            </View>
            <Text className='section-more' onClick={() => navigate('/pages/reminder/pest-warning')}>
              查看全部 &gt;
            </Text>
          </View>

          <View className='alert-item'>
            <Text className='alert-tag high'>高风险</Text>
            <Text className='alert-text'>水稻稻瘟病 — 近7日感染风险极高，建议提前防治</Text>
          </View>
          <View className='alert-item'>
            <Text className='alert-tag mid'>中风险</Text>
            <Text className='alert-text'>玉米蚜虫 — 气温升高，注意田间监测</Text>
          </View>
        </View>

        {/* Seasonal Crop Management */}
        <View className='section-card'>
          <View className='section-header'>
            <View className='section-title-row'>
              <Text className='section-title'>当季作物管理推荐</Text>
            </View>
            <Text className='section-more' onClick={() => navigate('/pages/ai-chat/index')}>
              查看更多 &gt;
            </Text>
          </View>

          <View className='crop-item'>
            <Image src='../../assets/sprout.png' mode='aspectFit' style='width:36px;height:36px' />
            <View>
              <Text className='crop-name'>水稻 — 分蘖期管理</Text>
              <Text className='crop-desc'>注意水位控制，适时追施氮肥</Text>
            </View>
          </View>
          <View className='crop-item'>
            <Image src='../../assets/leaf.png' mode='aspectFit' style='width:36px;height:36px' />
            <View>
              <Text className='crop-name'>蔬菜 — 梅雨季节防病指南</Text>
              <Text className='crop-desc'>通风透气，减少叶面湿度</Text>
            </View>
          </View>
        </View>
      </View>
    </View>
  );
}
