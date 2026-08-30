import { useEffect, useState, useMemo } from 'react';
import ReactECharts from 'echarts-for-react';
import { Spin, Segmented, Card, Empty } from 'antd';
import axios from 'axios';
import { useTheme } from '../context/ThemeContext';

function StockChart({ stockCode, stockName }) {
  const { isDark } = useTheme();
  const [chartData, setChartData] = useState(null);
  const [signalData, setSignalData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState('all');
  const [frequency, setFrequency] = useState('d');
  const [showSignals, setShowSignals] = useState(true);

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

  const signalOptions = [
    { label: '显示信号', value: true },
    { label: '隐藏信号', value: false },
  ];

  useEffect(() => {
    fetchChartData();
  }, [stockCode, period, frequency]);

  const fetchChartData = async () => {
    setLoading(true);
    try {
      // 策略接口失败不能让 K 线空白，所以单独 catch 掉
      const [histRes, sigRes] = await Promise.all([
        axios.get(`/api/stocks/history/${stockCode}`, {
          params: { period, frequency },
        }),
        axios
          .get(`/api/strategy/signals/${stockCode}`, {
            params: { period, frequency },
          })
          .catch(() => null),
      ]);
      setChartData(histRes.data);
      setSignalData(sigRes ? sigRes.data : null);
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
  // 信号色不能复用涨跌色：A股红涨绿跌，红色的"卖出"箭头无法阅读
  const buySignalColor = isDark ? '#4aa3ff' : '#1677ff';
  const sellSignalColor = isDark ? '#faad14' : '#d48806';

  const option = useMemo(() => {
    if (!chartData || chartData.length === 0) return null;

    const dates = chartData.map((item) => item.date);
    const firstPrice = chartData[0].open;
    const lastPrice = chartData[chartData.length - 1].close;
    const isUp = lastPrice >= firstPrice;

    const dateIndex = new Map(dates.map((d, idx) => [d, idx]));

    // 13 个策略在长周期下会堆出上千个标记（茅台全量 2400 根 K 线对应 1083 个），
    // 箭头互相重叠后 K 线完全不可读。密度超过 ~1/25 根时按 strength 取前 N 个，
    // 短周期（信号本就稀疏）不受影响。
    const MARKER_DENSITY = 25;
    const maxMarkers = Math.max(20, Math.round(dates.length / MARKER_DENSITY));
    const visibleMarkers = (() => {
      if (!showSignals || !signalData?.markers) return [];
      const inRange = signalData.markers.filter((m) => dateIndex.has(m.date));
      if (inRange.length <= maxMarkers) return inRange;
      return inRange
        .slice()
        .sort((a, b) => (b.strength || 0) - (a.strength || 0))
        .slice(0, maxMarkers);
    })();
    const hiddenMarkerCount =
      showSignals && signalData?.markers
        ? signalData.markers.filter((m) => dateIndex.has(m.date)).length -
          visibleMarkers.length
        : 0;

    const markers = visibleMarkers.map((m) => ({
      name: m.label,
      coord: [
        dateIndex.get(m.date),
        m.type === 'buy' ? m.price * 0.98 : m.price * 1.02,
      ],
      value: m.type === 'buy' ? 'B' : 'S',
      symbol: m.type === 'buy' ? 'triangle' : 'triangle',
      symbolRotate: m.type === 'buy' ? 0 : 180,
      symbolSize: 11 + (m.members?.length || 1) * 2,
      itemStyle: {
        color: m.type === 'buy' ? buySignalColor : sellSignalColor,
      },
      label: { show: false },
      signalName: m.strategy_name,
      memberNames: (m.member_names || []).join('、'),
      signalDate: m.date,
    }));

    return {
      animation: false,
      title: hiddenMarkerCount
        ? {
            // 静默截断会让人误以为图上就是全部信号，必须显式说明
            text: `信号密集，按强度显示前 ${markers.length} 个（另有 ${hiddenMarkerCount} 个未显示）`,
            right: '6%',
            top: 28,
            textStyle: {
              color: axisColor,
              fontSize: 11,
              fontWeight: 'normal',
            },
          }
        : undefined,
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross', link: [{ xAxisIndex: 'all' }] },
        backgroundColor: isDark ? 'rgba(30,30,30,0.95)' : 'rgba(255,255,255,0.95)',
        borderColor: isDark ? '#444' : '#eee',
        textStyle: { color: textColor },
      },
      legend: {
        data: ['K线', 'MA5', 'MA20', 'MA60', '成交量', 'DIF', 'DEA', 'MACD'],
        top: 8,
        textStyle: { color: axisColor },
      },
      grid: [
        { left: '8%', right: '6%', top: 48, height: '44%' },
        { left: '8%', right: '6%', top: '58%', height: '12%' },
        { left: '8%', right: '6%', top: '74%', height: '14%' },
      ],
      xAxis: [
        {
          type: 'category',
          data: dates,
          scale: true,
          boundaryGap: false,
          axisLine: { onZero: false, lineStyle: { color: gridColor } },
          axisLabel: { show: false },
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
        {
          type: 'category',
          gridIndex: 2,
          data: dates,
          scale: true,
          boundaryGap: false,
          axisLine: { onZero: false, lineStyle: { color: gridColor } },
          axisTick: { show: false },
          splitLine: { show: false },
          axisLabel: { color: axisColor, fontSize: 11 },
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
        {
          scale: true,
          gridIndex: 2,
          splitNumber: 2,
          axisLabel: { color: axisColor, fontSize: 10 },
          axisLine: { show: false },
          axisTick: { show: false },
          splitLine: { show: false },
        },
      ],
      dataZoom: [
        {
          type: 'inside',
          xAxisIndex: [0, 1, 2],
          start: 0,
          end: 100,
        },
        {
          show: true,
          xAxisIndex: [0, 1, 2],
          type: 'slider',
          top: '91%',
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
          markPoint: {
            silent: false,
            data: markers,
            tooltip: {
              formatter: (p) =>
                `${p.data.signalDate}<br/>` +
                `<b style="color:${p.data.value === 'B' ? buySignalColor : sellSignalColor}">` +
                `${p.data.value === 'B' ? '买入信号' : '卖出信号'}</b><br/>` +
                `${p.data.memberNames || p.data.signalName}`,
            },
          },
        },
        {
          name: 'MA5',
          type: 'line',
          data: chartData.map((item) => item.ma5 ?? null),
          showSymbol: false,
          lineStyle: { width: 1, color: '#f5a623' },
        },
        {
          name: 'MA20',
          type: 'line',
          data: chartData.map((item) => item.ma20 ?? null),
          showSymbol: false,
          lineStyle: { width: 1, color: '#4aa3ff' },
        },
        {
          name: 'MA60',
          type: 'line',
          data: chartData.map((item) => item.ma60 ?? null),
          showSymbol: false,
          lineStyle: { width: 1, color: '#b37feb' },
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
        {
          name: 'MACD',
          type: 'bar',
          xAxisIndex: 2,
          yAxisIndex: 2,
          data: chartData.map((item) => item.macd ?? null),
          itemStyle: {
            color: (params) => (params.value >= 0 ? upColor : downColor),
          },
        },
        {
          name: 'DIF',
          type: 'line',
          xAxisIndex: 2,
          yAxisIndex: 2,
          data: chartData.map((item) => item.dif ?? null),
          showSymbol: false,
          lineStyle: { width: 1, color: '#f5a623' },
        },
        {
          name: 'DEA',
          type: 'line',
          xAxisIndex: 2,
          yAxisIndex: 2,
          data: chartData.map((item) => item.dea ?? null),
          showSymbol: false,
          lineStyle: { width: 1, color: '#4aa3ff' },
        },
      ],
    };
  }, [chartData, signalData, showSignals, isDark, upColor, downColor, gridColor,
      axisColor, textColor, buySignalColor, sellSignalColor]);

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
        <Segmented
          options={signalOptions}
          value={showSignals}
          onChange={setShowSignals}
        />
      </div>
      <ReactECharts option={option} style={{ height: 620 }} notMerge />
    </Card>
  );
}

export default StockChart;
