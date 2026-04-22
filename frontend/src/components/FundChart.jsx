import { useEffect, useState, useMemo } from 'react';
import ReactECharts from 'echarts-for-react';
import { Spin, Segmented, Card, Empty } from 'antd';
import axios from 'axios';
import { useTheme } from '../context/ThemeContext';

function FundChart({ fundCode, fundName }) {
  const { isDark } = useTheme();
  const [chartData, setChartData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState('all');
  const [viewMode, setViewMode] = useState('return'); // 'return' = 累计收益率, 'nav' = 单位净值

  const periodOptions = [
    { label: '1月', value: '1m' },
    { label: '3月', value: '3m' },
    { label: '6月', value: '6m' },
    { label: '1年', value: '1y' },
    { label: '全部', value: 'all' },
  ];

  const viewOptions = [
    { label: '累计收益率', value: 'return' },
    { label: '单位净值', value: 'nav' },
  ];

  useEffect(() => {
    fetchChartData();
  }, [fundCode, period]);

  const fetchChartData = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`/api/funds/history/${fundCode}`, {
        params: { period }
      });
      setChartData(response.data);
    } catch (error) {
      console.error('获取基金历史数据失败:', error);
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
    const isReturnMode = viewMode === 'return';

    // 复权净值优先，缺失回退到单位净值
    const values = chartData.map((item) => item.adjusted_nav ?? item.nav);
    const firstValue = values[0];
    const lastValue = values[values.length - 1];
    const isUp = lastValue >= firstValue;
    const lineColor = isUp ? upColor : downColor;

    const displayValues = isReturnMode
      ? values.map((v) => ((v - firstValue) / firstValue) * 100)
      : values;

    const yAxisName = isReturnMode ? '收益率 (%)' : '净值';
    const seriesName = isReturnMode ? '累计收益率' : '单位净值';

    return {
      animation: false,
      tooltip: {
        trigger: 'axis',
        backgroundColor: isDark ? 'rgba(30,30,30,0.95)' : 'rgba(255,255,255,0.95)',
        borderColor: isDark ? '#444' : '#eee',
        textStyle: { color: textColor },
        formatter: (params) => {
          const p = params[0];
          const item = chartData[p.dataIndex];
          const change = item.change_percent;
          const changeColor = change >= 0 ? upColor : downColor;
          const sign = change >= 0 ? '+' : '';
          const adjustedNav = item.adjusted_nav ?? item.nav;
          const cumReturn = ((adjustedNav - firstValue) / firstValue) * 100;

          return `
            <div style="font-weight:600;margin-bottom:4px">${p.axisValue}</div>
            <div style="display:flex;align-items:center;gap:6px">
              <span style="flex:1">单位净值</span>
              <span style="font-weight:600">${item.nav.toFixed(4)}</span>
            </div>
            <div style="display:flex;align-items:center;gap:6px">
              <span style="flex:1">复权净值</span>
              <span style="font-weight:600">${adjustedNav.toFixed(4)}</span>
            </div>
            <div style="display:flex;align-items:center;gap:6px">
              <span style="flex:1">累计收益</span>
              <span style="font-weight:600;color:${cumReturn >= 0 ? upColor : downColor}">${cumReturn >= 0 ? '+' : ''}${cumReturn.toFixed(2)}%</span>
            </div>
            <div style="display:flex;align-items:center;gap:6px">
              <span style="flex:1">日涨跌幅</span>
              <span style="font-weight:600;color:${changeColor}">${sign}${change.toFixed(2)}%</span>
            </div>
          `;
        },
      },
      legend: {
        data: [seriesName],
        top: 8,
        textStyle: { color: axisColor },
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '10%',
        top: 48,
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: dates,
        boundaryGap: false,
        axisLine: { lineStyle: { color: gridColor } },
        axisLabel: { color: axisColor, fontSize: 11 },
      },
      yAxis: {
        type: 'value',
        scale: true,
        name: yAxisName,
        nameTextStyle: { color: axisColor, fontSize: 11 },
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: { lineStyle: { color: gridColor } },
        axisLabel: {
          color: axisColor,
          fontSize: 11,
          formatter: isReturnMode ? '{value}%' : '{value}',
        },
      },
      dataZoom: [
        { type: 'inside', start: 0, end: 100 },
        {
          type: 'slider',
          bottom: 0,
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
          name: seriesName,
          type: 'line',
          data: displayValues,
          smooth: true,
          symbol: 'none',
          lineStyle: { width: 2.5, color: lineColor },
          itemStyle: { color: lineColor },
          areaStyle: {
            color: {
              type: 'linear',
              x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [
                { offset: 0, color: isUp ? 'rgba(217,48,38,0.15)' : 'rgba(35,134,54,0.15)' },
                { offset: 1, color: isUp ? 'rgba(217,48,38,0.01)' : 'rgba(35,134,54,0.01)' },
              ],
            },
          },
        },
      ],
    };
  }, [chartData, isDark, upColor, downColor, gridColor, axisColor, textColor, viewMode]);

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
        <Empty description="暂无净值数据" style={{ padding: 60 }} />
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
          options={viewOptions}
          value={viewMode}
          onChange={setViewMode}
        />
      </div>
      <ReactECharts option={option} style={{ height: 480 }} />
    </Card>
  );
}

export default FundChart;
