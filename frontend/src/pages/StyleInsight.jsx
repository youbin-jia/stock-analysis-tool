import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card, Row, Col, Tag, Input, Spin, Empty, Typography, Space, Progress,
  Tabs, Alert, Tooltip, Button, Divider, Statistic,
} from 'antd';
import {
  CheckCircleFilled, CloseCircleFilled, QuestionCircleOutlined,
  TrophyOutlined, BookOutlined, FireOutlined, ThunderboltOutlined,
  RiseOutlined, FallOutlined,
} from '@ant-design/icons';
import axios from 'axios';

const { Title, Paragraph, Text } = Typography;

const STYLE_COLORS = {
  graham_deep_value: '#1677ff',
  buffett_quality: '#722ed1',
  lynch_growth: '#52c41a',
  marks_defensive: '#fa8c16',
};

const SCORE_COLOR = (s) => s >= 75 ? '#52c41a' : s >= 50 ? '#faad14' : '#ff4d4f';

const POPULAR = [
  { code: '600519', name: '贵州茅台' },
  { code: '000858', name: '五粮液' },
  { code: '600036', name: '招商银行' },
  { code: '601318', name: '中国平安' },
  { code: '000333', name: '美的集团' },
  { code: '002594', name: '比亚迪' },
  { code: '300750', name: '宁德时代' },
  { code: '600276', name: '恒瑞医药' },
  { code: '601398', name: '工商银行' },
  { code: '600900', name: '长江电力' },
];

