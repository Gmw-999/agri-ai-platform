import { View, Text, Image, ScrollView } from '@tarojs/components';
import Taro from '@tarojs/taro';
import { useState, useEffect } from 'react';
import { API } from '../../api/config';

interface ReminderItem {
  id: number; title: string; content: string;
  remind_date: string; remind_time: string;
  remind_type: string; crop_type: string; status: string;
}

const TYPE_LABELS: Record<string, string> = {
  weather: '天气', crop: '农事', pesticide: '植保', custom: '自定义',
};
const TYPE_COLORS: Record<string, string> = {
  weather: '#3498db', crop: '#27AE60', pesticide: '#e74c3c', custom: '#f39c12',
};

export default function ReminderHome() {
  const [reminders, setReminders] = useState<ReminderItem[]>([]);
  const [weatherAdvice, setWeatherAdvice] = useState('');
  const [loading, setLoading] = useState(true);

  const openid = Taro.getStorageSync('openid') || '';

  const fetchReminders = () => {
    if (!openid) return;
    Taro.request({
      url: API.reminderList,
      data: { openid, status: 'pending', page_size: 50 },
    }).then((r: any) => {
      if (r.data?.success) setReminders(r.data.data);
    });
  };

  const fetchWeatherAdvice = () => {
    Taro.request({
      url: API.reminderWeatherAdvice,
      data: { region: '长沙' },
    }).then((r: any) => {
      if (r.data?.success) setWeatherAdvice(r.data.data.advice || '');
    }).catch(() => {
      // 后端未启动或网络不可达，静默忽略
    }).finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchReminders();
    fetchWeatherAdvice();
  }, []);

  const completeReminder = (id: number) => {
    Taro.request({
      url: API.reminderUpdate,
      method: 'PUT',
      data: { id, status: 'completed' },
    }).then(() => {
      setReminders(reminders.filter(r => r.id !== id));
      Taro.showToast({ title: '已完成', icon: 'none' });
    });
  };

  const deleteReminder = (id: number) => {
    Taro.showModal({
      title: '删除提醒', content: '确定删除？',
      success: (res) => {
        if (res.confirm) {
          Taro.request({ url: API.reminderDelete, method: 'DELETE', data: { id } })
            .then(() => {
              setReminders(reminders.filter(r => r.id !== id));
              Taro.showToast({ title: '已删除', icon: 'none' });
            });
        }
      },
    });
  };

  return (
    <View className='page-container'>
      <View className='page-content' style='padding-bottom:80px'>
        {/* Weather Advice Card */}
        {weatherAdvice && (
          <View className='section-card' style='margin-bottom:12px;background:#f0faf0;border-left:3px solid #27AE60'>
            <View className='section-title-row'>
              <Image src='../../assets/sun.png' mode='aspectFit' style='width:20px;height:20px' />
              <Text className='section-title'>今日农事建议</Text>
            </View>
            <Text style='font-size:13px;color:#333;line-height:1.7;margin-top:6px'>{weatherAdvice.slice(0, 200)}</Text>
          </View>
        )}

        {/* Quick Actions */}
        <View style='display:flex;gap:10px;margin-bottom:16px'>
          <View className='quick-action-btn' onClick={() => Taro.navigateTo({ url: '/pages/reminder/add' })}>
            <Image src='../../assets/checkcircle.png' mode='aspectFit' style='width:24px;height:24px;margin-bottom:4px' />
            <Text style='font-size:12px;color:#333'>新建提醒</Text>
          </View>
          <View className='quick-action-btn' onClick={() => Taro.navigateTo({ url: '/pages/reminder/calendar' })}>
            <Image src='../../assets/sprout.png' mode='aspectFit' style='width:24px;height:24px;margin-bottom:4px' />
            <Text style='font-size:12px;color:#333'>农事日历</Text>
          </View>
          <View className='quick-action-btn' onClick={() => Taro.navigateTo({ url: '/pages/reminder/pest-warning' })}>
            <Image src='../../assets/leaf0.png' mode='aspectFit' style='width:24px;height:24px;margin-bottom:4px' />
            <Text style='font-size:12px;color:#333'>病虫预警</Text>
          </View>
        </View>

        {/* Reminder List */}
        <View style='display:flex;align-items:center;justify-content:space-between;margin-bottom:10px'>
          <Text className='section-title' style='margin-bottom:0'>待办提醒</Text>
          {reminders.length > 0 && (
            <Text style='font-size:12px;color:#999'>{reminders.length}条待办</Text>
          )}
        </View>

        {reminders.length === 0 && (
          <View className='empty-state' style='margin-top:20px'>
            <Text className='empty-title'>暂无待办提醒</Text>
            <Text className='empty-desc'>点击上方新建提醒</Text>
          </View>
        )}

        {reminders.map((item) => (
          <View key={item.id} className='section-card' style='margin-bottom:8px;padding:12px'>
            <View style='display:flex;align-items:flex-start;gap:10px'>
              <View style={`width:4px;height:36px;border-radius:2px;background:${TYPE_COLORS[item.remind_type] || '#999'};flex-shrink:0`} />
              <View style='flex:1'>
                <View style='display:flex;align-items:center;gap:6px;margin-bottom:4px'>
                  <Text style='font-size:12px;color:#666;background:#f5f5f5;padding:1px 8px;border-radius:4px'>{TYPE_LABELS[item.remind_type] || '自定义'}</Text>
                  <Text style='font-size:12px;color:#999'>{item.remind_date} {item.remind_time?.slice(0, 5)}</Text>
                </View>
                <Text style='font-size:14px;font-weight:500;color:#333'>{item.title}</Text>
                {item.content && <Text style='font-size:12px;color:#666;margin-top:4px'>{item.content.slice(0, 50)}</Text>}
              </View>
              <View style='display:flex;flex-direction:column;gap:4px'>
                <Text style='font-size:18px;color:#27AE60' onClick={() => completeReminder(item.id)}>✓</Text>
                <Text style='font-size:14px;color:#ccc' onClick={() => deleteReminder(item.id)}>✕</Text>
              </View>
            </View>
          </View>
        ))}
      </View>
    </View>
  );
}
