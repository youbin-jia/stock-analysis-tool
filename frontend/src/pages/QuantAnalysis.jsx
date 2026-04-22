import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Table, Tag, Statistic, Row, Col, Empty, Spin, InputNumber, Button, Tabs, Space, Tooltip } from 'antd';
import {
  ExperimentOutlined, RiseOutlined, FallOutlined, InfoCircleOutlined,
  ThunderboltOutlined, TrophyOutlined, FundOutlined, StockOutlined,
} from '@ant-design/icons';
import axios from 'axios';
import { useTheme } from '../context/ThemeContext';

const SCREEN_TYPES = [
  { key: 'cxg', label: '创新高' },
  { key: 'cxd', label: '创新低' },
  { key: 'cxfl', label: '持续放量' },
  { key: 'cxsl', label: '持续缩量' },
  { key: 'ljqs', label: '量价齐升' },
  { key: 'ljqd', label: '量价齐跌' },
  { key: 'lxsz', label: '连续上涨' },
  { key: 'lxxd', label: '连续下跌' },
  { key: 'xstp', label: '向上突破' },
  { key: 'xxtp', label: '向下突破' },
  { key: 'xzjp', label: '险资举牌' },
];

const FUND_TYPE_OPTIONS = [
  { label: '全部', value: '全部' },
  { label: '股票型', value: '股票型' },
  { label: '混合型', value: '混合型' },
  { label: '债券型', value: '债券型' },
  { label: '指数型', value: '指数型' },
  { label: 'QDII', value: 'QDII' },
  { label: 'FOF', value: 'FOF' },
];

