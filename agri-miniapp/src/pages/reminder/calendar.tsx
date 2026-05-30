import { View, Text, ScrollView } from '@tarojs/components';
import Taro from '@tarojs/taro';
import { useState, useEffect } from 'react';
import { API } from '../../api/config';

export default function ReminderCalendar() {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [days, setDays] = useState<Array<{ date: string; count: number }>>([]);
  const [dayReminders, setDayReminders] = useState<any[]>([]);
  const [selectedDate, setSelectedDate] = useState('');
  const openid = Taro.getStorageSync('openid') || '';

  const fetchCalendar = (y: number, m: number) => {
    Taro.request({
      url: API.reminderCalendar,
      data: { openid, year: y, month: m },
    }).then((r: any) => {
      if (r.data?.success) setDays(r.data.data);
    });
  };

  const fetchDayReminders = (date: string) => {
    Taro.request({
      url: API.reminderList,
      data: { openid, date_from: date, date_to: date, page_size: 50 },
    }).then((r: any) => {
      if (r.data?.success) {
        setDayReminders(r.data.data);
        setSelectedDate(date);
      }
    });
  };

  useEffect(() => {
    fetchCalendar(year, month);
    const firstDay = `${year}-${String(month).padStart(2, '0')}-01`;
    fetchDayReminders(firstDay);
  }, [year, month]);

  // 当月第一天是星期几（0=日）
  const firstDayWeek = new Date(year, month - 1, 1).getDay();
  const weekHeaders = ['日', '一', '二', '三', '四', '五', '六'];

  const prevMonth = () => {
    if (month === 1) { setYear(year - 1); setMonth(12); }
    else setMonth(month - 1);
  };
  const nextMonth = () => {
    if (month === 12) { setYear(year + 1); setMonth(1); }
    else setMonth(month + 1);
  };

  return (
    <View className='page-container'>
      <View className='page-header'>
        <View style='display:flex;align-items:center;gap:8px' onClick={() => Taro.navigateBack()}>
          <Text style='font-size:18px'>{'‹'}</Text>
          <Text className='header-title'>农事日历</Text>
        </View>
      </View>
      <View className='page-content'>
        {/* Month Nav */}
        <View style='display:flex;align-items:center;justify-content:space-between;margin-bottom:16px'>
          <Text style='font-size:20px;font-weight:600;color:#333' onClick={prevMonth}>{'‹'}</Text>
          <Text style='font-size:18px;font-weight:600;color:#333'>{year}年{month}月</Text>
          <Text style='font-size:20px;font-weight:600;color:#333' onClick={nextMonth}>{'>'}</Text>
        </View>

        {/* Calendar Grid */}
        <View className='section-card' style='padding:12px'>
          <View style='display:grid;grid-template-columns:repeat(7,1fr);gap:4px;text-align:center;margin-bottom:8px'>
            {weekHeaders.map((w, i) => (
              <Text key={i} style='font-size:12px;color:#999;padding:4px 0'>{w}</Text>
            ))}
          </View>
          <View style='display:grid;grid-template-columns:repeat(7,1fr);gap:4px;text-align:center'>
            {/* Empty cells before first day */}
            {Array(firstDayWeek).fill(null).map((_, i) => (
              <View key={`e${i}`} style='padding:6px 0' />
            ))}
            {days.map((d, i) => {
              const dayNum = parseInt(d.date.split('-')[2], 10);
              const isToday = d.date === `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
              const isSelected = d.date === selectedDate;
              return (
                <View
                  key={i}
                  style={`padding:6px 0;align-items:center;border-radius:8px;${isSelected ? 'background:#27AE60' : ''}${isToday && !isSelected ? 'background:#e8f8e8' : ''}`}
                  onClick={() => fetchDayReminders(d.date)}
                >
                  <Text style={`font-size:14px;text-align:center;${isSelected ? 'color:white;font-weight:600' : isToday ? 'color:#27AE60;font-weight:600' : 'color:#333'}`}>{dayNum}</Text>
                  {d.count > 0 && (
                    <View style='width:6px;height:6px;border-radius:3px;background:#27AE60;margin:2px auto 0' />
                  )}
                </View>
              );
            })}
          </View>
        </View>

        {/* Day Reminders */}
        {selectedDate && (
          <View style='margin-top:12px'>
            <Text style='font-size:14px;font-weight:500;color:#333;margin-bottom:8px'>{selectedDate} 的农事安排</Text>
            {dayReminders.length === 0 && (
              <Text style='font-size:13px;color:#999;text-align:center;padding:20px'>当天无农事安排</Text>
            )}
            {dayReminders.map((item: any) => (
              <View key={item.id} className='section-card' style='margin-bottom:8px;padding:12px'>
                <Text style='font-size:14px;font-weight:500;color:#333'>{item.title}</Text>
                {item.content && <Text style='font-size:12px;color:#666;margin-top:4px'>{item.content}</Text>}
                <Text style='font-size:11px;color:#999;margin-top:4px'>{item.remind_time?.slice(0, 5)} · {item.remind_type}</Text>
              </View>
            ))}
          </View>
        )}
      </View>
    </View>
  );
}
