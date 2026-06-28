import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Input, Button, Spin, Empty, Tag, Descriptions, Table, Alert, Space } from 'antd';
import axios from 'axios';

export default function EarningsSnapshot() {
  const { code: codeParam } = useParams();
  const navigate = useNavigate();
  const [code, setCode] = useState(codeParam || '600519');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const load = async (c) => {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.get(`/api/earnings/${c}`);
      setData(res.data);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(code); /* eslint-disable-next-line */ }, []);

  const fmt = (v, suffix = '') => (v === null || v === undefined ? '—' : `${Number(v).toLocaleString(undefined, { maximumFractionDigits: 2 })}${suffix}`);
  const yoyTag = (v) => {
    if (v === null || v === undefined) return <Tag>—</Tag>;
    const color = v >= 0 ? 'red' : 'green';  // 中国市场习惯：红涨绿跌
    return <Tag color={color}>{v >= 0 ? '+' : ''}{v.toFixed(2)}%</Tag>;
  };

  const trendCols = [
    { title: '报告期', dataIndex: 'report_date', key: 'report_date' },
    { title: '营收(元)', dataIndex: 'revenue', key: 'revenue', render: (v) => fmt(v) },
    { title: '营收同比', dataIndex: 'revenue_yoy', key: 'revenue_yoy', render: yoyTag },
    { title: '归母净利(元)', dataIndex: 'net_profit', key: 'net_profit', render: (v) => fmt(v) },
    { title: '净利同比', dataIndex: 'profit_yoy', key: 'profit_yoy', render: yoyTag },
    { title: '加权ROE', dataIndex: 'roe', key: 'roe', render: (v) => fmt(v, '%') },
    { title: '基本EPS', dataIndex: 'eps', key: 'eps', render: (v) => fmt(v) },
  ];

  return (
    <div>
      <Card title="财报快评（draft）" extra={
        <Space>
          <Input.Search
            defaultValue={code}
            style={{ width: 200 }}
            placeholder="股票代码"
            onSearch={(v) => { if (v) { setCode(v); load(v); navigate(`/earnings/${v}`); } }}
          />
          <Button onClick={() => load(code)} loading={loading}>刷新</Button>
        </Space>
      }>
        {loading && <Spin />}
        {error && <Alert type="error" message={error} />}
        {!loading && !error && !data && <Empty />}
        {data && data.available && (
          <>
            <Alert
              type="info"
              showIcon
              message={data.headline}
              description={`报告期：${data.period}　|　${data.disclaimer}`}
              style={{ marginBottom: 16 }}
            />
            <Descriptions bordered column={3} size="small" style={{ marginBottom: 16 }}>
              <Descriptions.Item label="营业收入">{fmt(data.key_metrics.revenue)}</Descriptions.Item>
              <Descriptions.Item label="归母净利">{fmt(data.key_metrics.net_profit)}</Descriptions.Item>
              <Descriptions.Item label="加权ROE">{fmt(data.key_metrics.roe, '%')}</Descriptions.Item>
              <Descriptions.Item label="基本EPS">{fmt(data.key_metrics.eps)}</Descriptions.Item>
              <Descriptions.Item label="扣非EPS">{fmt(data.key_metrics.eps_deducted)}</Descriptions.Item>
              <Descriptions.Item label="营收同比">{yoyTag(data.key_metrics.revenue_yoy)}</Descriptions.Item>
              <Descriptions.Item label="净利同比">{yoyTag(data.key_metrics.profit_yoy)}</Descriptions.Item>
              <Descriptions.Item label="营收环比">{yoyTag(data.key_metrics.revenue_qoq)}</Descriptions.Item>
              <Descriptions.Item label="净利环比">{yoyTag(data.key_metrics.profit_qoq)}</Descriptions.Item>
            </Descriptions>

            {data.red_flags?.length > 0 && (
              <Alert
                type="warning"
                showIcon
                message="自动识别风险点（需人工复核）"
                description={<ul style={{ marginBottom: 0 }}>{data.red_flags.map((f, i) => <li key={i}>{f}</li>)}</ul>}
                style={{ marginBottom: 16 }}
              />
            )}

            <Card type="inner" title="多期趋势" size="small">
              <Table
                rowKey="report_date"
                size="small"
                pagination={false}
                dataSource={data.trend}
                columns={trendCols}
              />
            </Card>
          </>
        )}
      </Card>
    </div>
  );
}