function QuantAnalysis() {
  const { isDark } = useTheme();
  const navigate = useNavigate();

  // 智能选股
  const [screenType, setScreenType] = useState('cxg');
  const [screenData, setScreenData] = useState([]);
  const [screenLoading, setScreenLoading] = useState(false);
  const [showHot, setShowHot] = useState(false);
  const [hotData, setHotData] = useState([]);

  // 多因子选股
  const [filters, setFilters] = useState({
    pe_min: null, pe_max: null, pb_min: null, pb_max: null,
    roe_min: null, revenue_growth_min: null, net_profit_growth_min: null,
    dividend_yield_min: null, debt_ratio_max: null,
  });
  const [fundamentalData, setFundamentalData] = useState([]);
  const [fundamentalLoading, setFundamentalLoading] = useState(false);

  // 推荐榜
  const [stockRecommend, setStockRecommend] = useState([]);
  const [stockRecommendLoading, setStockRecommendLoading] = useState(false);
  const [fundRecommend, setFundRecommend] = useState([]);
  const [fundRecommendLoading, setFundRecommendLoading] = useState(false);
  const [fundType, setFundType] = useState('全部');

  // 市场估值
  const [marketValuation, setMarketValuation] = useState(null);
  const [valuationLoading, setValuationLoading] = useState(false);

  const fetchScreenData = useCallback(async (type) => {
    setScreenLoading(true);
    setShowHot(false);
    try {
      const res = await axios.get('/api/quant/screen', { params: { type } });
      setScreenData(res.data || []);
    } catch (e) {
      console.error('智能选股失败:', e);
    } finally {
      setScreenLoading(false);
    }
  }, []);

  const fetchHotStocks = useCallback(async () => {
    setScreenLoading(true);
    setShowHot(true);
    try {
      const res = await axios.get('/api/quant/hot-stocks');
      setHotData(res.data || []);
    } catch (e) {
      console.error('人气榜失败:', e);
    } finally {
      setScreenLoading(false);
    }
  }, []);

  const fetchFundamental = async () => {
    setFundamentalLoading(true);
    try {
      const cleanFilters = {};
      Object.entries(filters).forEach(([k, v]) => {
        if (v !== null && v !== undefined) cleanFilters[k] = v;
      });
      const res = await axios.post('/api/quant/fundamental-screen', cleanFilters);
      setFundamentalData(res.data || []);
    } catch (e) {
      console.error('多因子筛选失败:', e);
    } finally {
      setFundamentalLoading(false);
    }
  };

  const fetchStockRecommend = useCallback(async () => {
    setStockRecommendLoading(true);
    try {
      const res = await axios.get('/api/quant/recommend', { params: { limit: 30 } });
      setStockRecommend(res.data || []);
    } catch (e) {
      console.error('股票推荐失败:', e);
    } finally {
      setStockRecommendLoading(false);
    }
  }, []);

  const fetchFundRecommend = useCallback(async (type) => {
    setFundRecommendLoading(true);
    try {
      const res = await axios.get('/api/quant/fund-recommend', { params: { type, limit: 20 } });
      setFundRecommend(res.data || []);
    } catch (e) {
      console.error('基金推荐失败:', e);
    } finally {
      setFundRecommendLoading(false);
    }
  }, []);

  const fetchMarketValuation = useCallback(async () => {
    setValuationLoading(true);
    try {
      const res = await axios.get('/api/quant/market-valuation');
      setMarketValuation(res.data);
    } catch (e) {
      console.error('市场估值失败:', e);
    } finally {
      setValuationLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchScreenData('cxg');
  }, []);

  useEffect(() => {
    fetchStockRecommend();
    fetchFundRecommend('全部');
    fetchMarketValuation();
  }, []);

  useEffect(() => {
    fetchFundRecommend(fundType);
  }, [fundType]);

  const renderChange = (val, suffix = '%') => {
    if (val == null) return <span style={{ color: 'var(--text-tertiary)' }}>-</span>;
    const color = val > 0 ? '#ff4d4f' : val < 0 ? '#52c41a' : 'var(--text-primary)';
    const icon = val > 0 ? <RiseOutlined style={{ marginRight: 2 }} /> : val < 0 ? <FallOutlined style={{ marginRight: 2 }} /> : null;
    return (
      <span style={{ color, fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>
        {icon}{val > 0 ? '+' : ''}{typeof val === 'number' ? val.toFixed(2) : val}{suffix}
      </span>
    );
  };

  const renderScoreBar = (score, maxScore = 100) => {
    const pct = Math.min(100, (score / maxScore) * 100);
    let color = '#52c41a';
    if (score >= 70) color = '#ff4d4f';
    else if (score >= 50) color = '#faad14';
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <div style={{ width: 60, height: 6, borderRadius: 3, background: 'var(--bg-secondary)', overflow: 'hidden' }}>
          <div style={{ width: `${pct}%`, height: '100%', borderRadius: 3, background: color }} />
        </div>
        <span style={{ fontVariantNumeric: 'tabular-nums', fontSize: 13, fontWeight: 600, color }}>{score}</span>
      </div>
    );
  };

  // 智能选股列
  const screenColumns = [
    {
      title: '排名', width: 55,
      render: (_, __, i) => (
        <span style={{ fontWeight: 700, fontSize: 14, color: i < 3 ? '#ff4d4f' : 'var(--text-primary)' }}>{i + 1}</span>
      ),
    },
    {
      title: '股票', width: 150,
      render: (_, r) => (
        <div style={{ cursor: 'pointer' }} onClick={() => navigate(`/detail/${r.code}`)}>
          <div style={{ fontWeight: 600, color: 'var(--accent)', fontSize: 14 }}>{r.name}</div>
          <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>{r.code}</div>
        </div>
      ),
    },
    {
      title: '最新价', dataIndex: 'price', width: 80,
      render: (val) => <span style={{ fontVariantNumeric: 'tabular-nums' }}>{val || '-'}</span>,
    },
    {
      title: '涨跌幅', dataIndex: 'change_percent', width: 100,
      render: (val) => renderChange(val),
    },
    {
      title: '换手率', dataIndex: 'turnover_rate', width: 90,
      render: (val) => val ? `${val}%` : '-',
    },
  ];

  // 人气榜列
  const hotColumns = [
    {
      title: '排名', width: 55,
      render: (_, __, i) => (
        <span style={{ fontWeight: 700, fontSize: 14, color: i < 3 ? '#ff4d4f' : 'var(--text-primary)' }}>{i + 1}</span>
      ),
    },
    {
      title: '股票', width: 150,
      render: (_, r) => (
        <div style={{ cursor: 'pointer' }} onClick={() => navigate(`/detail/${r.code}`)}>
          <div style={{ fontWeight: 600, color: 'var(--accent)', fontSize: 14 }}>{r.name}</div>
          <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>{r.code}</div>
        </div>
      ),
    },
    {
      title: '最新价', dataIndex: 'price', width: 80,
      render: (val) => <span style={{ fontVariantNumeric: 'tabular-nums' }}>{val || '-'}</span>,
    },
    {
      title: '涨跌幅', dataIndex: 'change_percent', width: 100,
      render: (val) => renderChange(val),
    },
    {
      title: '人气', dataIndex: 'hot_rank', width: 80,
      render: (val) => <span style={{ fontVariantNumeric: 'tabular-nums' }}>{val || '-'}</span>,
    },
  ];

  // 多因子列
  const fundamentalColumns = [
    {
      title: '排名', width: 55,
      render: (_, __, i) => (
        <span style={{ fontWeight: 700, fontSize: 14, color: i < 3 ? '#ff4d4f' : 'var(--text-primary)' }}>{i + 1}</span>
      ),
    },
    {
      title: '股票', width: 150,
      render: (_, r) => (
        <div style={{ cursor: 'pointer' }} onClick={() => navigate(`/detail/${r.code}`)}>
          <div style={{ fontWeight: 600, color: 'var(--accent)', fontSize: 14 }}>{r.name || r.code}</div>
          <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>{r.code}</div>
        </div>
      ),
    },
    {
      title: 'PE(TTM)', dataIndex: 'pe_ttm', width: 85,
      render: (val) => <span style={{ fontVariantNumeric: 'tabular-nums' }}>{val || '-'}</span>,
    },
    {
      title: 'PB', dataIndex: 'pb', width: 70,
      render: (val) => <span style={{ fontVariantNumeric: 'tabular-nums' }}>{val || '-'}</span>,
    },
    {
      title: 'ROE', dataIndex: 'roe', width: 80,
      render: (val) => val ? `${(val * 100).toFixed(2)}%` : '-',
    },
    {
      title: '营收增速', dataIndex: 'revenue_growth', width: 90,
      render: (val) => val ? `${(val * 100).toFixed(2)}%` : '-',
    },
    {
      title: '利润增速', dataIndex: 'net_profit_growth', width: 90,
      render: (val) => val ? `${(val * 100).toFixed(2)}%` : '-',
    },
    {
      title: '负债率', dataIndex: 'debt_ratio', width: 80,
      render: (val) => val ? `${(val * 100).toFixed(2)}%` : '-',
    },
    {
      title: '股息率', dataIndex: 'dividend_yield', width: 80,
      render: (val) => val ? `${val}%` : '-',
    },
    {
      title: '综合评分', dataIndex: 'total_score', width: 120,
      sorter: (a, b) => (a.total_score || 0) - (b.total_score || 0),
      defaultSortOrder: 'descend',
      render: (val) => renderScoreBar(val || 0),
    },
  ];

  // 股票推荐列
  const stockRecommendColumns = [
    {
      title: '排名', width: 55,
      render: (_, __, i) => (
        <span style={{ fontWeight: 700, fontSize: 14, color: i < 3 ? '#ff4d4f' : 'var(--text-primary)' }}>{i + 1}</span>
      ),
    },
    {
      title: '股票', width: 150,
      render: (_, r) => (
        <div style={{ cursor: 'pointer' }} onClick={() => navigate(`/detail/${r.code}`)}>
          <div style={{ fontWeight: 600, color: 'var(--accent)', fontSize: 14 }}>{r.name || r.code}</div>
          <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>{r.code}</div>
        </div>
      ),
    },
    {
      title: '综合评分', dataIndex: 'total_score', width: 120,
      sorter: (a, b) => (a.total_score || 0) - (b.total_score || 0),
      defaultSortOrder: 'descend',
      render: (val) => renderScoreBar(val || 0),
    },
    {
      title: '估值', dataIndex: 'valuation_score', width: 100,
      render: (val) => renderScoreBar(val || 0),
    },
    {
      title: '盈利', dataIndex: 'profit_score', width: 100,
      render: (val) => renderScoreBar(val || 0),
    },
    {
      title: '成长', dataIndex: 'growth_score', width: 100,
      render: (val) => renderScoreBar(val || 0),
    },
    {
      title: '偿债', dataIndex: 'debt_score', width: 100,
      render: (val) => renderScoreBar(val || 0),
    },
    {
      title: '股息', dataIndex: 'dividend_score', width: 100,
      render: (val) => renderScoreBar(val || 0),
    },
  ];

  // 基金推荐列
  const fundRecommendColumns = [
    {
      title: '排名', width: 55,
      render: (_, __, i) => (
        <span style={{ fontWeight: 700, fontSize: 14, color: i < 3 ? '#ff4d4f' : 'var(--text-primary)' }}>{i + 1}</span>
      ),
    },
    {
      title: '基金', width: 180,
      render: (_, r) => (
        <div style={{ cursor: 'pointer' }} onClick={() => navigate(`/fund/${r.code}`)}>
          <div style={{ fontWeight: 600, color: 'var(--accent)', fontSize: 14 }}>{r.name}</div>
          <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>
            {r.code}
            {r.fund_type && <Tag size="small" style={{ marginLeft: 6, fontSize: 11 }}>{r.fund_type}</Tag>}
          </div>
        </div>
      ),
    },
    {
      title: '最新净值', dataIndex: 'nav', width: 85,
      render: (val) => <span style={{ fontVariantNumeric: 'tabular-nums' }}>{val || '-'}</span>,
    },
    {
      title: '日涨幅', dataIndex: 'daily_change', width: 90,
      render: (val) => renderChange(val),
    },
    {
      title: '近1月', dataIndex: 'month_change', width: 85,
      render: (val) => renderChange(val),
    },
    {
      title: '近1年', dataIndex: 'year_change', width: 85,
      render: (val) => renderChange(val),
    },
    {
      title: '成立来', dataIndex: 'total_change', width: 90,
      render: (val) => renderChange(val),
    },
    {
      title: '综合得分', dataIndex: 'fund_score', width: 100,
      sorter: (a, b) => (a.fund_score || 0) - (b.fund_score || 0),
      defaultSortOrder: 'descend',
      render: (val) => <span style={{ fontVariantNumeric: 'tabular-nums', fontWeight: 700, color: '#ff4d4f' }}>{val || '-'}</span>,
    },
  ];

  const filterInputs = [
    { key: 'pe_min', label: 'PE最低', step: 1 },
    { key: 'pe_max', label: 'PE最高', step: 1 },
    { key: 'pb_min', label: 'PB最低', step: 0.1 },
    { key: 'pb_max', label: 'PB最高', step: 0.1 },
    { key: 'roe_min', label: 'ROE最低', step: 0.01, extra: '(小数)' },
    { key: 'revenue_growth_min', label: '营收增速最低', step: 0.01, extra: '(小数)' },
    { key: 'net_profit_growth_min', label: '利润增速最低', step: 0.01, extra: '(小数)' },
    { key: 'dividend_yield_min', label: '股息率最低', step: 0.1, extra: '(%)' },
    { key: 'debt_ratio_max', label: '负债率最高', step: 0.01, extra: '(小数)' },
  ];

  return (
    <div>
      {/* Card 1: 智能选股 */}
      <Card
        style={{ marginBottom: 20, borderRadius: 12, background: 'var(--bg-card)' }}
        styles={{ body: { padding: '20px 28px' } }}
      >
        <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
          <Col>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <ThunderboltOutlined style={{ fontSize: 22, color: '#faad14' }} />
              <span style={{ fontSize: 20, fontWeight: 700, color: 'var(--text-primary)' }}>智能选股</span>
            </div>
            <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 4 }}>
              基于技术面和市场面的选股策略，数据来源同花顺/东方财富
            </div>
          </Col>
        </Row>

        <div style={{ marginBottom: 16, display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {SCREEN_TYPES.map((s) => (
            <Tag
              key={s.key}
              color={screenType === s.key && !showHot ? 'blue' : 'default'}
              style={{ cursor: 'pointer', padding: '4px 12px', fontSize: 13 }}
              onClick={() => { setScreenType(s.key); fetchScreenData(s.key); }}
            >
              {s.label}
            </Tag>
          ))}
          <Tag
            color={showHot ? 'volcano' : 'default'}
            style={{ cursor: 'pointer', padding: '4px 12px', fontSize: 13, fontWeight: 600 }}
            onClick={fetchHotStocks}
          >
            人气榜
          </Tag>
        </div>

        {screenLoading ? (
          <div style={{ textAlign: 'center', padding: 60 }}>
            <Spin size="large" />
            <div style={{ marginTop: 12, color: 'var(--text-secondary)' }}>加载选股数据...</div>
          </div>
        ) : (showHot ? hotData : screenData).length > 0 ? (
          <Table
            columns={showHot ? hotColumns : screenColumns}
            dataSource={showHot ? hotData : screenData}
            rowKey="code"
            pagination={{ pageSize: 20, showSizeChanger: false }}
            size="middle"
            scroll={{ x: 600 }}
          />
        ) : (
          <Empty description="暂无选股数据" style={{ padding: 40 }} />
        )}
      </Card>

      {/* Card 2: 多因子选股 */}
      <Card
        style={{ marginBottom: 20, borderRadius: 12, background: 'var(--bg-card)' }}
        styles={{ body: { padding: '20px 28px' } }}
      >
        <div style={{ marginBottom: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <StockOutlined style={{ fontSize: 22, color: '#1890ff' }} />
            <span style={{ fontSize: 20, fontWeight: 700, color: 'var(--text-primary)' }}>多因子选股</span>
          </div>
          <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 4 }}>
            基本面筛选 + 综合评分，数据来源baostock
          </div>
        </div>

        <Row gutter={[16, 12]} style={{ marginBottom: 16 }}>
          {filterInputs.map((f) => (
            <Col key={f.key} xs={12} sm={8} md={6} lg={4}>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4 }}>
                {f.label} {f.extra && <span style={{ fontSize: 11, opacity: 0.7 }}>{f.extra}</span>}
              </div>
              <InputNumber
                size="small"
                style={{ width: '100%' }}
                step={f.step}
                placeholder="不限"
                value={filters[f.key]}
                onChange={(v) => setFilters((prev) => ({ ...prev, [f.key]: v }))}
              />
            </Col>
          ))}
          <Col xs={12} sm={8} md={6} lg={4} style={{ display: 'flex', alignItems: 'flex-end' }}>
            <Button type="primary" onClick={fetchFundamental} loading={fundamentalLoading} icon={<StockOutlined />}>
              开始筛选
            </Button>
          </Col>
        </Row>

        {fundamentalLoading ? (
          <div style={{ textAlign: 'center', padding: 60 }}>
            <Spin size="large" />
            <div style={{ marginTop: 12, color: 'var(--text-secondary)' }}>扫描全市场，请稍候...</div>
          </div>
        ) : fundamentalData.length > 0 ? (
          <Table
            columns={fundamentalColumns}
            dataSource={fundamentalData}
            rowKey="code"
            pagination={{ pageSize: 20, showSizeChanger: false }}
            size="middle"
            scroll={{ x: 1000 }}
          />
        ) : (
          <Empty description="设置筛选条件后点击开始筛选" style={{ padding: 40 }} />
        )}
      </Card>

      {/* Card 3: 推荐榜 */}
      <Card
        style={{ marginBottom: 20, borderRadius: 12, background: 'var(--bg-card)' }}
        styles={{ body: { padding: '20px 28px' } }}
      >
        <div style={{ marginBottom: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <TrophyOutlined style={{ fontSize: 22, color: '#faad14' }} />
            <span style={{ fontSize: 20, fontWeight: 700, color: 'var(--text-primary)' }}>推荐榜</span>
          </div>
        </div>

        <Tabs
          defaultActiveKey="stock"
          items={[
            {
              key: 'stock',
              label: '股票推荐',
              children: stockRecommendLoading ? (
                <div style={{ textAlign: 'center', padding: 40 }}>
                  <Spin size="large" />
                  <div style={{ marginTop: 12, color: 'var(--text-secondary)' }}>计算评分中，请稍候...</div>
                </div>
              ) : stockRecommend.length > 0 ? (
                <Table
                  columns={stockRecommendColumns}
                  dataSource={stockRecommend}
                  rowKey="code"
                  pagination={{ pageSize: 20, showSizeChanger: false }}
                  size="middle"
                  scroll={{ x: 900 }}
                />
              ) : (
                <Empty description="暂无推荐数据" style={{ padding: 40 }} />
              ),
            },
            {
              key: 'fund',
              label: '基金推荐',
              children: (
                <>
                  <div style={{ marginBottom: 12 }}>
                    <Space>
                      <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>基金类型：</span>
                      {FUND_TYPE_OPTIONS.map((opt) => (
                        <Tag
                          key={opt.value}
                          color={fundType === opt.value ? 'blue' : 'default'}
                          style={{ cursor: 'pointer' }}
                          onClick={() => setFundType(opt.value)}
                        >
                          {opt.label}
                        </Tag>
                      ))}
                    </Space>
                  </div>
                  {fundRecommendLoading ? (
                    <div style={{ textAlign: 'center', padding: 40 }}>
                      <Spin size="large" />
                    </div>
                  ) : fundRecommend.length > 0 ? (
                    <Table
                      columns={fundRecommendColumns}
                      dataSource={fundRecommend}
                      rowKey="code"
                      pagination={{ pageSize: 20, showSizeChanger: false }}
                      size="middle"
                      scroll={{ x: 900 }}
                    />
                  ) : (
                    <Empty description="暂无基金推荐数据" style={{ padding: 40 }} />
                  )}
                </>
              ),
            },
          ]}
        />
      </Card>

      {/* Card 4: 市场估值 */}
      <Card
        style={{ borderRadius: 12, background: 'var(--bg-card)' }}
        styles={{ body: { padding: '20px 28px' } }}
      >
        <div style={{ marginBottom: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <FundOutlined style={{ fontSize: 22, color: '#52c41a' }} />
            <span style={{ fontSize: 20, fontWeight: 700, color: 'var(--text-primary)' }}>市场估值</span>
          </div>
          <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 4 }}>
            全市场估值水平统计，数据来源akshare
          </div>
        </div>

        {valuationLoading ? (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Spin size="large" />
          </div>
        ) : marketValuation ? (
          <Row gutter={24}>
            <Col span={6}>
              <Statistic
                title="全市场PE中位数"
                value={marketValuation.pe_ttm_median || '-'}
                suffix="倍"
                valueStyle={{ color: 'var(--text-primary)', fontWeight: 700 }}
              />
              {marketValuation.pe_percentile ? (
                <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>
                  近10年分位: {marketValuation.pe_percentile}%
                </div>
              ) : null}
            </Col>
            <Col span={6}>
              <Statistic
                title="全市场PB中位数"
                value={marketValuation.pb_median || '-'}
                suffix="倍"
                valueStyle={{ color: 'var(--text-primary)', fontWeight: 700 }}
              />
              {marketValuation.pb_percentile ? (
                <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>
                  近10年分位: {marketValuation.pb_percentile}%
                </div>
              ) : null}
            </Col>
            <Col span={6}>
              <Statistic
                title="全市场股息率"
                value={marketValuation.dividend_yield || '-'}
                suffix="%"
                valueStyle={{ color: '#52c41a', fontWeight: 700 }}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="破净股数量"
                value={marketValuation.broken_net_count || '-'}
                suffix={marketValuation.total_count ? `/ ${marketValuation.total_count}` : '只'}
                valueStyle={{ color: '#faad14', fontWeight: 700 }}
              />
            </Col>
          </Row>
        ) : (
          <Empty description="暂无市场估值数据" style={{ padding: 40 }} />
        )}
      </Card>
    </div>
  );
}

export default QuantAnalysis;
