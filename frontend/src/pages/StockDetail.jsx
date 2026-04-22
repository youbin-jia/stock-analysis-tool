import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Row, Col, Button, Spin, Empty, Tag } from 'antd';
import {
  SwapOutlined,
  RiseOutlined,
  FallOutlined,
} from '@ant-design/icons';
import StockChart from '../components/StockChart';
import { useTheme } from '../context/ThemeContext';
import axios from 'axios';

function StockDetail() {
  const { code } = useParams();
  const navigate = useNavigate();
  const { isDark } = useTheme();
  const [stockInfo, setStockInfo] = useState(null);
  const [realtimeData, setRealtimeData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    setStockInfo(null);
    setRealtimeData(null);
    fetchStockData();
    const interval = setInterval(fetchRealtimeData, 30000);
    return () => clearInterval(interval);
  }, [code]);

  const fetchStockData = async () => {
    try {
      const [infoRes, rtRes] = await Promise.all([
        axios.get(`/api/stocks/info/${code}`).catch(() => null),
        axios.get(`/api/stocks/realtime/${code}`).catch(() => null),
      ]);
      if (infoRes) setStockInfo(infoRes.data);
      if (rtRes) setRealtimeData(rtRes.data);
    } catch (error) {
      console.error('获取股票数据失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchRealtimeData = async () => {
    try {
      const response = await axios.get(`/api/stocks/realtime/${code}`);
      setRealtimeData(response.data);
    } catch (error) {
      console.error('获取实时行情失败:', error);
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: 100 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!stockInfo && !realtimeData) {
    return (
      <Empty
        description="暂无该股票数据"
        style={{ marginTop: 100 }}
      />
    );
  }

  const name = stockInfo?.name || realtimeData?.name || code;
  const isUp = (realtimeData?.change_percent || 0) >= 0;
  const upColor = isDark ? '#ff4d4f' : '#d93026';
  const downColor = isDark ? '#73d13d' : '#238636';
  const color = isUp ? upColor : downColor;
  const Icon = isUp ? RiseOutlined : FallOutlined;

  const stats = realtimeData
    ? [
        { label: '今开', value: realtimeData.open, suffix: '元' },
        { label: '最高', value: realtimeData.high, suffix: '元' },
        { label: '最低', value: realtimeData.low, suffix: '元' },
        { label: '成交量', value: realtimeData.volume, suffix: '手' },
        { label: '成交额', value: realtimeData.amount, suffix: '万' },
        { label: '涨跌额', value: realtimeData.change, suffix: '元', isChange: true },
      ]
    : [];

  return (
    <div>
      {/* 顶部股票信息栏 */}
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
              <Tag color={stockInfo?.market === 'SH' ? 'blue' : 'cyan'} style={{ fontSize: 12 }}>
                {stockInfo?.market === 'SH' ? '上海' : '深圳'}
              </Tag>
            </div>
            <div style={{ fontSize: 13, color: 'var(--text-tertiary)' }}>
              {stockInfo?.industry || '—'}
            </div>
          </Col>
          <Col>
            <Button
              type="primary"
              icon={<SwapOutlined />}
              onClick={() => navigate('/comparison', { state: { code } })}
            >
              加入对比
            </Button>
          </Col>
        </Row>

        {/* 核心价格区 */}
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
                {realtimeData ? realtimeData.price.toFixed(2) : '—'}
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
                {realtimeData
                  ? `${isUp ? '+' : ''}${realtimeData.change_percent.toFixed(2)}%`
                  : '—'}
              </span>
              <span
                style={{
                  fontSize: 15,
                  color,
                  fontWeight: 500,
                }}
              >
                {realtimeData
                  ? `${isUp ? '+' : ''}${realtimeData.change.toFixed(2)}`
                  : '—'}
              </span>
            </div>
          </Col>
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
                  color: s.isChange ? color : 'var(--text-primary)',
                  fontVariantNumeric: 'tabular-nums',
                }}
              >
                {typeof s.value === 'number' ? s.value.toLocaleString() : '—'}
                <span style={{ fontSize: 12, color: 'var(--text-tertiary)', marginLeft: 2 }}>
                  {s.suffix}
                </span>
              </div>
            </Col>
          ))}
        </Row>
      </Card>

      {/* K 线图 */}
      <StockChart stockCode={code} stockName={name} />
    </div>
  );
}

export default StockDetail;
