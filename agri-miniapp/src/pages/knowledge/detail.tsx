import { View, Text, Image, ScrollView } from '@tarojs/components';
import Taro from '@tarojs/taro';
import { useState, useEffect } from 'react';
import { API } from '../../api/config';

interface Drug {
  name: string; usage: string; image_url: string; purchase_url: string;
}
interface DetailData {
  id: number; title: string; summary: string; symptoms: string;
  cause: string; prevention: string; treatment: string; drugs: Drug[];
  tags: string; view_count: number; is_pest: number; category_name: string;
  cover_image: string;
}

export default function KnowledgeDetail() {
  const params = Taro.getCurrentInstance().router?.params || {};
  const id = Number(params.id || 0);
  const openid = params.openid || '';
  const [data, setData] = useState<DetailData | null>(null);
  const [favorited, setFavorited] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    Taro.request({
      url: API.knowledgeDetail,
      data: { id, openid },
    }).then((r: any) => {
      if (r.data?.success) setData(r.data.data);
    }).finally(() => setLoading(false));

    if (openid) {
      Taro.request({
        url: API.knowledgeFavCheck,
        data: { openid, knowledge_id: id },
      }).then((r: any) => {
        if (r.data?.success) setFavorited(r.data.data.favorited);
      });
    }
  }, [id]);

  const toggleFav = () => {
    if (!openid) { Taro.showToast({ title: '请先登录', icon: 'none' }); return; }
    Taro.request({
      url: API.knowledgeFavorite,
      method: 'POST',
      data: { openid, knowledge_id: id },
    }).then((r: any) => {
      if (r.data?.success) {
        setFavorited(r.data.data.favorited);
        Taro.showToast({ title: r.data.data.message, icon: 'none' });
      }
    });
  };

  const askAI = () => {
    Taro.switchTab({ url: '/pages/ai-chat/index' });
  };

  if (loading) return <View className='page-container'><View className='page-content'><Text style='color:#999'>加载中...</Text></View></View>;
  if (!data) return <View className='page-container'><View className='page-content'><Text>条目不存在</Text></View></View>;

  const renderSection = (title: string, content: string) => {
    if (!content) return null;
    return (
      <View className='section-card' style='margin-bottom:12px'>
        <Text className='section-title'>{title}</Text>
        <Text style='font-size:14px;color:#333;line-height:1.8;white-space:pre-wrap'>{content}</Text>
      </View>
    );
  };

  return (
    <View className='page-container'>
      <ScrollView scrollY style='height:100vh'>
        <View style='padding:12px 16px;padding-bottom:80px'>
          {/* Header */}
          <View style='margin-bottom:16px'>
            <View style='display:flex;align-items:center;gap:8px;margin-bottom:4px'>
              <Text className='section-title' style='font-size:20px'>{data.title}</Text>
              {data.is_pest === 1 && <Text style='font-size:11px;color:#e74c3c;background:#fde8e8;padding:2px 8px;border-radius:4px'>虫害</Text>}
              {data.is_pest === 0 && <Text style='font-size:11px;color:#27AE60;background:#e8f8e8;padding:2px 8px;border-radius:4px'>病害</Text>}
            </View>
            <Text style='font-size:12px;color:#999'>{data.category_name} · {data.view_count}次浏览</Text>
          </View>

          {/* Summary */}
          <View className='section-card' style='margin-bottom:12px;background:#f0faf0'>
            <Text style='font-size:14px;color:#333;line-height:1.7'>{data.summary}</Text>
          </View>

          {renderSection('症状特征', data.symptoms)}
          {renderSection('发病原因', data.cause)}
          {renderSection('预防措施', data.prevention)}
          {renderSection('防治方法', data.treatment)}

          {/* Drugs */}
          {data.drugs && data.drugs.length > 0 && (
            <View className='section-card' style='margin-bottom:12px'>
              <Text className='section-title'>推荐用药</Text>
              {data.drugs.map((d, i) => (
                <View key={i} style='padding:10px 0;border-bottom:1px solid #f0f0f0'>
                  <Text style='font-size:14px;font-weight:500;color:#333'>{d.name}</Text>
                  <Text style='font-size:12px;color:#666;margin-top:4px'>用法：{d.usage}</Text>
                  {d.purchase_url && (
                    <Text style='font-size:12px;color:#27AE60;margin-top:4px' onClick={() => Taro.setClipboardData({ data: d.purchase_url! })}>
                      复制购买链接
                    </Text>
                  )}
                </View>
              ))}
            </View>
          )}

          {/* Tags */}
          {data.tags && (
            <View style='display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px'>
              {data.tags.split(',').map((tag, i) => (
                <Text key={i} style='font-size:11px;color:#666;background:#f5f5f5;padding:3px 10px;border-radius:12px'>{tag.trim()}</Text>
              ))}
            </View>
          )}
        </View>
      </ScrollView>

      {/* Bottom Bar */}
      <View style='position:fixed;bottom:0;left:0;right:0;background:white;border-top:1px solid #f0f0f0;padding:10px 16px;display:flex;gap:10px;padding-bottom:env(safe-area-inset-bottom,10px)'>
        <View
          style={`flex:1;padding:10px 0;border-radius:8px;text-align:center;${favorited ? 'background:#f0faf0' : 'background:#f5f5f5'}`}
          onClick={toggleFav}
        >
          <Text style={`font-size:14px;${favorited ? 'color:#27AE60' : 'color:#666'}`}>{favorited ? '已收藏' : '收藏'}</Text>
        </View>
        <View
          style='flex:2;padding:10px 0;border-radius:8px;text-align:center;background:#27AE60'
          onClick={askAI}
        >
          <Text style='font-size:14px;color:white;font-weight:500'>咨询 AI 防治</Text>
        </View>
      </View>
    </View>
  );
}
