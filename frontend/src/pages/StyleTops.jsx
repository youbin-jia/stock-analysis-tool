import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card, Row, Col, Table, Tag, Tabs, Button, Spin, Empty, Typography, Space,
  Progress, message, Tooltip,
} from 'antd';
import {
  TrophyOutlined, ReloadOutlined, BookOutlined, ThunderboltOutlined,
  RiseOutlined, FallOutlined, InfoCircleOutlined,
} from '@ant-design/icons';
import axios from 'axios';

const { Title, Text, Paragraph } = Typography;

const STYLE_COLORS = {
  graham_deep_value: '#1677ff',
  buffett_quality: '#722ed1',
  lynch_growth: '#52c41a',
  marks_defensive: '#fa8c16',
};
const SCORE_COLOR = (s) => s >= 75 ? '#52c41a' : s >= 50 ? '#faad14' : '#ff4d4f';

export default function StyleTops() {
  const navigate = useNavigate();
  const [tops, setTops] = useState(null);
  const [state, setState] = useState({ status: 'idle' });
  const [loading, setLoading] = useState(true);
  const [polling, setPolling] = useState(false);

  const loadTops = useCallback(async () => {
    try {
      const { data } = await axios.get('/api/quant/style-tops', { params: { limit: 10 } });
      setTops(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadState = useCallback(async () => {
    try {
      const { data } = await axios.get('/api/quant/bulk-scan/state');
      setState(data);
      return data;
    } catch (e) {
      return null;
    }
  }, []);

  useEffect(() => {
    loadTops();
    loadState();
  }, [loadTops, loadState]);

  // 轮询扫描状态
  useEffect(() => {
    if (!polling) return;
    const id = setInterval(async () => {
      const s = await loadState();
      if (s && (s.status === 'done' || s.status === 'failed')) {
        setPolling(false);
        loadTops();
        if (s.status === 'done') message.success('扫描完成');
        else message.error('扫描失败：' + s.message);
      }
    }, 3000);
    return () => clearInterval(id);
  }, [polling, loadState, loadTops]);

  const startScan = async () => {
    try {
      const { data } = await axios.post('/api/quant/bulk-scan/start', null, {
        params: { max_candidates: 800 },
      });
      if (data.started) {
        message.info('扫描已启动，预计需要几分钟');
        setPolling(true);
      } else {
        message.warning('已有扫描任务在运行中');
        setPolling(true);
      }
      setState(data.state);
    } catch (e) {
      message.error('启动失败');
    }
  };

  const renderChange = (val) => {
    if (val == null) return '-';
    const color = val > 0 ? '#ff4d4f' : val < 0 ? '#52c41a' : 'var(--text-primary)';
    return (
      <span style={{ color, fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>
        {val > 0 ? '+' : ''}{Number(val).toFixed(2)}%
      </span>
    );
  };

  const makeColumns = (styleKey) => [
    {
      title: '#', width: 50,
      render: (_, __, i) => (
        <span style={{
          fontWeight: 700,
          color: i < 3 ? '#ff4d4f' : 'var(--text-primary)',
          fontSize: 14,
        }}>{i + 1}</span>
      ),
    },
    {
      title: '股票', width: 160,
      render: (_, r) => (
        <div style={{ cursor: 'pointer' }} onClick={() => navigate(`/detail/${r.code}`)}>
          <div style={{ fontWeight: 600, color: 'var(--accent)' }}>{r.name}</div>
          <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{r.code}</div>
        </div>
      ),
    },
    {
      title: '流派得分',
      width: 140,
      render: (_, r) => {
        const s = r.style_scores?.[styleKey] || {};
        return (
          <Space size={6}>
            <Text strong style={{ color: SCORE_COLOR(s.score || 0), fontSize: 16 }}>
              {s.score ?? '-'}
            </Text>
            <Tag style={{ margin: 0 }}>{s.passed_count}/{s.total_rules}</Tag>
          </Space>
        );
      },
    },
    { title: '最新价', dataIndex: 'price', width: 80,
      render: (v) => v ? Number(v).toFixed(2) : '-' },
    { title: '涨跌幅', dataIndex: 'change_percent', width: 90, render: renderChange },
    {
      title: 'PE',
      dataIndex: 'pe_ttm',
      width: 80,
      sorter: (a, b) => (a.pe_ttm || 0) - (b.pe_ttm || 0),
      render: (v) => v ? Number(v).toFixed(2) : '-',
    },
    {
      title: 'PB',
      dataIndex: 'pb',
      width: 70,
      sorter: (a, b) => (a.pb || 0) - (b.pb || 0),
      render: (v) => v ? Number(v).toFixed(2) : '-',
    },
    {
      title: 'ROE',
      dataIndex: 'roe',
      width: 80,
      sorter: (a, b) => (a.roe || 0) - (b.roe || 0),
      render: (v) => v ? `${(v * 100).toFixed(2)}%` : '-',
    },
    {
      title: '营收增速',
      dataIndex: 'revenue_growth',
      width: 90,
      render: (v) => v ? `${(v * 100).toFixed(1)}%` : '-',
    },
    {
      title: '利润增速',
      dataIndex: 'net_profit_growth',
      width: 90,
      render: (v) => v ? `${(v * 100).toFixed(1)}%` : '-',
    },
    {
      title: '负债率',
      dataIndex: 'debt_ratio',
      width: 80,
      render: (v) => v ? `${(v * 100).toFixed(1)}%` : '-',
    },
    {
      title: '操作', width: 120,
      render: (_, r) => (
        <Button size="small" type="link"
          onClick={() => navigate(`/style-insight?code=${r.code}`)}>
          <TrophyOutlined /> 详细评分
        </Button>
      ),
    },
  ];

  const renderScanBar = () => {
    if (state.status === 'running') {
      const pct = state.total > 0 ? Math.round((state.progress / state.total) * 100) : 0;
      return (
        <Card style={{ marginBottom: 16, background: 'var(--bg-card)' }}>
          <Space direction="vertical" style={{ width: '100%' }}>
            <Space>
              <Spin size="small" />
              <Text strong>扫描进行中</Text>
              <Text type="secondary">{state.message}</Text>
            </Space>
            <Progress percent={pct} status="active"
              format={(p) => `${p}% (${state.progress}/${state.total})`} />
          </Space>
        </Card>
      );
    }
    return null;
  };

  if (loading) return <Spin />;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
        <div>
          <Title level={3} style={{ color: 'var(--text-primary)', margin: 0 }}>
            <TrophyOutlined /> 全市场流派 Top10
          </Title>
          <Text type="secondary">
            基于经典投资经验扫描全市场，从 4 大流派视角各选出最匹配的 Top10 股票
          </Text>
        </div>
        <Space>
          {tops?.scanned_at && (
            <Tooltip title={`覆盖 ${tops.total_stocks} 只 / 候选 ${tops.candidates} 只 / 评分 ${tops.total_scored} 只`}>
              <Tag icon={<InfoCircleOutlined />}>
                最近扫描：{tops.scanned_at.replace('T', ' ')}
              </Tag>
            </Tooltip>
          )}
          <Button type="primary" icon={<ReloadOutlined />}
            loading={state.status === 'running' || polling}
            onClick={startScan}>
            {tops?.available ? '重新扫描' : '开始扫描'}
          </Button>
        </Space>
      </div>

      {renderScanBar()}

      {!tops?.available ? (
        <Card style={{ background: 'var(--bg-card)' }}>
          <Empty description={
            <span>
              暂无扫描结果。<br />
              <Text type="secondary">点击右上角「开始扫描」按钮启动全市场扫描（耗时数分钟）</Text>
            </span>
          } />
        </Card>
      ) : (
        <Tabs
          defaultActiveKey="graham_deep_value"
          items={Object.entries(tops.tops).map(([key, info]) => ({
            key,
            label: (
              <Space>
                <span style={{ color: STYLE_COLORS[key] }}>●</span>
                {info.style_name}
                <Tag color="blue">{info.data?.length || 0}</Tag>
              </Space>
            ),
            children: (
              <Card style={{ background: 'var(--bg-card)' }}>
                <Row gutter={[16, 8]} style={{ marginBottom: 12 }}>
                  <Col span={24}>
                    <div style={{
                      borderLeft: `3px solid ${STYLE_COLORS[key]}`,
                      paddingLeft: 12,
                    }}>
                      <Text strong style={{ color: STYLE_COLORS[key], fontSize: 15 }}>
                        {info.style_name}
                      </Text>
                      <div style={{ marginTop: 4, color: 'var(--text-secondary)', fontStyle: 'italic' }}>
                        "{info.key_principle}"
                      </div>
                      <div style={{ marginTop: 6 }}>
                        {info.books?.map(b => (
                          <Tag key={b} icon={<BookOutlined />}
                            style={{ cursor: 'pointer' }}
                            onClick={() => navigate(`/books/${b}`)}>
                            {b}
                          </Tag>
                        ))}
                      </div>
                    </div>
                  </Col>
                </Row>
                <Table
                  size="small"
                  rowKey="code"
                  columns={makeColumns(key)}
                  dataSource={info.data || []}
                  pagination={false}
                  scroll={{ x: 1100 }}
                  locale={{ emptyText: '该流派暂无符合条件的股票（需至少通过 3 条规则）' }}
                />
              </Card>
            ),
          }))}
        />
      )}
    </div>
  );
}
