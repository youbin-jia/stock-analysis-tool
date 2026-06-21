import { useEffect, useState, useCallback } from 'react';
import {
  Card, Row, Col, Tag, Button, Spin, Empty, Typography, Space, Tabs,
  Progress, message, Tooltip, Alert, List, Divider,
} from 'antd';
import {
  ReloadOutlined, FireOutlined, BulbOutlined, RiseOutlined,
  WarningOutlined, LinkOutlined, GlobalOutlined, RobotOutlined,
  ThunderboltOutlined, SafetyOutlined,
} from '@ant-design/icons';
import axios from 'axios';

const { Title, Paragraph, Text } = Typography;

const SOURCE_COLOR = {
  '求是网': '#ff4d4f',
  '新华网': '#1677ff',
  '中国政府网': '#722ed1',
};

const SIGNAL_COLOR = {
  '扶持': 'green',
  '规范': 'orange',
  '中性': 'default',
};

export default function PolicyInsight() {
  const [data, setData] = useState(null);
  const [state, setState] = useState({ status: 'idle' });
  const [loading, setLoading] = useState(true);
  const [polling, setPolling] = useState(false);

  const loadResult = useCallback(async () => {
    try {
      const { data: r } = await axios.get('/api/policy/result');
      if (r.available) setData(r);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, []);

  const loadState = useCallback(async () => {
    try {
      const { data: s } = await axios.get('/api/policy/state');
      setState(s);
      return s;
    } catch (e) { return null; }
  }, []);

  useEffect(() => { loadResult(); loadState(); }, [loadResult, loadState]);

  useEffect(() => {
    if (!polling) return;
    const id = setInterval(async () => {
      const s = await loadState();
      if (s && (s.status === 'done' || s.status === 'failed')) {
        setPolling(false);
        loadResult();
        if (s.status === 'done') message.success('刷新完成');
        else message.error('刷新失败：' + s.message);
      }
    }, 3000);
    return () => clearInterval(id);
  }, [polling, loadState, loadResult]);

  const refresh = async () => {
    try {
      const { data: r } = await axios.post('/api/policy/refresh', null, {
        params: { days: 30, max_articles: 40 },
      });
      if (r.started) {
        message.info('已启动刷新，AI 分析需 2-3 分钟');
        setPolling(true);
        setState(r.state);
      } else {
        message.warning('已有任务在运行');
        setPolling(true);
      }
    } catch (e) {
      message.error('启动失败');
    }
  };

  const renderScanBar = () => {
    if (state.status !== 'running') return null;
    const pct = state.total > 0 ? Math.round((state.progress / state.total) * 100) : 0;
    return (
      <Card style={{ marginBottom: 16, background: 'var(--bg-card)' }}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Space>
            <Spin size="small" />
            <Text strong>政策抓取与 AI 分析中</Text>
            <Text type="secondary">{state.message}</Text>
          </Space>
          <Progress percent={pct} status="active"
            format={() => `${state.progress}/${state.total}`} />
        </Space>
      </Card>
    );
  };

  if (loading) return <Spin />;

  const agg = data?.aggregate || {};

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
        <div>
          <Title level={3} style={{ color: 'var(--text-primary)', margin: 0 }}>
            <GlobalOutlined /> 政策风向
          </Title>
          <Text type="secondary">
            汇集求是、新华、政府网近 30 天政策文章，使用 Kimi 大模型提炼投资方向与策略
          </Text>
        </div>
        <Space>
          {data?.collected_at && (
            <Tag>最近更新：{data.collected_at.replace('T', ' ')}</Tag>
          )}
          <Button type="primary" icon={<ReloadOutlined />}
            loading={state.status === 'running' || polling}
            onClick={refresh}>
            一键刷新近 30 天
          </Button>
        </Space>
      </div>

      {renderScanBar()}

      {!data ? (
        <Card style={{ background: 'var(--bg-card)' }}>
          <Empty description={
            <span>
              暂无数据。<br />
              <Text type="secondary">点击右上角「一键刷新」启动抓取与 AI 分析</Text>
            </span>
          } />
        </Card>
      ) : (
        <>
          {/* 宏观概览 */}
          {agg.macro_overview && (
            <div style={{
              marginBottom: 16,
              padding: '14px 18px',
              background: 'rgba(22, 119, 255, 0.10)',
              borderLeft: '4px solid #1677ff',
              borderRadius: 6,
            }}>
              <Space>
                <BulbOutlined style={{ color: '#1677ff', fontSize: 18 }} />
                <Text strong style={{ color: '#1677ff' }}>近一月宏观主基调</Text>
              </Space>
              <Paragraph style={{ marginTop: 8, marginBottom: 0, color: 'var(--text-primary)', lineHeight: 1.7 }}>
                {agg.macro_overview}
              </Paragraph>
            </div>
          )}

          <Row gutter={[16, 16]}>
            {/* 左：投资方向 + 信号 */}
            <Col xs={24} lg={14}>
              <Card title={<><RiseOutlined /> AI 提炼的投资方向</>}
                style={{ background: 'var(--bg-card)' }}>
                {(agg.investment_directions || []).length === 0 ? (
                  <Empty description="暂无方向" />
                ) : (
                  <List
                    dataSource={agg.investment_directions || []}
                    renderItem={(d, i) => (
                      <List.Item style={{ borderColor: 'var(--border-color)' }}>
                        <div style={{ width: '100%' }}>
                          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
                            <Tag color="blue" style={{ fontSize: 14, padding: '2px 10px' }}>#{i + 1}</Tag>
                            <div style={{ flex: 1 }}>
                              <Text strong style={{ color: 'var(--text-primary)', fontSize: 15 }}>
                                {d.direction}
                              </Text>
                              <div style={{ marginTop: 4, color: 'var(--text-secondary)' }}>
                                {d.rationale}
                              </div>
                              <div style={{ marginTop: 6 }}>
                                {(d.industries || []).map(ind => (
                                  <Tag key={ind} color="cyan">{ind}</Tag>
                                ))}
                              </div>
                              {d.risk && (
                                <div style={{ marginTop: 6, fontSize: 12, color: '#fa8c16' }}>
                                  <WarningOutlined /> 风险：{d.risk}
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      </List.Item>
                    )}
                  />
                )}
              </Card>

              {/* 政策信号 */}
              {agg.policy_signals && (
                <Card title={<><SafetyOutlined /> 政策信号矩阵</>}
                  style={{ marginTop: 16, background: 'var(--bg-card)' }}>
                  <Row gutter={[12, 12]}>
                    <Col span={8}>
                      <div style={{
                        padding: 12, background: 'rgba(82, 196, 26, 0.1)',
                        borderLeft: '3px solid #52c41a', borderRadius: 4,
                      }}>
                        <Text strong style={{ color: '#52c41a' }}>扶持</Text>
                        <ul style={{ paddingLeft: 18, marginTop: 6, marginBottom: 0, color: 'var(--text-primary)' }}>
                          {(agg.policy_signals.positive || []).map((x, i) => <li key={i}>{x}</li>)}
                        </ul>
                      </div>
                    </Col>
                    <Col span={8}>
                      <div style={{
                        padding: 12, background: 'rgba(250, 173, 20, 0.1)',
                        borderLeft: '3px solid #faad14', borderRadius: 4,
                      }}>
                        <Text strong style={{ color: '#faad14' }}>规范</Text>
                        <ul style={{ paddingLeft: 18, marginTop: 6, marginBottom: 0, color: 'var(--text-primary)' }}>
                          {(agg.policy_signals.neutral || []).map((x, i) => <li key={i}>{x}</li>)}
                        </ul>
                      </div>
                    </Col>
                    <Col span={8}>
                      <div style={{
                        padding: 12, background: 'rgba(255, 77, 79, 0.1)',
                        borderLeft: '3px solid #ff4d4f', borderRadius: 4,
                      }}>
                        <Text strong style={{ color: '#ff4d4f' }}>谨慎</Text>
                        <ul style={{ paddingLeft: 18, marginTop: 6, marginBottom: 0, color: 'var(--text-primary)' }}>
                          {(agg.policy_signals.cautious || []).map((x, i) => <li key={i}>{x}</li>)}
                        </ul>
                      </div>
                    </Col>
                  </Row>
                </Card>
              )}
            </Col>

            {/* 右：主题/行业热度 */}
            <Col xs={24} lg={10}>
              <Card title={<><FireOutlined /> 主题热度</>}
                style={{ background: 'var(--bg-card)' }}>
                <Space wrap>
                  {(data.topic_rank || []).slice(0, 20).map(t => (
                    <Tag key={t.topic} color="magenta"
                      style={{ fontSize: 13, padding: '4px 10px' }}>
                      {t.topic} <Text strong style={{ color: '#fff' }}>×{t.count}</Text>
                    </Tag>
                  ))}
                </Space>
              </Card>

              <Card title={<><ThunderboltOutlined /> 行业热度</>}
                style={{ marginTop: 16, background: 'var(--bg-card)' }}>
                <Space wrap>
                  {(data.industry_rank || []).slice(0, 20).map(t => (
                    <Tag key={t.industry} color="blue"
                      style={{ fontSize: 13, padding: '4px 10px' }}>
                      {t.industry} <Text strong style={{ color: '#fff' }}>×{t.count}</Text>
                    </Tag>
                  ))}
                </Space>
              </Card>

              {/* 关键主题 */}
              {(agg.key_themes || []).length > 0 && (
                <Card title={<><BulbOutlined /> 核心主题解读</>}
                  style={{ marginTop: 16, background: 'var(--bg-card)' }}>
                  {(agg.key_themes || []).map((t, i) => (
                    <div key={i} style={{
                      padding: '10px 0',
                      borderBottom: i < agg.key_themes.length - 1 ? '1px solid var(--border-color)' : 'none',
                    }}>
                      <Space>
                        <Text strong style={{ color: 'var(--text-primary)' }}>{t.theme}</Text>
                        <Tag color="red">权重 {t.weight}</Tag>
                      </Space>
                      <div style={{ marginTop: 4, color: 'var(--text-secondary)' }}>{t.description}</div>
                      <div style={{ marginTop: 4 }}>
                        {(t.related_industries || []).map(ind => (
                          <Tag key={ind}>{ind}</Tag>
                        ))}
                      </div>
                    </div>
                  ))}
                </Card>
              )}
            </Col>
          </Row>

          {/* 文章列表 */}
          <Card title={<><GlobalOutlined /> 政策文章 ({data.article_count})</>}
            style={{ marginTop: 16, background: 'var(--bg-card)' }}>
            <Tabs
              items={[
                { key: 'all', label: '全部', source: null },
                { key: 'qstheory', label: '求是网', source: '求是网' },
                { key: 'xinhua', label: '新华网', source: '新华网' },
                { key: 'gov', label: '中国政府网', source: '中国政府网' },
              ].map(({ key, label, source }) => {
                const list = source
                  ? data.articles.filter(a => a.source === source)
                  : data.articles;
                return {
                  key, label: `${label} (${list.length})`,
                  children: (
                    <List
                      dataSource={list}
                      pagination={{ pageSize: 10, size: 'small' }}
                      renderItem={(a) => (
                        <List.Item style={{ borderColor: 'var(--border-color)' }}>
                          <div style={{ width: '100%' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 }}>
                              <a href={a.url} target="_blank" rel="noopener noreferrer"
                                style={{ color: 'var(--accent)', fontWeight: 600, fontSize: 15, flex: 1 }}>
                                {a.title} <LinkOutlined style={{ fontSize: 12 }} />
                              </a>
                              <Space size={4}>
                                <Tag color={SOURCE_COLOR[a.source]}>{a.source}</Tag>
                                {a.date && <Tag>{a.date}</Tag>}
                                {a.ai?.policy_signal && (
                                  <Tag color={SIGNAL_COLOR[a.ai.policy_signal]}>{a.ai.policy_signal}</Tag>
                                )}
                              </Space>
                            </div>
                            {a.ai?.summary && (
                              <div style={{
                                marginTop: 8, padding: '8px 12px',
                                background: 'var(--bg-secondary)', borderRadius: 4,
                                color: 'var(--text-primary)', fontSize: 13,
                              }}>
                                <Text strong style={{ color: '#1677ff' }}>
                                  <RobotOutlined /> AI 摘要：
                                </Text>
                                {a.ai.summary}
                                {a.ai.investment_impact && (
                                  <div style={{ marginTop: 4, color: '#52c41a' }}>
                                    <RiseOutlined /> 投资影响：{a.ai.investment_impact}
                                  </div>
                                )}
                              </div>
                            )}
                            <div style={{ marginTop: 6 }}>
                              {(a.ai?.topics || []).map(t => (
                                <Tag key={t} color="magenta" style={{ marginBottom: 4 }}>{t}</Tag>
                              ))}
                              {(a.ai?.industries || []).map(t => (
                                <Tag key={t} color="cyan" style={{ marginBottom: 4 }}>{t}</Tag>
                              ))}
                            </div>
                          </div>
                        </List.Item>
                      )}
                    />
                  ),
                };
              })}
            />
          </Card>

          {/* 免责声明 */}
          <div style={{ marginTop: 16, padding: 10, textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 12 }}>
            {agg.summary_disclaimer || '本页内容由 AI 基于公开政策报道生成，仅作政策梳理，不构成投资建议。原文版权归来源所有。'}
          </div>
        </>
      )}
    </div>
  );
}
