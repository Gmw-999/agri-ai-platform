import { View, Text, Image, ScrollView } from '@tarojs/components';
import Taro from '@tarojs/taro';
import { useState, useEffect } from 'react';
import { API } from '../../api/config';

interface PestWarning {
  id: number; region: string; crop: string; pest_name: string;
  warning_level: string; description: string; prevention_measures: string;
  start_date: string; end_date: string; source: string;
}

const LEVEL_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  extreme: { label: '特急', color: '#fff', bg: '#e74c3c' },
  high: { label: '高危', color: '#fff', bg: '#f39c12' },
  medium: { label: '预警', color: '#333', bg: '#f1c40f' },
  low: { label: '注意', color: '#666', bg: '#ecf0f1' },
};

export default function PestWarning() {
  const [list, setList] = useState<PestWarning[]>([]);
  const [loading, setLoading] = useState(true);
  const [region, setRegion] = useState('');

  useEffect(() => {
    Taro.request({
      url: API.reminderPestWarnings,
      data: { region, limit: 50 },
    }).then((r: any) => {
      if (r.data?.success) setList(r.data.data);
    }).finally(() => setLoading(false));
  }, []);

  const getLevelConf = (level: string) => LEVEL_CONFIG[level] || LEVEL_CONFIG.low;

  return (
    <View className='page-container'>
      <View className='page-header'>
        <View style='display:flex;align-items:center;gap:8px' onClick={() => Taro.navigateBack()}>
          <Text style='font-size:18px'>{'‹'}</Text>
          <Text className='header-title'>病虫害预警</Text>
        </View>
      </View>
      <View className='page-content' style='padding-bottom:40px'>
        {/* Legend */}
        <View style='display:flex;gap:12px;margin-bottom:16px;flex-wrap:wrap'>
          {Object.entries(LEVEL_CONFIG).map(([k, v]) => (
            <View key={k} style='display:flex;align-items:center;gap:4px'>
              <View style={`width:10px;height:10px;border-radius:3px;background:${v.bg}`} />
              <Text style='font-size:11px;color:#666'>{v.label}</Text>
            </View>
          ))}
        </View>

        {/* Warning Cards */}
        {loading && <Text style='color:#999;text-align:center;padding:40px'>加载中...</Text>}
        {!loading && list.length === 0 && (
          <View className='empty-state' style='margin-top:40px'>
            <Text className='empty-title'>暂无预警信息</Text>
            <Text className='empty-desc'>当前地区暂无病虫害预警</Text>
          </View>
        )}

        {list.map((item) => {
          const lc = getLevelConf(item.warning_level);
          return (
            <View key={item.id} className='section-card' style={`margin-bottom:12px;border-left:4px solid ${lc.bg}`}>
              <View style='display:flex;align-items:center;justify-content:space-between;margin-bottom:8px'>
                <Text style='font-size:15px;font-weight:600;color:#333'>{item.pest_name}</Text>
                <View style={`padding:2px 10px;border-radius:4px;background:${lc.bg}`}>
                  <Text style={`font-size:11px;font-weight:600;color:${lc.color}`}>{lc.label}</Text>
                </View>
              </View>
              <Text style='font-size:12px;color:#666;margin-bottom:6px'>{item.crop} · {item.region} · {item.start_date}~{item.end_date}</Text>
              <Text style='font-size:13px;color:#333;line-height:1.6;margin-bottom:8px'>{item.description}</Text>
              {item.prevention_measures && (
                <View style='background:#f8f9fa;border-radius:8px;padding:10px'>
                  <Text style='font-size:12px;font-weight:500;color:#27AE60;margin-bottom:4px'>防治措施</Text>
                  <Text style='font-size:13px;color:#333;line-height:1.7;white-space:pre-wrap'>{item.prevention_measures}</Text>
                </View>
              )}
            </View>
          );
        })}
      </View>
    </View>
  );
}
