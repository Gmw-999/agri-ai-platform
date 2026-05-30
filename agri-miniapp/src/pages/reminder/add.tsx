import { View, Text, Input, Picker, Textarea } from '@tarojs/components';
import Taro from '@tarojs/taro';
import { useState } from 'react';
import { API } from '../../api/config';

const TYPE_OPTIONS = [
  { value: 'custom', label: '自定义' },
  { value: 'weather', label: '天气农事' },
  { value: 'crop', label: '作物管理' },
  { value: 'pesticide', label: '植保防治' },
];

export default function AddReminder() {
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [date, setDate] = useState(() => {
    const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  });
  const [time, setTime] = useState('08:00');
  const [typeIndex, setTypeIndex] = useState(0);
  const [cropType, setCropType] = useState('');

  const save = () => {
    if (!title.trim()) { Taro.showToast({ title: '请输入提醒标题', icon: 'none' }); return; }
    const openid = Taro.getStorageSync('openid') || 'anon';
    Taro.request({
      url: API.reminderCreate,
      method: 'POST',
      data: {
        openid,
        title: title.trim(),
        content: content.trim(),
        remind_date: date,
        remind_time: time,
        remind_type: TYPE_OPTIONS[typeIndex].value,
        crop_type: cropType,
      },
    }).then((r: any) => {
      if (r.data?.success) {
        Taro.showToast({ title: '创建成功', icon: 'none' });
        setTimeout(() => Taro.navigateBack(), 1000);
      } else {
        Taro.showToast({ title: '创建失败', icon: 'none' });
      }
    });
  };

  return (
    <View className='page-container'>
      <View className='page-header'>
        <View style='display:flex;align-items:center;justify-content:space-between'>
          <View style='display:flex;align-items:center;gap:8px' onClick={() => Taro.navigateBack()}>
            <Text style='font-size:18px'>{'‹'}</Text>
            <Text className='header-title'>新建提醒</Text>
          </View>
          <Text style='font-size:14px;color:#27AE60;font-weight:500' onClick={save}>保存</Text>
        </View>
      </View>
      <View className='page-content'>
        {/* Title */}
        <View className='form-group'>
          <Text className='form-label'>提醒标题</Text>
          <Input
            className='form-input'
            placeholder='如：打药、施肥、浇水...'
            value={title}
            onInput={(e) => setTitle(e.detail.value)}
          />
        </View>

        {/* Date */}
        <View className='form-group'>
          <Text className='form-label'>日期</Text>
          <Picker mode='date' value={date} onChange={(e) => setDate(e.detail.value)}>
            <View className='form-input' style='display:flex;align-items:center;justify-content:space-between'>
              <Text>{date}</Text>
              <Text style='color:#999'>></Text>
            </View>
          </Picker>
        </View>

        {/* Time */}
        <View className='form-group'>
          <Text className='form-label'>时间</Text>
          <Picker mode='time' value={time} onChange={(e) => setTime(e.detail.value)}>
            <View className='form-input' style='display:flex;align-items:center;justify-content:space-between'>
              <Text>{time}</Text>
              <Text style='color:#999'>></Text>
            </View>
          </Picker>
        </View>

        {/* Type */}
        <View className='form-group'>
          <Text className='form-label'>提醒类型</Text>
          <Picker mode='selector' range={TYPE_OPTIONS.map(o => o.label)} value={typeIndex} onChange={(e) => setTypeIndex(Number(e.detail.value))}>
            <View className='form-input' style='display:flex;align-items:center;justify-content:space-between'>
              <Text>{TYPE_OPTIONS[typeIndex].label}</Text>
              <Text style='color:#999'>></Text>
            </View>
          </Picker>
        </View>

        {/* Crop */}
        <View className='form-group'>
          <Text className='form-label'>关联作物（可选）</Text>
          <Input
            className='form-input'
            placeholder='如：水稻、小麦、番茄...'
            value={cropType}
            onInput={(e) => setCropType(e.detail.value)}
          />
        </View>

        {/* Content */}
        <View className='form-group'>
          <Text className='form-label'>备注说明</Text>
          <Textarea
            className='form-textarea'
            placeholder='输入提醒的具体内容...'
            value={content}
            onInput={(e) => setContent(e.detail.value)}
          />
        </View>
      </View>
    </View>
  );
}
