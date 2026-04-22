import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Row, Col, Button, Spin, Empty, Tag, Table, Progress } from 'antd';
import {
  SwapOutlined,
  RiseOutlined,
  FallOutlined,
} from '@ant-design/icons';
import FundChart from '../components/FundChart';
import { useTheme } from '../context/ThemeContext';
import axios from 'axios';

function FundDetail() {
  const { code } = useParams();
  const navigate = useNavigate();
  const { isDark } = useTheme();
  const [fundInfo, setFundInfo] = useState(null);
  const [historyData, setHistoryData] = useState(null);
  const [holdings, setHoldings] = useState([]);
  const [estimate, setEstimate] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    setFundInfo(null);
    setHistoryData(null);
    setHoldings([]);
    setEstimate(null);
    fetchFundData();
  }, [code]);

  const fetchFundData = async () => {
    try {
      const [infoRes, historyRes, holdingsRes, estimateRes] = await Promise.all([
        axios.get(`/api/funds/info/${code}`).catch(() => null),
        axios.get(`/api/funds/history/${code}`, { params: { period: 'all' } }).catch(() => null),
        axios.get(`/api/funds/holdings/${code}`).catch(() => null),
        axios.get(`/api/funds/estimate/${code}`).catch(() => null),
      ]);
      if (infoRes) setFundInfo(infoRes.data);
      if (historyRes) setHistoryData(historyRes.data);
      if (holdingsRes) setHoldings(holdingsRes.data?.holdings || []);
      if (estimateRes) setEstimate(estimateRes.data);
    } catch (error) {
      console.error('获取基金数据失败:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: 100 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!fundInfo && !historyData) {
    return (
      <Empty
        description="暂无该基金数据"
        style={{ marginTop: 100 }}
      />
    );
  }

  const name = fundInfo?.name || code;

  // 从历史数据计算最新净值和涨跌幅
  const latest = historyData?.[historyData.length - 1];
  const prev = historyData?.length > 1 ? historyData[historyData.length - 2] : null;
  const latestNav = latest?.nav || 0;
  const latestAdjustedNav = latest?.adjusted_nav ?? latestNav;
  const changePercent = latest?.change_percent || 0;
  const isUp = changePercent >= 0;
  const upColor = isDark ? '#ff4d4f' : '#d93026';
  const downColor = isDark ? '#73d13d' : '#238636';
  const color = isUp ? upColor : downColor;
  const Icon = isUp ? RiseOutlined : FallOutlined;

  // 使用复权净值计算区间收益（与主流平台一致）
  const firstAdjustedNav = historyData?.[0]?.adjusted_nav ?? historyData?.[0]?.nav ?? latestAdjustedNav;
  const totalReturn = firstAdjustedNav > 0 ? ((latestAdjustedNav - firstAdjustedNav) / firstAdjustedNav) * 100 : 0;

  // 实时估值
  const estimateChange = estimate?.estimate_change ?? null;
  const estimateNav = estimate?.estimate_nav ?? null;
  const estimateTime = estimate?.estimate_time ?? null;
  const isEstimateUp = estimateChange !== null ? estimateChange >= 0 : isUp;
  const estimateColor = isEstimateUp ? upColor : downColor;
  const EstimateIcon = isEstimateUp ? RiseOutlined : FallOutlined;

  const stats = latest
    ? [
        { label: '最新净值', value: latestNav, suffix: '', isFixed: 4 },
        { label: '日涨跌幅', value: changePercent, suffix: '%', isChange: true },
        { label: '成立以来收益', value: totalReturn, suffix: '%', isChange: true },
        { label: '净值日期', value: latest.date, suffix: '', isText: true },
      ]
    : [];

  // 如果有实时估值，插入到日涨跌幅之后
  if (estimateChange !== null) {
    stats.splice(2, 0, {
      label: '实时估值',
      value: estimateNav,
      suffix: '',
      isFixed: 4,
      isEstimate: true,
    });
    stats.splice(3, 0, {
      label: '估算涨跌',
      value: estimateChange,
      suffix: '%',
      isChange: true,
      isEstimate: true,
    });
  }

  const holdingColumns = [
    {
      title: '排名',
      dataIndex: 'rank',
      width: 60,
      render: (val) => <span style={{ fontWeight: 600 }}>{val}</span>,
    },
    {
      title: '股票名称',
      dataIndex: 'stock_name',
      render: (val, record) => (
        <span
          style={{ cursor: 'pointer', color: 'var(--accent)', fontWeight: 600 }}
          onClick={() => navigate(`/detail/${record.stock_code}`)}
        >
          {val}
        </span>
      ),
    },
    {
      title: '股票代码',
      dataIndex: 'stock_code',
      width: 100,
      render: (val) => (
        <span style={{ fontVariantNumeric: 'tabular-nums', color: 'var(--text-secondary)' }}>
          {val}
        </span>
      ),
    },
    {
      title: '占净值比例',
      dataIndex: 'weight',
      width: 180,
      render: (val) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <Progress
            percent={val}
            size="small"
            strokeColor="#1677ff"
            showInfo={false}
            style={{ width: 80 }}
          />
          <span style={{ fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>
            {val}%
          </span>
        </div>
      ),
    },
    {
      title: '持股数（万股）',
      dataIndex: 'shares',
      width: 140,
      render: (val) => (
        <span style={{ fontVariantNumeric: 'tabular-nums', color: 'var(--text-secondary)' }}>
          {val}
        </span>
      ),
    },
    {
      title: '持仓市值（万元）',
      dataIndex: 'market_value',
      width: 160,
      render: (val) => (
        <span style={{ fontVariantNumeric: 'tabular-nums', color: 'var(--text-secondary)' }}>
          {val}
        </span>
      ),
    },
  ];

  return (
    <div>
      {/* 顶部基金信息栏 */}
      <Card
        style={{ marginBottom: 20, borderRadius: 12, background: 'var(--bg-card)' }}
        styles={{ body: { padding: '20px 28px' } }}
      >
        <Row justify="space-between" align="middle" wrap={false}>
          <Col>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 4 }}>
              <span style={{ fontSize: 22, fontWeight: 700, color: 'var(--text-primary)' }}>
                {name}
              </span>
              <Tag style={{ fontSize: 13, padding: '2px 10px', background: 'var(--bg-primary)', color: 'var(--text-secondary)', borderColor: 'var(--border-color)' }}>
                {code}
              </Tag>
              {fundInfo?.fund_type && (
                <Tag color="green" style={{ fontSize: 12 }}>
                  {fundInfo.fund_type}
                </Tag>
              )}
            </div>
          </Col>
          <Col>
            <Button
              type="primary"
              icon={<SwapOutlined />}
              onClick={() => navigate('/fund-comparison', { state: { code } })}
            >
              加入对比
            </Button>
          </Col>
        </Row>

        {/* 核心净值区 */}
        <Row align="bottom" style={{ marginTop: 20 }} gutter={32}>
          <Col>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 12 }}>
              <span
                style={{
                  fontSize: 40,
                  fontWeight: 700,
                  color,
                  fontVariantNumeric: 'tabular-nums',
                  letterSpacing: '-0.02em',
                }}
              >
                {latestNav > 0 ? latestNav.toFixed(4) : '—'}
              </span>
              <span
                style={{
                  fontSize: 18,
                  fontWeight: 600,
                  color,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 4,
                }}
              >
                <Icon />
                {latestNav > 0
                  ? `${isUp ? '+' : ''}${changePercent.toFixed(2)}%`
                  : '—'}
              </span>
            </div>
          </Col>
          {estimateChange !== null && (
            <Col>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, paddingLeft: 16, borderLeft: '1px solid var(--border-color)' }}>
                <span style={{ fontSize: 13, color: 'var(--text-tertiary)' }}>实时估值</span>
                <span
                  style={{
                    fontSize: 28,
                    fontWeight: 700,
                    color: estimateColor,
                    fontVariantNumeric: 'tabular-nums',
                  }}
                >
                  {estimateNav > 0 ? estimateNav.toFixed(4) : '—'}
                </span>
                <span
                  style={{
                    fontSize: 15,
                    fontWeight: 600,
                    color: estimateColor,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 4,
                  }}
                >
                  <EstimateIcon />
                  {estimateNav > 0
                    ? `${isEstimateUp ? '+' : ''}${estimateChange.toFixed(2)}%`
                    : '—'}
                </span>
                {estimateTime && (
                  <span style={{ fontSize: 11, color: 'var(--text-tertiary)', marginLeft: 4 }}>
                    {estimateTime}
                  </span>
                )}
              </div>
            </Col>
          )}
        </Row>

        {/* 详细数据网格 */}
        <Row gutter={[24, 16]} style={{ marginTop: 20 }}>
          {stats.map((s) => (
            <Col key={s.label} xs={8} sm={8} md={4}>
              <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginBottom: 2 }}>
                {s.label}
              </div>
              <div
                style={{
                  fontSize: 15,
                  fontWeight: 600,
                  color: s.isEstimate
                    ? estimateColor
                    : s.isChange
                      ? color
                      : 'var(--text-primary)',
                  fontVariantNumeric: 'tabular-nums',
                }}
              >
                {s.isText
                  ? s.value
                  : typeof s.value === 'number'
                    ? (s.isFixed ? s.value.toFixed(s.isFixed) : `${s.value >= 0 && s.isChange ? '+' : ''}${s.value.toFixed(2)}`)
                    : '—'}
                {!s.isText && (
                  <span style={{ fontSize: 12, color: 'var(--text-tertiary)', marginLeft: 2 }}>
                    {s.suffix}
                  </span>
                )}
              </div>
            </Col>
          ))}
        </Row>
      </Card>

      {/* 净值走势图 */}
      <FundChart fundCode={code} fundName={name} />

      {/* 持仓明细 */}
      {holdings.length > 0 && (
        <Card
          title="投资组合（前十大重仓股）"
          style={{ marginTop: 20, borderRadius: 12, background: 'var(--bg-card)' }}
          styles={{ body: { padding: '16px 20px' } }}
        >
          <Table
            columns={holdingColumns}
            dataSource={holdings}
            rowKey="rank"
            pagination={false}
            size="middle"
            scroll={{ x: 700 }}
          />
        </Card>
      )}
    </div>
  );
}

export default FundDetail;
