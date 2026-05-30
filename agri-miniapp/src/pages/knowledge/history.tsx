import { View, Text, Image } from '@tarojs/components';
import Taro from '@tarojs/taro';
import { useState, useEffect } from 'react';
import { API } from '../../api/config';

interface HistoryItem {
  id: number; title: string; summary: string; view_count: number;
  is_pest: number; category_name: string; browsed_at: string;
}

export default function BrowseHistory() {
  const [list, setList] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = () => {
    const openid = Taro.getStorageSync('openid') || '';
    if (!openid) { setLoading(false); return; }
    Taro.request({
      url: API.knowledgeHistory,
      data: { openid, page: 1, page_size: 50 },
    }).then((r: any) => {
      if (r.data?.success) setList(r.data.data);
    }).finally(() => setLoading(false));
  };

  useEffect(() => { fetchData(); }, []);

  const clearHistory = () => {
    const openid = Taro.getStorageSync('openid') || '';
    Taro.showModal({
      title: '确认清空',
      content: '确定要清空浏览历史吗？',
      success: (res) => {
        if (res.confirm) {
          Taro.request({
            url: API.knowledgeClearHistory,
            method: 'DELETE',
            data: { openid },
          }).then(() => {
            setList([]);
            Taro.showToast({ title: '已清空', icon: 'none' });
          });
        }
      },
    });
  };

  const goDetail = (id: number) => {
    const openid = Taro.getStorageSync('openid') || '';
    Taro.navigateTo({ url: `/pages/knowledge/detail?id=${id}&openid=${openid}` });
  };

  return (
    <View className='page-container'>
      <View className='page-header'>
        <View style='display:flex;align-items:center;justify-content:space-between'>
          <View style='display:flex;align-items:center;gap:8px' onClick={() => Taro.navigateBack()}>
            <Text style='font-size:18px'>{'‹'}</Text>
            <Text className='header-title'>浏览历史</Text>
          </View>
          {list.length > 0 && <Text style='font-size:13px;color:#999' onClick={clearHistory}>清空</Text>}
        </View>
      </View>
      <View className='page-content'>
        {list.map((item) => (
          <View key={item.id} className='kb-list-item' onClick={() => goDetail(item.id)}>
            <Image src='../../assets/sprout.png' mode='aspectFit' style='width:36px;height:36px' />
            <View style='flex:1'>
              <Text className='kb-item-name'>{item.title}</Text>
              <Text className='kb-item-desc'>{item.summary?.slice(0, 30)}...</Text>
            </View>
            <Image src='../../assets/chevronright.png' mode='aspectFit' style='width:16px;height:16px' />
          </View>
        ))}
        {!loading && list.length === 0 && (
          <View className='empty-state' style='margin-top:60px'>
            <Text className='empty-title'>暂无浏览历史</Text>
            <Text className='empty-desc'>查看知识库详情会自动记录</Text>
          </View>
        )}
      </View>
    </View>
  );
}