export default function StyleInsight() {
  const navigate = useNavigate();
  const [code, setCode] = useState('600519');
  const [inputCode, setInputCode] = useState('600519');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [cycle, setCycle] = useState(null);
  const [styles, setStyles] = useState([]);

  const fetchData = (c) => {
    setLoading(true);
    axios.get(`/api/quant/style-score/${c}`)
      .then(r => setData(r.data))
      .catch(e => console.error(e))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    axios.get('/api/quant/styles').then(r => setStyles(r.data));
    axios.get('/api/quant/market-cycle').then(r => setCycle(r.data)).catch(() => {});
  }, []);

  useEffect(() => { fetchData(code); }, [code]);

  const handleSearch = () => {
    if (inputCode && /^\d{6}$/.test(inputCode)) setCode(inputCode);
  };

  return (
    <div>
      <div style={{ marginBottom: 20 }}>
        <Title level={3} style={{ color: 'var(--text-primary)', marginBottom: 4 }}>
          <TrophyOutlined /> 流派洞察 · 经验驱动评分
        </Title>
        <Text type="secondary">
          基于经典投资著作提炼的可量化规则，从 4 大流派视角评估个股，逐条展示触发的书籍经验。
        </Text>
      </div>

      {/* 市场周期解读 */}
      {cycle && cycle.interpretation && (() => {
        const c = cycle.interpretation.color;
        const palette = {
          red:    { bg: 'rgba(255, 77, 79, 0.12)',  border: '#ff4d4f', accent: '#ff4d4f' },
          orange: { bg: 'rgba(250, 140, 22, 0.12)', border: '#fa8c16', accent: '#fa8c16' },
          green:  { bg: 'rgba(82, 196, 26, 0.12)',  border: '#52c41a', accent: '#52c41a' },
          cyan:   { bg: 'rgba(19, 194, 194, 0.12)', border: '#13c2c2', accent: '#13c2c2' },
          blue:   { bg: 'rgba(22, 119, 255, 0.12)', border: '#1677ff', accent: '#1677ff' },
        }[c] || { bg: 'var(--bg-card)', border: '#1677ff', accent: '#1677ff' };

        return (
          <div
            style={{
              marginBottom: 16,
              padding: '14px 18px',
              background: palette.bg,
              borderLeft: `4px solid ${palette.border}`,
              borderRadius: 6,
              color: 'var(--text-primary)',
            }}
          >
            <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 10 }}>
              <Text strong style={{ color: 'var(--text-primary)', fontSize: 15 }}>
                市场温度：<span style={{ color: palette.accent }}>{cycle.interpretation.temperature}</span>
              </Text>
              <Tag color={c}>{cycle.interpretation.sentiment}</Tag>
              <Text style={{ color: 'var(--text-secondary)' }}>
                估值平均分位 <Text strong style={{ color: 'var(--text-primary)' }}>{cycle.interpretation.avg_percentile}%</Text>
              </Text>
              <Text style={{ color: 'var(--text-secondary)' }}>
                | PE中位 {cycle.market.pe_ttm_median}（分位 {cycle.market.pe_percentile}%）
              </Text>
              <Text style={{ color: 'var(--text-secondary)' }}>
                | PB中位 {cycle.market.pb_median}（分位 {cycle.market.pb_percentile}%）
              </Text>
            </div>

            <div style={{ marginTop: 8, color: 'var(--text-primary)', lineHeight: 1.6 }}>
              {cycle.interpretation.suggestion}
            </div>

            <div style={{ marginTop: 10, display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 8 }}>
              <Text strong style={{ color: palette.accent }}>建议动作：</Text>
              <Text style={{ color: 'var(--text-primary)' }}>{cycle.interpretation.action}</Text>
              <span style={{ marginLeft: 4, display: 'inline-flex', flexWrap: 'wrap', gap: 4 }}>
                {cycle.interpretation.references.map(r => (
                  <Tag key={r.book} icon={<BookOutlined />} style={{ margin: 0 }}>
                    {r.book} · {r.principle}
                  </Tag>
                ))}
              </span>
            </div>
          </div>
        );
      })()}

      {/* 输入框 */}
      <Card style={{ marginBottom: 16, background: 'var(--bg-card)' }}>
        <Space wrap>
          <Input.Search
            placeholder="输入6位股票代码"
            value={inputCode}
            onChange={(e) => setInputCode(e.target.value)}
            onSearch={handleSearch}
            enterButton="评估"
            style={{ width: 280 }}
          />
          <Text type="secondary">快捷：</Text>
          {POPULAR.map(s => (
            <Tag
              key={s.code}
              style={{ cursor: 'pointer' }}
              color={s.code === code ? 'blue' : 'default'}
              onClick={() => { setInputCode(s.code); setCode(s.code); }}
            >
              {s.name}
            </Tag>
          ))}
        </Space>
      </Card>

      <Spin spinning={loading}>
        {!data ? <Empty /> : (
          <>
            {/* 头部摘要 */}
            <Card style={{ marginBottom: 16, background: 'var(--bg-card)' }}>
              <Row gutter={24} align="middle">
                <Col xs={24} md={8}>
                  <Title level={4} style={{ margin: 0, color: 'var(--text-primary)' }}>
                    {data.name || data.code} <Text type="secondary" style={{ fontSize: 14 }}>{data.code}</Text>
                  </Title>
                  <div style={{ marginTop: 8 }}>
                    <Button size="small" onClick={() => navigate(`/detail/${data.code}`)}>查看行情</Button>
                  </div>
                </Col>
                <Col xs={12} md={4}>
                  <Statistic title="综合评分" value={data.composite_score} suffix="/100"
                    valueStyle={{ color: SCORE_COLOR(data.composite_score), fontSize: 28 }} />
                </Col>
                <Col xs={24} md={12}>
                  <div style={{
                    padding: '12px 16px',
                    borderLeft: `4px solid ${STYLE_COLORS[data.best_style.key]}`,
                    background: 'var(--bg-secondary)',
                    borderRadius: 4,
                  }}>
                    <Text type="secondary">最佳匹配流派</Text>
                    <div style={{ marginTop: 4 }}>
                      <Text strong style={{ color: STYLE_COLORS[data.best_style.key], fontSize: 16 }}>
                        <FireOutlined /> {data.best_style.name}
                      </Text>
                      <Text strong style={{ marginLeft: 12, color: SCORE_COLOR(data.best_style.score) }}>
                        {data.best_style.score} 分
                      </Text>
                    </div>
                    <div style={{ marginTop: 6, color: 'var(--text-secondary)', fontStyle: 'italic' }}>
                      "{data.best_style.key_principle}"
                    </div>
                  </div>
                </Col>
              </Row>

              <Divider style={{ margin: '16px 0' }} />

              {/* 关键基本面 */}
              <Row gutter={[16, 12]}>
                <Col xs={12} sm={6} md={3}>
                  <Statistic title="PE(TTM)" value={data.fundamental.pe_ttm || '-'}
                    valueStyle={{ fontSize: 16 }} />
                </Col>
                <Col xs={12} sm={6} md={3}>
                  <Statistic title="PB" value={data.fundamental.pb || '-'}
                    valueStyle={{ fontSize: 16 }} />
                </Col>
                <Col xs={12} sm={6} md={3}>
                  <Statistic title="ROE" value={data.fundamental.roe ? (data.fundamental.roe * 100).toFixed(2) : '-'}
                    suffix="%" valueStyle={{ fontSize: 16 }} />
                </Col>
                <Col xs={12} sm={6} md={3}>
                  <Statistic title="净利率" value={data.fundamental.net_profit_margin ? (data.fundamental.net_profit_margin * 100).toFixed(2) : '-'}
                    suffix="%" valueStyle={{ fontSize: 16 }} />
                </Col>
                <Col xs={12} sm={6} md={3}>
                  <Statistic title="营收增速" value={data.fundamental.revenue_growth ? (data.fundamental.revenue_growth * 100).toFixed(2) : '-'}
                    suffix="%" valueStyle={{ fontSize: 16 }} />
                </Col>
                <Col xs={12} sm={6} md={3}>
                  <Statistic title="利润增速" value={data.fundamental.net_profit_growth ? (data.fundamental.net_profit_growth * 100).toFixed(2) : '-'}
                    suffix="%" valueStyle={{ fontSize: 16 }} />
                </Col>
                <Col xs={12} sm={6} md={3}>
                  <Statistic title="负债率" value={data.fundamental.debt_ratio ? (data.fundamental.debt_ratio * 100).toFixed(2) : '-'}
                    suffix="%" valueStyle={{ fontSize: 16 }} />
                </Col>
                <Col xs={12} sm={6} md={3}>
                  <Statistic title="股息率" value={data.fundamental.dividend_yield || '-'}
                    suffix="%" valueStyle={{ fontSize: 16 }} />
                </Col>
              </Row>
            </Card>

            {/* 流派评分对比 */}
            <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
              {data.styles.map(s => (
                <Col key={s.key} xs={24} sm={12} lg={6}>
                  <Card
                    style={{
                      background: 'var(--bg-card)',
                      borderTop: `3px solid ${STYLE_COLORS[s.key]}`,
                      height: '100%',
                    }}
                  >
                    <Title level={5} style={{ margin: 0, color: STYLE_COLORS[s.key] }}>
                      {s.name}
                    </Title>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {s.books.map(b => <Tag key={b} style={{ marginRight: 4, fontSize: 11 }}>{b}</Tag>)}
                    </Text>
                    <div style={{ margin: '12px 0' }}>
                      <Progress
                        percent={s.score}
                        strokeColor={SCORE_COLOR(s.score)}
                        format={(p) => <span style={{ color: SCORE_COLOR(s.score), fontWeight: 700 }}>{p}</span>}
                      />
                      <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>
                        通过 {s.passed_count} / {s.total_rules} 条规则
                      </div>
                    </div>
                    <Paragraph
                      style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 0 }}
                      ellipsis={{ rows: 2 }}
                    >
                      {s.description}
                    </Paragraph>
                  </Card>
                </Col>
              ))}
            </Row>

            {/* 规则详情 Tab */}
            <Tabs
              defaultActiveKey={data.best_style.key}
              items={data.styles.map(s => ({
                key: s.key,
                label: (
                  <Space>
                    <span style={{ color: STYLE_COLORS[s.key] }}>●</span>
                    {s.name}
                    <Tag color={SCORE_COLOR(s.score)}>{s.score}</Tag>
                  </Space>
                ),
                children: (
                  <Card style={{ background: 'var(--bg-card)' }}>
                    <div
                      style={{
                        marginBottom: 16,
                        padding: '12px 16px',
                        background: `${STYLE_COLORS[s.key]}1a`,  /* 10% 透明度 */
                        borderLeft: `4px solid ${STYLE_COLORS[s.key]}`,
                        borderRadius: 6,
                      }}
                    >
                      <Space wrap>
                        <BookOutlined style={{ color: STYLE_COLORS[s.key] }} />
                        <Text strong style={{ color: STYLE_COLORS[s.key] }}>核心理念：</Text>
                        <Text italic style={{ color: 'var(--text-primary)' }}>
                          "{s.key_principle}"
                        </Text>
                      </Space>
                      <div style={{ marginTop: 6, color: 'var(--text-secondary)', fontSize: 13 }}>
                        {s.description}
                      </div>
                    </div>
                    <Row gutter={[12, 12]}>
                      {s.rules.map((r, i) => (
                        <Col key={i} xs={24} md={12}>
                          <Card
                            size="small"
                            style={{
                              background: r.passed ? 'rgba(82, 196, 26, 0.06)' : 'rgba(255, 77, 79, 0.04)',
                              borderLeft: `3px solid ${r.passed ? '#52c41a' : '#ff4d4f'}`,
                            }}
                          >
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                              <div style={{ flex: 1 }}>
                                <Space>
                                  {r.passed
                                    ? <CheckCircleFilled style={{ color: '#52c41a' }} />
                                    : <CloseCircleFilled style={{ color: '#ff4d4f' }} />}
                                  <Text strong style={{ color: 'var(--text-primary)' }}>{r.rule}</Text>
                                </Space>
                                <div style={{ marginTop: 6, fontSize: 13, color: 'var(--text-secondary)' }}>
                                  {r.comment}
                                </div>
                              </div>
                              <Tooltip title={`点击查看《${r.book}》详情`}>
                                <Tag
                                  icon={<BookOutlined />}
                                  style={{ cursor: 'pointer' }}
                                  onClick={() => navigate('/books')}
                                >
                                  {r.book}
                                </Tag>
                              </Tooltip>
                            </div>
                          </Card>
                        </Col>
                      ))}
                    </Row>
                  </Card>
                ),
              }))}
            />
          </>
        )}
      </Spin>

      {/* 流派说明 */}
      <Card style={{ marginTop: 16, background: 'var(--bg-card)' }} title={<><BookOutlined /> 四大流派对照</>}>
        <Row gutter={[16, 16]}>
          {styles.map(s => (
            <Col key={s.key} xs={24} md={12}>
              <div style={{ borderLeft: `3px solid ${STYLE_COLORS[s.key]}`, paddingLeft: 12 }}>
                <Text strong style={{ color: STYLE_COLORS[s.key] }}>{s.name}</Text>
                <Paragraph style={{ marginBottom: 4, color: 'var(--text-secondary)' }}>
                  {s.description}
                </Paragraph>
                <Text italic type="secondary">"{s.key_principle}"</Text>
              </div>
            </Col>
          ))}
        </Row>
      </Card>
    </div>
  );
}
