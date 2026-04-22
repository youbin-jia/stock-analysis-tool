import { useState, useEffect, useMemo } from 'react';
import ReactECharts from 'echarts-for-react';
import {
  Spin,
  Card,
  Segmented,
  Tag,
  Button,
  Empty,
  AutoComplete,
  Input,
} from 'antd';
import {
  PlusOutlined,
  SearchOutlined,
} from '@ant-design/icons';
import axios from 'axios';
import { useTheme } from '../context/ThemeContext';

const COLORS = [
  '#1677ff', '#52c41a', '#faad14', '#f5222d',
  '#722ed1', '#eb2f96', '#13c2c2', '#fa541c',
];

const COLORS_DARK = [
  '#4aa3ff', '#73d13d', '#ffc53d', '#ff7875',
  '#b37feb', '#ff85c0', '#5cdbd3', '#ff9c6e',
];

function FundComparison({ initialCodes = [] }) {
  const { isDark } = useTheme();
  const themeColors = isDark ? COLORS_DARK : COLORS;
  const gridColor = isDark ? '#2a2a2a' : '#f0f0f0';
  const axisColor = isDark ? '#737373' : '#888888';
  const textColor = isDark ? '#e8e8e8' : '#333333';

  const [selectedFunds, setSelectedFunds] = useState([]);
  const [chartData, setChartData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [period, setPeriod] = useState('all');
  const [normalize, setNormalize] = useState(true);
  const [searchOptions, setSearchOptions] = useState([]);
  const [searchLoading, setSearchLoading] = useState(false);

  const periodOptions = [
    { label: '1月', value: '1m' },
    { label: '3月', value: '3m' },
    { label: '6月', value: '6m' },
    { label: '1年', value: '1y' },
    { label: '全部', value: 'all' },
  ];

  useEffect(() => {
    if (initialCodes.length > 0) {
      const initFunds = initialCodes.map((code) => ({ code, name: code }));
      setSelectedFunds(initFunds);
    }
  }, []);

  useEffect(() => {
    if (selectedFunds.length > 0) {
      fetchComparisonData();
    } else {
      setChartData(null);
    }
  }, [period, normalize, selectedFunds]);

  const fetchComparisonData = async () => {
    if (selectedFunds.length === 0) return;

    setLoading(true);
    try {
      const codes = selectedFunds.map((s) => s.code).join(',');
      const response = await axios.get('/api/funds/comparison', {
        params: { codes, period, normalize },
      });
      setChartData(response.data);
    } catch (error) {
      console.error('获取基金对比数据失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async (value) => {
    if (!value || value.length < 1) {
      setSearchOptions([]);
      return;
    }
    setSearchLoading(true);
    try {
      const res = await axios.get('/api/funds/search', { params: { keyword: value } });
      setSearchOptions(
        res.data.map((item) => ({
          value: item.code,
          label: (
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ fontWeight: 500 }}>{item.name}</span>
              <span style={{ color: '#888', fontSize: 12 }}>{item.code}</span>
            </div>
          ),
        }))
      );
    } catch (e) {
      console.error(e);
    } finally {
      setSearchLoading(false);
    }
  };

  const handleAddFund = async (code) => {
    if (!code || selectedFunds.some((s) => s.code === code)) return;
    try {
      const res = await axios.get(`/api/funds/info/${code}`);
      setSelectedFunds((prev) => [...prev, res.data]);
    } catch {
      // ignore
    }
  };

  const handleRemoveFund = (code) => {
    setSelectedFunds(selectedFunds.filter((s) => s.code !== code));
  };

  const option = useMemo(() => {
    if (!chartData?.funds?.length) return null;

    const dates = chartData.funds[0]?.data.map((item) => item.date) || [];
    const series = chartData.funds.map((fund, index) => ({
      name: fund.name,
      type: 'line',
      data: fund.data.map((item) => item.value),
      smooth: true,
      symbol: 'none',
      lineStyle: { width: 2.5, color: themeColors[index % themeColors.length] },
      itemStyle: { color: themeColors[index % themeColors.length] },
      emphasis: { focus: 'series' },
    }));

    return {
      animation: false,
      tooltip: {
        trigger: 'axis',
        backgroundColor: isDark ? 'rgba(30,30,30,0.95)' : 'rgba(255,255,255,0.95)',
        borderColor: isDark ? '#444' : '#eee',
        textStyle: { color: textColor },
        formatter: (params) => {
          let result = `<div style="font-weight:600;margin-bottom:4px">${params[0].axisValue}</div>`;
          params.forEach((param) => {
            const value = param.value.toFixed(2);
            const unit = normalize ? '%' : '元';
            result += `<div style="display:flex;align-items:center;gap:6px;margin:2px 0">
              <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${param.color}"></span>
              <span style="flex:1">${param.seriesName}</span>
              <span style="font-weight:600">${value}${unit}</span>
            </div>`;
          });
          return result;
        },
      },
      legend: {
        data: chartData.funds.map((s) => s.name),
        top: 8,
        textStyle: { color: axisColor },
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        top: 52,
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: dates,
        axisLine: { lineStyle: { color: gridColor } },
        axisLabel: { color: axisColor, fontSize: 11 },
      },
      yAxis: {
        type: 'value',
        name: normalize ? '收益率 (%)' : '净值 (元)',
        nameTextStyle: { color: axisColor, fontSize: 11 },
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: { lineStyle: { color: gridColor } },
        axisLabel: {
          color: axisColor,
          fontSize: 11,
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
      series,
    };
  }, [chartData, isDark, themeColors, gridColor, axisColor, textColor, normalize]);

  if (selectedFunds.length === 0) {
    return (
      <Card style={{ borderRadius: 12, background: 'var(--bg-card)' }}>
        <div style={{ padding: '40px 0', textAlign: 'center' }}>
          <Empty description="请添加基金进行对比">
            <div style={{ marginTop: 16, width: 300, margin: '16px auto' }}>
              <AutoComplete
                style={{ width: '100%' }}
                options={searchOptions}
                onSearch={handleSearch}
                onSelect={handleAddFund}
                loading={searchLoading}
              >
                <Input
                  placeholder="搜索基金代码或名称"
                  prefix={<SearchOutlined style={{ color: '#bfbfbf' }} />}
                  suffix={
                    <Button
                      type="primary"
                      size="small"
                      icon={<PlusOutlined />}
                      style={{ borderRadius: 4 }}
                    >
                      添加
                    </Button>
                  }
                />
              </AutoComplete>
            </div>
          </Empty>
        </div>
      </Card>
    );
  }

  return (
    <Card style={{ borderRadius: 12, background: 'var(--bg-card)' }} styles={{ body: { padding: '16px 20px' } }}>
      {/* 控制栏 */}
      <div
        style={{
          display: 'flex',
          gap: 12,
          marginBottom: 16,
          flexWrap: 'wrap',
          alignItems: 'center',
        }}
      >
        <AutoComplete
          style={{ width: 240 }}
          options={searchOptions}
          onSearch={handleSearch}
          onSelect={handleAddFund}
          loading={searchLoading}
        >
          <Input
            placeholder="搜索添加基金"
            prefix={<SearchOutlined style={{ color: '#bfbfbf' }} />}
            style={{ borderRadius: 6 }}
          />
        </AutoComplete>

        <Segmented
          options={periodOptions}
          value={period}
          onChange={setPeriod}
        />

        <Segmented
          options={[
            { label: '收益率', value: true },
            { label: '原始净值', value: false },
          ]}
          value={normalize}
          onChange={setNormalize}
        />
      </div>

      {/* 已选基金标签 */}
      <div style={{ marginBottom: 16, display: 'flex', flexWrap: 'wrap', gap: 8 }}>
        {selectedFunds.map((fund, idx) => (
          <Tag
            key={fund.code}
            color={themeColors[idx % themeColors.length]}
            closable
            onClose={() => handleRemoveFund(fund.code)}
            style={{ fontSize: 13, padding: '4px 10px', borderRadius: 6 }}
          >
            {fund.name} ({fund.code})
          </Tag>
        ))}
      </div>

      {/* 图表 */}
      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 80 }}>
          <Spin size="large" />
        </div>
      ) : chartData?.funds?.length > 0 ? (
        <ReactECharts option={option} style={{ height: 480 }} />
      ) : (
        <Empty description="暂无对比数据" style={{ padding: 60 }} />
      )}
    </Card>
  );
}

export default FundComparison;
