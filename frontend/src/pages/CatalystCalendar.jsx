import { useEffect, useState } from 'react';
import { Card, Select, Spin, Alert, Tag, Timeline, Empty, Row, Col, Statistic, Space, Input, Button } from 'antd';
import axios from 'axios';

const typeMeta = {
  earnings: { color: 'blue', label: '财报' },
  dividend: { color: 'green', label: '分红' },
  unlock:   { color: 'orange', label: '解禁' },
};

export default function CatalystCalendar() {
  const [days, setDays] = useState(30);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [stockCode, setStockCode] = useState('');
  const [stockData, setStockData] = useState(null);

  const load = async (d) => {
    setLoading(true); setError(null);
    try {
      const res = await axios.get(`/api/calendar/upcoming?days=${d}`);
      setData(res.data);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally { setLoading(false); }
  };

  const loadStock = async (code) => {
    if (!code) return;
    try {
      const res = await axios.get(`/api/calendar/stock/${code}?days=180`);
      setStockData(res.data);
    } catch (e) {
      setStockData({ events: [], error: e.message });
    }
  };

  useEffect(() => { load(days); /* eslint-disable-next-line */ }, []);

  return (
    <div>
      <Card title="催化剂日历（draft）" extra={
        <Space>
          <span>窗口：</span>
          <Select value={days} onChange={(v) => { setDays(v); load(v); }} style={{ width: 120 }}
            options={[{value:7,label:'未来 7 天'},{value:14,label:'未来 14 天'},{value:30,label:'未来 30 天'},{value:60,label:'未来 60 天'},{value:90,label:'未来 90 天'}]} />
        </Space>
      }>
        {loading && <Spin />}
        {error && <Alert type="error" message={error} />}
        {data && (
          <>
            <Row gutter={16} style={{ marginBottom: 16 }}>
              <Col span={6}><Card><Statistic title="事件总数" value={data.count} /></Card></Col>
              <Col span={6}><Card><Statistic title="财报披露" value={data.by_type.earnings} valueStyle={{ color: '#1677ff' }} /></Card></Col>
              <Col span={6}><Card><Statistic title="分红除息" value={data.by_type.dividend} valueStyle={{ color: '#52c41a' }} /></Card></Col>
              <Col span={6}><Card><Statistic title="限售解禁" value={data.by_type.unlock} valueStyle={{ color: '#fa8c16' }} /></Card></Col>
            </Row>
            <Alert type="info" showIcon message={data.disclaimer} style={{ marginBottom: 16 }} />
            {data.events.length === 0 ? <Empty /> : (
              <Timeline
                mode="left"
                items={data.events.slice(0, 200).map((e, i) => ({
                  key: i,
                  color: typeMeta[e.type]?.color || 'gray',
                  label: e.date,
                  children: (
                    <span>
                      <Tag color={typeMeta[e.type]?.color}>{typeMeta[e.type]?.label}</Tag>
                      <strong>{e.name}</strong>({e.code})　{e.title}
                    </span>
                  ),
                }))}
              />
            )}
          </>
        )}
      </Card>

      <Card title="个股事件查询" style={{ marginTop: 16 }} extra={
        <Space>
          <Input placeholder="股票代码" value={stockCode} onChange={(e) => setStockCode(e.target.value)} style={{ width: 180 }} />
          <Button type="primary" onClick={() => loadStock(stockCode)}>查询</Button>
        </Space>
      }>
        {!stockData && <Empty description="输入代码查询未来 180 天事件" />}
        {stockData && stockData.events?.length === 0 && <Empty description="未来 180 天无披露事件" />}
        {stockData && stockData.events?.length > 0 && (
          <Timeline
            mode="left"
            items={stockData.events.map((e, i) => ({
              key: i,
              color: typeMeta[e.type]?.color || 'gray',
              label: e.date,
              children: <><Tag color={typeMeta[e.type]?.color}>{typeMeta[e.type]?.label}</Tag>{e.title}</>,
            }))}
          />
        )}
      </Card>
    </div>
  );
}
