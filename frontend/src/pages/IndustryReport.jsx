import { useEffect, useRef, useState } from 'react';
import {
  Card, Form, Select, Input, Button, Space, Tag, Spin, Alert, Drawer, List,
  Tooltip, Popconfirm, message, Empty, Statistic, Row, Col, Divider, Checkbox, AutoComplete,
} from 'antd';
import {
  HistoryOutlined, DeleteOutlined, ReloadOutlined, ThunderboltOutlined, CopyOutlined, DownloadOutlined,
} from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import axios from 'axios';

const STYLE_LABELS = { data_driven: '数据驱动', logic_driven: '逻辑驱动', stock_first: '个股优先' };

export default function IndustryReport() {
  const [form] = Form.useForm();
  const [presets, setPresets] = useState({ industries: [], focus_dims: [], styles: [] });
  const [content, setContent] = useState('');
  const [meta, setMeta] = useState(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);
  const [done, setDone] = useState(null);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [historyList, setHistoryList] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const abortRef = useRef(null);
  const previewRef = useRef(null);

  // 加载预设
  useEffect(() => {
    axios.get('/api/industry-report/presets').then(r => setPresets(r.data));
  }, []);

  // 自动滚到底
  useEffect(() => {
    if (previewRef.current && running) {
      previewRef.current.scrollTop = previewRef.current.scrollHeight;
    }
  }, [content, running]);

  const loadHistory = async () => {
    setHistoryLoading(true);
    try {
      const r = await axios.get('/api/industry-report/list?limit=100');
      setHistoryList(r.data.data || []);
    } finally { setHistoryLoading(false); }
  };

  const openHistory = () => { setHistoryOpen(true); loadHistory(); };

  const viewHistory = async (id) => {
    try {
      const r = await axios.get(`/api/industry-report/${id}`);
      setContent(r.data.content);
      setMeta({ industry: r.data.industry, model: r.data.model, from_history: true });
      setDone({ id: r.data.id, chars: r.data.tokens, duration_ms: r.data.duration_ms });
      setError(null);
      setHistoryOpen(false);
      // 回填表单
      form.setFieldsValue({
        industry: r.data.industry,
        style: r.data.style,
        custom_requirement: r.data.custom_requirement,
        focus_dims: r.data.focus_dims,
      });
    } catch (e) {
      message.error(e.response?.data?.detail || e.message);
    }
  };

  const removeHistory = async (id) => {
    await axios.delete(`/api/industry-report/${id}`);
    message.success('已删除');
    loadHistory();
  };

  const generate = async (values) => {
    if (running) return;
    setRunning(true); setError(null); setContent(''); setMeta(null); setDone(null);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const resp = await fetch('/api/industry-report/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          industry: values.industry,
          style: values.style,
          custom_requirement: values.custom_requirement || null,
          focus_dims: values.focus_dims || [],
          temperature: 0.6,
        }),
        signal: controller.signal,
      });
      if (!resp.ok) {
        const t = await resp.text();
        throw new Error(`HTTP ${resp.status}: ${t.slice(0, 200)}`);
      }

      const reader = resp.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';
      while (true) {
        const { value, done: streamDone } = await reader.read();
        if (streamDone) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop(); // 留下最后未完成的一段
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          try {
            const ev = JSON.parse(line.slice(6));
            if (ev.type === 'meta') {
              setMeta({ industry: ev.industry, model: ev.model });
            } else if (ev.type === 'delta') {
              setContent(prev => prev + ev.text);
            } else if (ev.type === 'done') {
              setDone(ev);
              message.success(`生成完成（${ev.chars} 字 / ${(ev.duration_ms / 1000).toFixed(1)}s）`);
            } else if (ev.type === 'error') {
              setError(ev.message);
              message.error(ev.message);
            }
          } catch (e) { /* skip */ }
        }
      }
    } catch (e) {
      if (e.name !== 'AbortError') {
        setError(e.message);
        message.error(e.message);
      }
    } finally {
      setRunning(false);
      abortRef.current = null;
    }
  };

  const stop = () => {
    abortRef.current?.abort();
    setRunning(false);
    message.info('已中断');
  };

  const copyContent = () => {
    navigator.clipboard.writeText(content);
    message.success('已复制到剪贴板');
  };

  const downloadMd = () => {
    const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${meta?.industry || 'report'}_${Date.now()}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div>
      <Card
        title={<><ThunderboltOutlined /> 行业研究报告生成器（Kimi 驱动）</>}
        extra={
          <Space>
            <Button icon={<HistoryOutlined />} onClick={openHistory}>历史</Button>
          </Space>
        }
      >
        <Row gutter={16}>
          {/* 左：表单 */}
          <Col xs={24} md={8}>
            <Form
              form={form}
              layout="vertical"
              initialValues={{
                industry: '半导体',
                style: 'data_driven',
                focus_dims: ['macro', 'prosperity', 'leaders', 'valuation', 'catalyst', 'risk', 'stock_map', 'tracking'],
              }}
              onFinish={generate}
            >
              <Form.Item
                label="行业（可选预置或自由输入）"
                name="industry"
                rules={[{ required: true, message: '请填行业名称' }]}
              >
                <AutoComplete
                  placeholder="如：半导体 / AI 算力硬件 / 创新药"
                  options={presets.industries.map(i => ({
                    value: i.name,
                    label: <><strong>{i.name}</strong> <span style={{ color: '#999' }}>— {i.desc}</span></>,
                  }))}
                  filterOption={(input, option) =>
                    option.value.toLowerCase().includes(input.toLowerCase())
                  }
                />
              </Form.Item>

              <Form.Item label="风格" name="style">
                <Select options={presets.styles.map(s => ({ value: s.key, label: s.name }))} />
              </Form.Item>

              <Form.Item label="关注维度（多选）" name="focus_dims">
                <Checkbox.Group style={{ display: 'flex', flexDirection: 'column' }}>
                  {presets.focus_dims.map(d => (
                    <Checkbox key={d.key} value={d.key}>{d.name}</Checkbox>
                  ))}
                </Checkbox.Group>
              </Form.Item>

              <Form.Item label="自定义要求（可选）" name="custom_requirement">
                <Input.TextArea
                  rows={5}
                  placeholder={'例：\n- 重点关注 HBM 国产替代链\n- 标的图谱必须包含寒武纪、北方华创\n- 给出 12 个月目标价'}
                />
              </Form.Item>

              <Form.Item>
                <Space>
                  {!running ? (
                    <Button type="primary" htmlType="submit" loading={running} icon={<ThunderboltOutlined />}>
                      生成报告
                    </Button>
                  ) : (
                    <Button danger onClick={stop}>中断</Button>
                  )}
                  <Button onClick={() => { setContent(''); setMeta(null); setDone(null); setError(null); }}>
                    清空
                  </Button>
                </Space>
              </Form.Item>
            </Form>
          </Col>

          {/* 右：预览 */}
          <Col xs={24} md={16}>
            <Card
              size="small"
              type="inner"
              title={
                <Space>
                  <span>报告预览</span>
                  {meta && <Tag color="blue">{meta.industry}</Tag>}
                  {meta?.model && <Tag>{meta.model}</Tag>}
                  {meta?.from_history && <Tag color="purple">历史</Tag>}
                  {running && <Tag color="processing" icon={<Spin size="small" />}>生成中</Tag>}
                </Space>
              }
              extra={
                content && (
                  <Space>
                    <Tooltip title="复制 Markdown"><Button size="small" icon={<CopyOutlined />} onClick={copyContent} /></Tooltip>
                    <Tooltip title="下载 .md 文件"><Button size="small" icon={<DownloadOutlined />} onClick={downloadMd} /></Tooltip>
                  </Space>
                )
              }
            >
              {done && (
                <Row gutter={8} style={{ marginBottom: 12 }}>
                  <Col span={8}><Statistic title="字符数" value={done.chars || 0} /></Col>
                  <Col span={8}><Statistic title="耗时" value={(done.duration_ms / 1000).toFixed(1)} suffix="s" /></Col>
                  <Col span={8}><Statistic title="报告 ID" value={done.id || '—'} /></Col>
                </Row>
              )}

              {error && <Alert type="error" message={error} style={{ marginBottom: 12 }} />}

              <div
                ref={previewRef}
                style={{
                  maxHeight: 'calc(100vh - 320px)',
                  minHeight: 400,
                  overflowY: 'auto',
                  padding: '8px 16px',
                  background: 'var(--bg-primary)',
                  border: '1px solid var(--border-color)',
                  borderRadius: 8,
                }}
                className="markdown-body"
              >
                {!content && !running && <Empty description="选择行业、添加自定义要求，点击「生成报告」" />}
                {content && (
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      table: ({ node, ...props }) => (
                        <div style={{ overflowX: 'auto', margin: '12px 0' }}>
                          <table {...props} style={{
                            borderCollapse: 'collapse',
                            width: '100%',
                            fontSize: 13,
                          }} />
                        </div>
                      ),
                      th: ({ node, ...props }) => (
                        <th {...props} style={{
                          border: '1px solid var(--border-color)',
                          padding: '6px 10px',
                          background: 'var(--bg-input)',
                          textAlign: 'left',
                        }} />
                      ),
                      td: ({ node, ...props }) => (
                        <td {...props} style={{
                          border: '1px solid var(--border-color)',
                          padding: '6px 10px',
                        }} />
                      ),
                      h1: ({ node, ...props }) => <h1 {...props} style={{ borderBottom: '2px solid var(--border-color)', paddingBottom: 8, marginTop: 24 }} />,
                      h2: ({ node, ...props }) => <h2 {...props} style={{ marginTop: 20, color: 'var(--accent)' }} />,
                      code: ({ node, inline, ...props }) =>
                        inline
                          ? <code {...props} style={{ background: 'var(--bg-input)', padding: '1px 6px', borderRadius: 4 }} />
                          : <pre style={{ background: 'var(--bg-input)', padding: 12, borderRadius: 6, overflowX: 'auto' }}><code {...props} /></pre>,
                      blockquote: ({ node, ...props }) => (
                        <blockquote {...props} style={{
                          borderLeft: '4px solid var(--accent)',
                          paddingLeft: 12,
                          color: 'var(--text-secondary)',
                          margin: '12px 0',
                        }} />
                      ),
                    }}
                  >
                    {content}
                  </ReactMarkdown>
                )}
              </div>
            </Card>
          </Col>
        </Row>
      </Card>

      <Drawer
        title={<><HistoryOutlined /> 历史报告</>}
        open={historyOpen}
        onClose={() => setHistoryOpen(false)}
        width={520}
        extra={<Button icon={<ReloadOutlined />} onClick={loadHistory}>刷新</Button>}
      >
        <Spin spinning={historyLoading}>
          {historyList.length === 0 ? <Empty /> : (
            <List
              dataSource={historyList}
              renderItem={(r) => (
                <List.Item
                  actions={[
                    <Button size="small" onClick={() => viewHistory(r.id)}>查看</Button>,
                    <Popconfirm title="确认删除？" onConfirm={() => removeHistory(r.id)}>
                      <Button size="small" danger icon={<DeleteOutlined />} />
                    </Popconfirm>,
                  ]}
                >
                  <List.Item.Meta
                    title={<Space><strong>{r.industry}</strong><Tag>{STYLE_LABELS[r.style] || r.style}</Tag></Space>}
                    description={
                      <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                        <div>#{r.id} · {r.model} · {r.tokens} 字 · {(r.duration_ms / 1000).toFixed(1)}s</div>
                        <div>{new Date(r.created_at).toLocaleString()}</div>
                      </div>
                    }
                  />
                </List.Item>
              )}
            />
          )}
        </Spin>
      </Drawer>
    </div>
  );
}
