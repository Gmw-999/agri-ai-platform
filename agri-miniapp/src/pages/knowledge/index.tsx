import { View, Text, Image, Input, ScrollView } from '@tarojs/components';
import Taro from '@tarojs/taro';
import { useState, useEffect } from 'react';
import { API } from '../../api/config';

interface Category {
  id: number; name: string; icon: string; sort_order: number;
}
interface KnowledgeItem {
  id: number; title: string; cover_image: string; summary: string;
  view_count: number; is_pest: number; category_name: string;
}

export default function KnowledgeBase() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [activeCat, setActiveCat] = useState<number | null>(null);
  const [list, setList] = useState<KnowledgeItem[]>([]);
  const [search, setSearch] = useState('');
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    Taro.request({ url: API.knowledgeCategories }).then((r: any) => {
      if (r.data?.success) {
        const cats = r.data.data as Category[];
        setCategories(cats);
        if (cats.length) setActiveCat(cats[0].id);
      }
    });
  }, []);

  useEffect(() => {
    fetchList();
  }, [activeCat, search]);

  const fetchList = (pg = 1) => {
    setLoading(true);
    Taro.request({
      url: API.knowledgeList,
      data: {
        category_id: search ? undefined : activeCat,
        keyword: search || '',
        page: pg,
        page_size: 20,
      },
    }).then((r: any) => {
      if (r.data?.success) {
        setList(pg === 1 ? r.data.data : [...list, ...r.data.data]);
        setTotal(r.data.total);
        setPage(pg);
      }
    }).finally(() => setLoading(false));
  };

  const handleSearch = (e: any) => {
    setSearch(e.detail.value);
    setPage(1);
  };

  const goDetail = (id: number) => {
    const openid = Taro.getStorageSync('openid') || '';
    Taro.navigateTo({ url: `/pages/knowledge/detail?id=${id}&openid=${openid}` });
  };

  return (
    <View className='page-container'>
      <View className='page-content'>
        {/* Search */}
        <View className='kb-search'>
          <Image src='../../assets/search.png' mode='aspectFit' style='width:18px;height:18px' />
          <Input
            className='kb-search-input'
            placeholder='搜索作物/病害名称'
            value={search}
            onInput={handleSearch}
            confirmType='search'
          />
          <Text style='font-size:13px;color:#27AE60;flex-shrink:0' onClick={() => Taro.navigateTo({ url: '/pages/knowledge/favorites' })}>收藏</Text>
          <Text style='font-size:13px;color:#27AE60;flex-shrink:0' onClick={() => Taro.navigateTo({ url: '/pages/knowledge/history' })}>历史</Text>
        </View>

        {/* Category Tabs */}
        {!search && (
          <ScrollView scrollX className='kb-categories' showScrollbar={false}>
            {categories.map((cat) => (
              <View
                key={cat.id}
                className={`kb-cat-tab ${activeCat === cat.id ? 'active' : ''}`}
                onClick={() => { setActiveCat(cat.id); setPage(1); }}
              >
                <Text>{cat.name}</Text>
              </View>
            ))}
          </ScrollView>
        )}

        {/* Knowledge List */}
        <View className='kb-list'>
          {list.map((item) => (
            <View key={item.id} className='kb-list-item' onClick={() => goDetail(item.id)}>
              <Image src={item.cover_image || '../../assets/sprout.png'} mode='aspectFit' style='width:40px;height:40px;border-radius:8px' />
              <View style='flex:1'>
                <Text className='kb-item-name'>
                  {item.title}
                  {item.is_pest === 1 && <Text style='font-size:10px;color:#e74c3c;background:#fde8e8;padding:1px 6px;border-radius:4px;margin-left:6px'>虫害</Text>}
                </Text>
                <Text className='kb-item-desc'>{item.summary?.slice(0, 40)}...</Text>
              </View>
              <Image src='../../assets/chevronright.png' mode='aspectFit' style='width:16px;height:16px' />
            </View>
          ))}
        </View>

        {!loading && list.length === 0 && (
          <View className='empty-state' style='margin-top:60px'>
            <Image src='../../assets/searchx.png' mode='aspectFit' style='width:64px;height:64px;margin-bottom:16px' />
            <Text className='empty-title'>未找到相关病虫害</Text>
            <Text className='empty-desc'>试试换个关键词</Text>
            <View className='primary-btn' onClick={() => Taro.switchTab({ url: '/pages/ai-chat/index' })}>
              <Text>咨询 AI 助手</Text>
            </View>
          </View>
        )}

        {list.length < total && (
          <View className='load-more' onClick={() => fetchList(page + 1)}>
            <Text style='color:#27AE60;font-size:14px'>加载更多</Text>
          </View>
        )}
      </View>
    </View>
  );
}
