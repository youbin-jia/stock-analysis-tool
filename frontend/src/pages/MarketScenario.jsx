import { useState, useEffect, useMemo } from 'react';
import { Card, Segmented, Select, Alert, Spin, Empty, Row, Col, Statistic, Table, Tag } from 'antd';
import ReactECharts from 'echarts-for-react';
import axios from 'axios';
import { useTheme } from '../context/ThemeContext';

const FORWARD_OPTIONS = [
  { label: '1个月', value: 21 },
  { label: '2个月', value: 42 },
  { label: '3个月', value: 63 },
];

const VOL_OPTIONS = [
  { label: '近20日波动', value: 20 },
  { label: '近60日波动', value: 60 },
  { label: '近250日波动', value: 250 },
];

function MarketScenario() {
  const { isDark } = useTheme();
  const [indexes, setIndexes] = useState([]);
  const [indexCode, setIndexCode] = useState('sh000688');
  const [forwardDays, setForwardDays] = useState(42);
  const [volWindow, setVolWindow] = useState(60);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axios
      .get('/api/market/indexes')
      .then((res) => setIndexes(res.data))
      .catch((err) => console.error('获取指数列表失败:', err));
  }, []);

  useEffect(() => {
    setLoading(true);
    axios
      .get('/api/market/scenario', {
        params: { index_code: indexCode, forward_days: forwardDays, vol_window: volWindow },
      })
      .then((res) => setData(res.data))
      .catch((err) => {
        console.error('获取情景区间失败:', err);
        setData(null);
      })
      .finally(() => setLoading(false));
  }, [indexCode, forwardDays, volWindow]);

  const textColor = isDark ? '#e8e8e8' : '#333333';
  const axisColor = isDark ? '#737373' : '#888888';
  const gridColor = isDark ? '#2a2a2a' : '#f0f0f0';

  const option = useMemo(() => {
    if (!data) return null;

    const histDates = data.history.map((h) => h.date);
    const allDates = [...histDates, ...data.forward_dates];
    const pad = new Array(histDates.length - 1).fill(null);
    const anchor = data.last_price;
    // 情景线从历史最后一点接续，避免视觉断裂
    const forward = (key) => {
      const s = data.scenarios.find((x) => x.key === key);
      return [...pad, anchor, ...s.values];
    };

    // 区间用「下沿 + 差值堆叠」实现填充
    const band = (lowKey, highKey) => {
      const low = forward(lowKey);
      const high = forward(highKey);
      return {
        base: low,
        span: high.map((v, i) => (v == null || low[i] == null ? null : Number((v - low[i]).toFixed(2)))),
      };
    };

    const outer = band('p05', 'p95');
    const inner = band('p25', 'p75');

    const mkBand = (name, b, color, stackName) => [
      {
        name: `${name}-base`,
        type: 'line',
        stack: stackName,
        data: b.base,
        lineStyle: { opacity: 0 },
        showSymbol: false,
        areaStyle: { opacity: 0 },
        tooltip: { show: false },
        silent: true,
      },
      {
        name,
        type: 'line',
        stack: stackName,
        data: b.span,
        lineStyle: { opacity: 0 },
        showSymbol: false,
        areaStyle: { color },
        tooltip: { show: false },
        silent: true,
      },
    ];

    const levelLines = data.levels
      .filter((l) => l.name.startsWith('MA'))
      .map((l) => ({
        yAxis: l.value,
        label: {
          formatter: `${l.name} ${l.value}`,
          color: axisColor,
          fontSize: 10,
          position: 'insideEndTop',
        },
        lineStyle: { color: axisColor, type: 'dotted', width: 1 },
      }));

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
        data: ['实际走势', '中性', '乐观', '悲观', '极端乐观', '极端悲观'],
        top: 8,
        textStyle: { color: axisColor },
      },
      grid: { left: '8%', right: '6%', top: 48, bottom: 60 },
      xAxis: {
        type: 'category',
        data: allDates,
        boundaryGap: false,
        axisLine: { lineStyle: { color: gridColor } },
        axisLabel: { color: axisColor, fontSize: 10 },
      },
      yAxis: {
        type: 'value',
        scale: true,
        splitLine: { lineStyle: { color: gridColor } },
        axisLabel: { color: axisColor, fontSize: 10 },
      },
      dataZoom: [
        { type: 'inside', start: 0, end: 100 },
        { type: 'slider', start: 0, end: 100, height: 18, bottom: 12 },
      ],
      series: [
        ...mkBand('90%概率区间', outer, isDark ? 'rgba(24,144,255,0.10)' : 'rgba(24,144,255,0.08)', 'outer'),
        ...mkBand('50%概率区间', inner, isDark ? 'rgba(24,144,255,0.20)' : 'rgba(24,144,255,0.16)', 'inner'),
        {
          name: '实际走势',
          type: 'line',
          data: data.history.map((h) => h.close),
          showSymbol: false,
          lineStyle: { width: 2, color: isDark ? '#e8e8e8' : '#333' },
          markLine: { symbol: 'none', silent: true, data: levelLines },
        },
        {
          name: '极端乐观',
          type: 'line',
          data: forward('p95'),
          showSymbol: false,
          lineStyle: { width: 1, type: 'dotted', color: '#ff4d4f' },
        },
        {
          name: '乐观',
          type: 'line',
          data: forward('p75'),
          showSymbol: false,
          lineStyle: { width: 1, type: 'dashed', color: '#ff7875' },
        },
        {
          name: '中性',
          type: 'line',
          data: forward('p50'),
          showSymbol: false,
          lineStyle: { width: 2, type: 'dashed', color: '#1890ff' },
        },
        {
          name: '悲观',
          type: 'line',
          data: forward('p25'),
          showSymbol: false,
          lineStyle: { width: 1, type: 'dashed', color: '#95de64' },
        },
        {
          name: '极端悲观',
          type: 'line',
          data: forward('p05'),
          showSymbol: false,
          lineStyle: { width: 1, type: 'dotted', color: '#52c41a' },
        },
      ],
    };
  }, [data, isDark, textColor, axisColor, gridColor]);

  return (
    <div>
      <Alert
        type="warning"
        showIcon
        style={{ marginBottom: 16 }}
        message="这不是预测"
        description="下图未来部分是按历史已实现波动率推演的随机游走分位数区间：中枢采用零漂移假设，区间宽度只反映过去的波动水平。它回答的是「若波动率不变，价格有多大概率落在什么范围」，不代表方向判断。"
      />

      <Card
        size="small"
        style={{ marginBottom: 16 }}
        styles={{ body: { display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'center' } }}
      >
        <Select
          value={indexCode}
          onChange={setIndexCode}
          style={{ width: 160 }}
          options={indexes.map((i) => ({ label: i.name, value: i.code }))}
        />
        <Segmented options={FORWARD_OPTIONS} value={forwardDays} onChange={setForwardDays} />
        <Segmented options={VOL_OPTIONS} value={volWindow} onChange={setVolWindow} />
      </Card>

      <Spin spinning={loading}>
        {data ? (
          <>
            <Row gutter={16} style={{ marginBottom: 16 }}>
              <Col span={6}>
                <Card size="small">
                  <Statistic title={`${data.index_name} 最新`} value={data.last_price} precision={2} />
                  <div style={{ color: 'var(--text-secondary)', fontSize: 12 }}>{data.last_date}</div>
                </Card>
              </Col>
              <Col span={6}>
                <Card size="small">
                  <Statistic title="年化波动率" value={data.annualized_vol} precision={1} suffix="%" />
                  <div style={{ color: 'var(--text-secondary)', fontSize: 12 }}>
                    回看 {data.vol_window} 个交易日
                  </div>
                </Card>
              </Col>
              <Col span={6}>
                <Card size="small">
                  <Statistic
                    title="推演终点"
                    value={data.forward_dates[data.forward_dates.length - 1]}
                    valueStyle={{ fontSize: 20 }}
                  />
                  <div style={{ color: 'var(--text-secondary)', fontSize: 12 }}>
                    {data.forward_days} 个交易日后
                  </div>
                </Card>
              </Col>
              <Col span={6}>
                <Card size="small">
                  <Statistic
                    title="50% 概率区间"
                    value={`${data.scenarios.find((s) => s.key === 'p25').end_value} ~ ${
                      data.scenarios.find((s) => s.key === 'p75').end_value
                    }`}
                    valueStyle={{ fontSize: 20 }}
                  />
                  <div style={{ color: 'var(--text-secondary)', fontSize: 12 }}>终点价位</div>
                </Card>
              </Col>
            </Row>

            <Card size="small" style={{ marginBottom: 16 }}>
              {option ? <ReactECharts option={option} style={{ height: 460 }} notMerge /> : <Empty />}
            </Card>

            <Row gutter={16}>
              <Col span={12}>
                <Card size="small" title="终点情景">
                  <Table
                    size="small"
                    pagination={false}
                    rowKey="key"
                    dataSource={data.scenarios}
                    columns={[
                      { title: '情景', dataIndex: 'label' },
                      {
                        title: '累计概率',
                        dataIndex: 'probability',
                        render: (v) => `${(v * 100).toFixed(0)}%`,
                      },
                      { title: '点位', dataIndex: 'end_value' },
                      {
                        title: '较现价',
                        dataIndex: 'end_change_pct',
                        render: (v) => (
                          <Tag color={v >= 0 ? 'red' : 'green'}>
                            {v >= 0 ? '+' : ''}
                            {v}%
                          </Tag>
                        ),
                      },
                    ]}
                  />
                </Card>
              </Col>
              <Col span={12}>
                <Card size="small" title="关键位置">
                  <Table
                    size="small"
                    pagination={false}
                    rowKey="name"
                    dataSource={data.levels}
                    columns={[
                      { title: '位置', dataIndex: 'name' },
                      { title: '点位', dataIndex: 'value' },
                      {
                        title: '现价相对',
                        dataIndex: 'distance_pct',
                        render: (v) => (
                          <Tag color={v >= 0 ? 'red' : 'green'}>
                            {v >= 0 ? '+' : ''}
                            {v}%
                          </Tag>
                        ),
                      },
                    ]}
                  />
                </Card>
              </Col>
            </Row>
          </>
        ) : (
          !loading && <Empty description="暂无数据" />
        )}
      </Spin>
    </div>
  );
}

export default MarketScenario;
