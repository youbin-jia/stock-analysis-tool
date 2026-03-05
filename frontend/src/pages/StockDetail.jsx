import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Row, Col, Statistic, Button, Space, Spin, message } from 'antd';
import { ArrowUpOutlined, ArrowDownOutlined, CompareArrowsOutlined } from '@ant-design/icons';
import StockChart from '../components/StockChart';
import axios from 'axios';

function StockDetail() {
  const { code } = useParams();
  const navigate = useNavigate();
  const [stockInfo, setStockInfo] = useState(null);
  const [realtimeData, setRealtimeData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStockData();
    const interval = setInterval(fetchRealtimeData, 30000); // 每30秒刷新实时数据
    return () => clearInterval(interval);
  }, [code]);

  const fetchStockData = async () => {
    setLoading(true);
    try {
      await Promise.all([fetchStockInfo(), fetchRealtimeData()]);
    } catch (error) {
      console.error('获取股票数据失败:', error);
      message.error('获取股票数据失败');
    } finally {
      setLoading(false);
    }
  };

  const fetchStockInfo = async () => {
    try {
      const response = await axios.get(`/api/stocks/info/${code}`);
      setStockInfo(response.data);
    } catch (error) {
      console.error('获取股票信息失败:', error);
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

  const addToComparison = () => {
    navigate('/comparison', { state: { code } });
  };

  if (loading) {
    return <Spin tip="加载中..." style={{ display: 'block', marginTop: 100 }} />;
  }

  const isUp = realtimeData?.change_percent >= 0;

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button onClick={() => navigate(-1)}>返回</Button>
        <Button
          type="primary"
          icon={<CompareArrowsOutlined />}
          onClick={addToComparison}
        >
          加入对比
        </Button>
      </Space>

      <Card title={`${stockInfo?.name || code} (${code})`} style={{ marginBottom: 16 }}>
        <Row gutter={16}>
          <Col span={6}>
            <Statistic
              title="最新价"
              value={realtimeData?.price || 0}
              precision={2}
              prefix={isUp ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
              valueStyle={{ color: isUp ? '#cf1322' : '#3f8600' }}
              suffix="元"
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="涨跌幅"
              value={realtimeData?.change_percent || 0}
              precision={2}
              prefix={isUp ? '+' : ''}
              valueStyle={{ color: isUp ? '#cf1322' : '#3f8600' }}
              suffix="%"
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="成交量"
              value={realtimeData?.volume || 0}
              suffix="手"
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="成交额"
              value={realtimeData?.amount || 0}
              precision={2}
              suffix="万"
            />
          </Col>
        </Row>
        <Row gutter={16} style={{ marginTop: 16 }}>
          <Col span={6}>
            <Statistic
              title="开盘"
              value={realtimeData?.open || 0}
              precision={2}
              suffix="元"
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="最高"
              value={realtimeData?.high || 0}
              precision={2}
              suffix="元"
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="最低"
              value={realtimeData?.low || 0}
              precision={2}
              suffix="元"
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="涨跌额"
              value={realtimeData?.change || 0}
              precision={2}
              prefix={isUp ? '+' : ''}
              valueStyle={{ color: isUp ? '#cf1322' : '#3f8600' }}
              suffix="元"
            />
          </Col>
        </Row>
      </Card>

      <StockChart stockCode={code} stockName={stockInfo?.name || code} />
    </div>
  );
}

export default StockDetail;
