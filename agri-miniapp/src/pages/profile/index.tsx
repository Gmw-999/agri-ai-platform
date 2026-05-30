import { View, Text, Image } from '@tarojs/components';
import Taro from '@tarojs/taro';

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

export default function Profile() {
  return (
    <View className='page-container'>
      {/* Profile Header */}
      <View className='profile-header'>
        <View className='profile-avatar'>
          <Image src='../../assets/user.png' mode='aspectFit' />
        </View>
        <View style='flex:1'>
          <Text className='profile-name'>张大农</Text>
          <Text className='profile-location'>湖南省长沙市 · 种植大户</Text>
          <View className='profile-tags'>
            <Text className='profile-tag'>水稻</Text>
            <Text className='profile-tag'>蔬菜</Text>
            <Text className='profile-tag'>玉米</Text>
          </View>
        </View>
      </View>

      {/* Stats */}
      <View className='profile-stats'>
        <View>
          <Text className='stat-value'>128</Text>
          <Text className='stat-label'>识别次数</Text>
        </View>
        <View className='stat-divider' />
        <View>
          <Text className='stat-value'>36</Text>
          <Text className='stat-label'>已收藏</Text>
        </View>
        <View className='stat-divider' />
        <View>
          <Text className='stat-value'>15</Text>
          <Text className='stat-label'>咨询记录</Text>
        </View>
      </View>

      {/* Menu */}
      <View>
        {menuItems.map((item) => (
          <View key={item.label} className='profile-menu-item' onClick={() => item.path && Taro.navigateTo({ url: item.path })}>
            <View className='menu-item-left'>
              <Image src={`../../assets/${item.icon}`} mode='aspectFit' />
              <Text>{item.label}</Text>
            </View>
            <Image src='../../assets/chevronright.png' mode='aspectFit' style='width:16px;height:16px' />
          </View>
        ))}
      </View>
    </View>
  );
}
