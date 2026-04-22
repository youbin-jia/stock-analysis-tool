import { useEffect, useState, useMemo } from 'react';
import ReactECharts from 'echarts-for-react';
import { Spin, Segmented, Card, Empty } from 'antd';
import axios from 'axios';
import { useTheme } from '../context/ThemeContext';

function StockChart({ stockCode, stockName }) {
  const { isDark } = useTheme();
  const [chartData, setChartData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState('all');
  const [frequency, setFrequency] = useState('d');

  const periodOptions = [
    { label: '1月', value: '1m' },
    { label: '3月', value: '3m' },
    { label: '6月', value: '6m' },
    { label: '1年', value: '1y' },
    { label: '全部', value: 'all' },
  ];

  const freqOptions = [
    { label: '日线', value: 'd' },
    { label: '周线', value: 'w' },
    { label: '月线', value: 'm' },
  ];

  useEffect(() => {
    fetchChartData();
  }, [stockCode, period, frequency]);

  const fetchChartData = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`/api/stocks/history/${stockCode}`, {
        params: { period, frequency }
      });
      setChartData(response.data);
    } catch (error) {
      console.error('获取历史数据失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const upColor = isDark ? '#ff4d4f' : '#d93026';
  const downColor = isDark ? '#73d13d' : '#238636';
  const gridColor = isDark ? '#2a2a2a' : '#f0f0f0';
  const axisColor = isDark ? '#737373' : '#888888';
  const textColor = isDark ? '#e8e8e8' : '#333333';

  const option = useMemo(() => {
    if (!chartData || chartData.length === 0) return null;

    const dates = chartData.map((item) => item.date);
    const firstPrice = chartData[0].open;
    const lastPrice = chartData[chartData.length - 1].close;
    const isUp = lastPrice >= firstPrice;

    return {
      animation: false,
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' },
        backgroundColor: isDark ? 'rgba(30,30,30,0.95)' : 'rgba(255,255,255,0.95)',
        borderColor: isDark ? '#444' : '#eee',
        textStyle: { color: textColor },
      },
      legend: {
        data: ['K线', '成交量'],
        top: 8,
        textStyle: { color: axisColor },
      },
      grid: [
        { left: '8%', right: '6%', top: 48, height: '52%' },
        { left: '8%', right: '6%', top: '68%', height: '16%' },
      ],
      xAxis: [
        {
          type: 'category',
          data: dates,
          scale: true,
          boundaryGap: false,
          axisLine: { onZero: false, lineStyle: { color: gridColor } },
          axisLabel: { color: axisColor, fontSize: 11 },
          splitLine: { show: false },
          min: 'dataMin',
          max: 'dataMax',
        },
        {
          type: 'category',
          gridIndex: 1,
          data: dates,
          scale: true,
          boundaryGap: false,
          axisLine: { onZero: false, lineStyle: { color: gridColor } },
          axisTick: { show: false },
          splitLine: { show: false },
          axisLabel: { show: false },
          min: 'dataMin',
          max: 'dataMax',
        },
      ],
      yAxis: [
        {
          scale: true,
          axisLine: { show: false },
          axisTick: { show: false },
          splitLine: { lineStyle: { color: gridColor } },
          axisLabel: { color: axisColor, fontSize: 11 },
        },
        {
          scale: true,
          gridIndex: 1,
          splitNumber: 2,
          axisLabel: { show: false },
          axisLine: { show: false },
          axisTick: { show: false },
          splitLine: { show: false },
        },
      ],
      dataZoom: [
        {
          type: 'inside',
          xAxisIndex: [0, 1],
          start: 0,
          end: 100,
        },
        {
          show: true,
          xAxisIndex: [0, 1],
          type: 'slider',
          top: '88%',
          height: 20,
          start: 0,
          end: 100,
          borderColor: gridColor,
          fillerColor: isDark ? 'rgba(74,163,255,0.15)' : 'rgba(22,119,255,0.08)',
          handleStyle: { color: isDark ? '#4aa3ff' : '#1677ff' },
          textStyle: { color: axisColor },
        },
      ],
      series: [
        {
          name: 'K线',
          type: 'candlestick',
          data: chartData.map((item) => [item.open, item.close, item.low, item.high]),
          itemStyle: {
            color: isUp ? upColor : downColor,
            color0: isUp ? downColor : upColor,
            borderColor: isUp ? upColor : downColor,
            borderColor0: isUp ? downColor : upColor,
          },
        },
        {
          name: '成交量',
          type: 'bar',
          xAxisIndex: 1,
          yAxisIndex: 1,
          data: chartData.map((item) => item.volume),
          itemStyle: {
            color: (params) => {
              const item = chartData[params.dataIndex];
              return item.close >= item.open ? upColor : downColor;
            },
          },
        },
      ],
    };
  }, [chartData, isDark, upColor, downColor, gridColor, axisColor, textColor]);

  if (loading) {
    return (
      <Card style={{ borderRadius: 12, background: 'var(--bg-card)' }}>
        <div style={{ display: 'flex', justifyContent: 'center', padding: 80 }}>
          <Spin size="large" />
        </div>
      </Card>
    );
  }

  if (!chartData || chartData.length === 0) {
    return (
      <Card style={{ borderRadius: 12, background: 'var(--bg-card)' }}>
        <Empty description="暂无K线数据" style={{ padding: 60 }} />
      </Card>
    );
  }

  return (
    <Card style={{ borderRadius: 12, background: 'var(--bg-card)' }} styles={{ body: { padding: '16px 20px' } }}>
      <div style={{ display: 'flex', gap: 12, marginBottom: 12, flexWrap: 'wrap' }}>
        <Segmented
          options={periodOptions}
          value={period}
          onChange={setPeriod}
        />
        <Segmented
          options={freqOptions}
          value={frequency}
          onChange={setFrequency}
        />
      </div>
      <ReactECharts option={option} style={{ height: 480 }} />
    </Card>
  );
}

export default StockChart;
