import { View, Text, Image, Input } from '@tarojs/components';
import Taro from '@tarojs/taro';
import { useState, useEffect } from 'react';
import { agentChat } from '../../api';
import { API } from '../../api/config';

interface WeatherNow {
  temp: string;
  text: string;
  humidity: string;
  windSpeed: string;
  windDir: string;
  icon?: string;
  feelsLike?: string;
}

interface WeatherDaily {
  fxDate: string;
  textDay: string;
  tempMin: string;
  tempMax: string;
  precip?: string;
  iconDay?: string;
}

interface WeatherData {
  city: string;
  now: WeatherNow;
  daily: WeatherDaily[];
  warning: any[];
  update_time: string;
}

export default function Weather() {
  const [loading, setLoading] = useState(false);
  const [advice, setAdvice] = useState('');
  const [weather, setWeather] = useState<WeatherData | null>(null);
  const [location, setLocation] = useState('湖南省长沙市');
  const [showInput, setShowInput] = useState(false);
  const [locInput, setLocInput] = useState(location);

  const dayLabels = ['今', '明', '三', '四', '五', '六', '日'];

  const fetchWeatherData = async (loc: string) => {
    try {
      const res = await Taro.request({
        url: `${API.weather}?region=${encodeURIComponent(loc)}`,
        method: 'GET',
        timeout: 60000,
      });
      if ((res.data as any)?.success) {
        setWeather((res.data as any).data as WeatherData);
      } else {
        console.warn('[天气] 接口返回失败:', res.data);
      }
    } catch (e) {
      console.warn('[天气] 请求异常:', e);
    }
  };

  const fetchAdvice = async (loc: string) => {
    setLoading(true);
    setAdvice('');
    try {
      const reply = await agentChat({
        message: `${loc}今天天气怎么样，适合打药吗`,
        session_id: `weather_${Date.now()}`,
      });
      setAdvice(reply);
    } catch {
      Taro.showToast({ title: '获取农事建议失败', icon: 'none' });
    } finally {
      setLoading(false);
    }
  };

  const fetchAll = async (loc: string) => {
    await Promise.all([fetchWeatherData(loc), fetchAdvice(loc)]);
  };

  const handleLocChange = () => {
    const loc = locInput.trim() || '湖南省长沙市';
    setLocation(loc);
    setShowInput(false);
    fetchAll(loc);
  };

  useEffect(() => {
    fetchAll(location);
  }, []);

  const now = weather?.now;
  const daily = weather?.daily || [];

  // Map weather types to existing local assets
  const getIcon = (text?: string) => {
    if (!text) return '../../assets/sun.png';
    if (text.includes('晴')) return '../../assets/sun.png';
    if (text.includes('多云') || text.includes('阴')) return '../../assets/cloudsun.png';
    if (text.includes('雨') || text.includes('雷') || text.includes('阵')) return '../../assets/cloudrain.png';
    return '../../assets/sun.png';
  };

  const getDayDesc = (text: string) => {
    // Shorten weather descriptions
    const m: Record<string, string> = {
      '晴': '晴', '多云': '多云', '阴': '阴', '小雨': '小雨',
      '中雨': '中雨', '大雨': '大雨', '暴雨': '暴雨', '雷阵雨': '雷雨',
      '阵雨': '阵雨', '小雪': '小雪', '中雪': '中雪', '大雪': '大雪',
      '雾': '雾', '霾': '霾', '扬沙': '扬沙',
    };
    for (const [k, v] of Object.entries(m)) {
      if (text.includes(k)) return v;
    }
    return text.slice(0, 2);
  };

  const getSeverity = () => {
    if (!weather?.warning?.length) return null;
    const w = weather.warning[0] as any;
    const isRed = w.level === '红色' || w.severity === 'Extreme';
    const isOrange = w.level === '橙色' || w.severity === 'Severe';
    const isYellow = w.level === '黄色' || w.severity === 'Moderate';
    return {
      title: w.title || '',
      text: w.text || '',
      color: isRed ? '#e74c3c' : isOrange ? '#f39c12' : isYellow ? '#f1c40f' : '#3498db',
    };
  };
  const warning = getSeverity();

  return (
    <View className='page-container'>
      <View className='page-content'>
        {/* Location */}
        {showInput ? (
          <View style='display:flex;gap:8px;align-items:center;margin-bottom:12px'>
            <Input
              style='flex:1;padding:8px 12px;background:white;border-radius:8px;font-size:14px'
              placeholder='输入地区名称'
              value={locInput}
              onInput={(e) => setLocInput(e.detail.value)}
              onConfirm={handleLocChange}
            />
            <View
              style='padding:8px 16px;background:#2e8b57;color:white;border-radius:8px;font-size:14px'
              onClick={handleLocChange}
            >
              <Text>确定</Text>
            </View>
          </View>
        ) : (
          <View className='location-bar' onClick={() => setShowInput(true)}>
            <Image src='../../assets/mappin.png' mode='aspectFit' />
            <Text>{weather?.city || location}</Text>
            <Image src='../../assets/chevrondown.png' mode='aspectFit' />
          </View>
        )}

        {/* Current Weather */}
        <View className='current-weather'>
          <View className='temp-display'>
            <View>
              <Text className='temp-value'>{now ? `${now.temp}°C` : '--°C'}</Text>
              <Text className='temp-desc'>{now?.text || '加载中'}</Text>
            </View>
            <Image
              src={now?.text ? getIcon(now.text) : '../../assets/sun.png'}
              mode='aspectFit'
              style='width:64px;height:64px'
            />
          </View>
          <View className='weather-details'>
            <View className='wd-item'>
              <Image src='../../assets/wind.png' mode='aspectFit' />
              <Text>{now ? `${now.windSpeed}km/h` : '--级'}</Text>
            </View>
            <View className='wd-item'>
              <Image src='../../assets/droplets.png' mode='aspectFit' />
              <Text>{now ? `${now.humidity}%` : '--%'}</Text>
            </View>
          </View>
          <View className='farm-status'>
            <Image src='../../assets/checkcircle.png' mode='aspectFit' style='width:18px;height:18px' />
            <Text>{now ? `体感 ${now.feelsLike || now.temp}°C · ${weather?.update_time || ''}` : '查询中...'}</Text>
          </View>
        </View>

        {/* Warning Alert */}
        {warning && (
          <View className='section-card' style={`border-left:4px solid ${warning.color};margin-bottom:12px`}>
            <View className='section-title-row'>
              <Image src='../../assets/trianglealert.png' mode='aspectFit' style='width:18px;height:18px' />
              <Text className='section-title'>{warning.title}</Text>
            </View>
            <Text style='font-size:12px;color:#666;margin-top:4px'>{warning.text.slice(0, 100)}...</Text>
          </View>
        )}

        {/* 7-Day Forecast */}
        <View className='section-card'>
          <Text className='section-title'>未来7天预报</Text>
          <View className='forecast-grid'>
            {(daily.length > 0 ? daily : Array(7).fill(null)).map((d, i) => (
              <View key={i} className='forecast-day'>
                <Text className='fd-label'>{dayLabels[i] || `${i+1}`}</Text>
                <Image
                  src={d ? getIcon((d as any).textDay) : '../../assets/sun0.png'}
                  mode='aspectFit'
                  style='width:24px;height:24px'
                />
                <Text className='fd-temp'>{d ? `${(d as any).tempMax}°` : '--°'}</Text>
                {d && <Text style='font-size:10px;color:#999;margin-top:2px'>{getDayDesc((d as any).textDay)}</Text>}
              </View>
            ))}
          </View>
        </View>

        {/* Farming Advice */}
        {loading && (
          <View style='text-align:center;padding:24px'>
            <Text style='color:#999'>正在获取农事建议...</Text>
          </View>
        )}

        {advice && (
          <View className='section-card'>
            <View className='advice-header'>
              <Image src='../../assets/leaf0.png' mode='aspectFit' />
              <Text>农事操作建议</Text>
            </View>
            <View>
              {advice.split(/\d\./).filter(Boolean).map((point, i) => (
                <View key={i} className='advice-item'>
                  <View className='advice-bullet' />
                  <Text>{point.trim()}</Text>
                </View>
              ))}
            </View>
          </View>
        )}
      </View>
    </View>
  );
}
