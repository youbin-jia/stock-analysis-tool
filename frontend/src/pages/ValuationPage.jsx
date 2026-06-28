import { useState } from 'react';
import { Card, Form, InputNumber, Button, Row, Col, Table, Alert, Tabs, Input, Statistic, Tag, Spin, Descriptions, Space, Divider } from 'antd';
import axios from 'axios';

function DCFPanel() {
  const [form] = Form.useForm();
  const [result, setResult] = useState(null);
  const [sens, setSens] = useState(null);
  const [loading, setLoading] = useState(false);
  const [growthYears, setGrowthYears] = useState([0.12, 0.10, 0.08, 0.06, 0.04]);

  const submit = async (values) => {
    setLoading(true);
    const payload = {
      fcf_base: values.fcf_base,
      growth_rates: growthYears,
      terminal_growth: values.terminal_growth,
      wacc: values.wacc,
      net_debt: values.net_debt || 0,
      shares_out: values.shares_out,
    };
    try {
      const [r1, r2] = await Promise.all([
        axios.post('/api/valuation/dcf', payload),
        axios.post('/api/valuation/dcf/sensitivity', payload),
      ]);
      setResult(r1.data);
      setSens(r2.data);
    } catch (e) {
      setResult({ error: e.response?.data?.detail || e.message });
    } finally {
      setLoading(false);
    }
  };

  const updateYear = (idx, val) => {
    const next = [...growthYears];
    next[idx] = val;
    setGrowthYears(next);
  };

  return (
    <div>
      <Alert
        type="info"
        showIcon
        message="引导式 DCF（draft）"
        description="所有假设必须显式传入，避免硬编码。结果对假设极度敏感，请配合敏感性表使用，并由人工复核。"
        style={{ marginBottom: 16 }}
      />
      <Form
        form={form}
        layout="vertical"
        initialValues={{ fcf_base: 600, terminal_growth: 0.025, wacc: 0.09, net_debt: -1000, shares_out: 12.56 }}
        onFinish={submit}
      >
        <Row gutter={16}>
          <Col span={6}><Form.Item label="基期 FCF（亿元）" name="fcf_base" rules={[{ required: true }]}><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
          <Col span={6}><Form.Item label="WACC" name="wacc" rules={[{ required: true }]}><InputNumber step={0.005} style={{ width: '100%' }} /></Form.Item></Col>
          <Col span={6}><Form.Item label="永续增长率 g" name="terminal_growth" rules={[{ required: true }]}><InputNumber step={0.005} style={{ width: '100%' }} /></Form.Item></Col>
          <Col span={6}><Form.Item label="净债务（亿元，负=净现金）" name="net_debt"><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
          <Col span={6}><Form.Item label="总股本（亿股）" name="shares_out" rules={[{ required: true }]}><InputNumber step={0.01} style={{ width: '100%' }} /></Form.Item></Col>
        </Row>

        <Divider orientation="left" plain>显性预测期年增长率</Divider>
        <Row gutter={16}>
          {growthYears.map((g, i) => (
            <Col span={4} key={i}>
              <div style={{ fontSize: 12, marginBottom: 4 }}>第 {i + 1} 年</div>
              <InputNumber value={g} step={0.01} style={{ width: '100%' }} onChange={(v) => updateYear(i, v)} />
            </Col>
          ))}
          <Col span={4}>
            <div style={{ fontSize: 12, marginBottom: 4 }}>&nbsp;</div>
            <Button size="small" onClick={() => setGrowthYears([...growthYears, 0.03])}>+ 加一年</Button>{' '}
            {growthYears.length > 1 && <Button size="small" onClick={() => setGrowthYears(growthYears.slice(0, -1))}>− 减</Button>}
          </Col>
        </Row>

        <Form.Item style={{ marginTop: 16 }}>
          <Button type="primary" htmlType="submit" loading={loading}>计算 DCF</Button>
        </Form.Item>
      </Form>

      {loading && <Spin />}
      {result && result.error && <Alert type="error" message={result.error} />}
      {result && result.ok && (
        <>
          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col span={6}><Card><Statistic title="企业价值 EV (亿)" value={result.enterprise_value} precision={2} /></Card></Col>
            <Col span={6}><Card><Statistic title="股权价值 (亿)" value={result.equity_value} precision={2} /></Card></Col>
            <Col span={6}><Card><Statistic title="每股内在价值" value={result.per_share} precision={2} valueStyle={{ color: '#cf1322' }} /></Card></Col>
            <Col span={6}><Card><Statistic title="终值占比" value={result.terminal_pv / result.enterprise_value * 100} precision={1} suffix="%" /></Card></Col>
          </Row>

          {result.warnings?.length > 0 && (
            <Alert
              type="warning"
              showIcon
              message="假设合理性提醒"
              description={<ul style={{ marginBottom: 0 }}>{result.warnings.map((w, i) => <li key={i}>{w}</li>)}</ul>}
              style={{ marginBottom: 16 }}
            />
          )}

          <Card type="inner" title="显性预测期" size="small" style={{ marginBottom: 16 }}>
            <Table
              size="small"
              pagination={false}
              rowKey="year"
              dataSource={result.explicit_fcf.map((fcf, i) => ({ year: i + 1, fcf, pv: result.explicit_pv[i] }))}
              columns={[
                { title: '年', dataIndex: 'year' },
                { title: 'FCF（亿）', dataIndex: 'fcf', render: (v) => v.toFixed(2) },
                { title: '现值（亿）', dataIndex: 'pv', render: (v) => v.toFixed(2) },
              ]}
            />
          </Card>

          {sens && (
            <Card type="inner" title="敏感性表：每股内在价值（行=WACC，列=g）" size="small">
              <Table
                size="small"
                pagination={false}
                rowKey={(r) => r.wacc}
                dataSource={sens.wacc_axis.map((w, i) => {
                  const row = { wacc: w };
                  sens.g_axis.forEach((g, j) => { row[`g_${j}`] = sens.per_share_matrix[i][j]; });
                  return row;
                })}
                columns={[
                  { title: 'WACC＼g', dataIndex: 'wacc', render: (v) => <Tag>{(v * 100).toFixed(2)}%</Tag> },
                  ...sens.g_axis.map((g, j) => ({
                    title: `${(g * 100).toFixed(2)}%`,
                    dataIndex: `g_${j}`,
                    render: (v) => v === null ? '—' : v.toFixed(2),
                  })),
                ]}
              />
            </Card>
          )}
        </>
      )}
    </div>
  );
}

function CompsPanel() {
  const [code, setCode] = useState('600519');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const load = async (c) => {
    setLoading(true); setError(null);
    try {
      const res = await axios.get(`/api/valuation/comps/${c}`);
      setData(res.data);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
      setData(null);
    } finally { setLoading(false); }
  };

  const fmt = (v, suf = '') => v === null || v === undefined ? '—' : `${Number(v).toFixed(2)}${suf}`;

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Input.Search defaultValue={code} onSearch={(v) => { setCode(v); load(v); }} placeholder="股票代码" style={{ width: 220 }} />
      </Space>
      {loading && <Spin />}
      {error && <Alert type="error" message={error} />}
      {data && data.available && (
        <>
          <Alert type="info" showIcon message={`所属行业：${data.industry}`} description={data.disclaimer} style={{ marginBottom: 16 }} />
          {data.target && (
            <Descriptions bordered size="small" column={4} style={{ marginBottom: 16 }} title="目标公司">
              <Descriptions.Item label="代码">{data.target.code}</Descriptions.Item>
              <Descriptions.Item label="名称">{data.target.name}</Descriptions.Item>
              <Descriptions.Item label="价格">{fmt(data.target.price)}</Descriptions.Item>
              <Descriptions.Item label="PE(TTM)">{fmt(data.target.pe_ttm)}</Descriptions.Item>
              <Descriptions.Item label="PB">{fmt(data.target.pb)}</Descriptions.Item>
              <Descriptions.Item label="PS">{fmt(data.target.ps)}</Descriptions.Item>
              <Descriptions.Item label="ROE">{fmt(data.target.roe, '%')}</Descriptions.Item>
              <Descriptions.Item label="今日涨跌">{fmt(data.target.change_percent, '%')}</Descriptions.Item>
            </Descriptions>
          )}
          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col span={6}><Card><Statistic title="行业中位 PE" value={data.summary.median_pe} precision={2} /></Card></Col>
            <Col span={6}><Card><Statistic title="行业中位 PB" value={data.summary.median_pb} precision={2} /></Card></Col>
            <Col span={6}><Card><Statistic title="行业中位 PS" value={data.summary.median_ps} precision={2} /></Card></Col>
            <Col span={6}><Card><Statistic title="行业中位 ROE" value={data.summary.median_roe} precision={2} suffix="%" /></Card></Col>
          </Row>
          {data.commentary?.length > 0 && (
            <Alert type="success" showIcon message="相对估值要点（draft）"
              description={<ul style={{ marginBottom: 0 }}>{data.commentary.map((c, i) => <li key={i}>{c}</li>)}</ul>}
              style={{ marginBottom: 16 }}
            />
          )}
          <Card type="inner" title={`同行业可比公司（共 ${data.summary.count} 家，显示前 30）`} size="small">
            <Table
              size="small"
              pagination={{ pageSize: 15 }}
              rowKey="code"
              dataSource={data.peers}
              columns={[
                { title: '代码', dataIndex: 'code' },
                { title: '名称', dataIndex: 'name' },
                { title: '价格', dataIndex: 'price', render: (v) => fmt(v) },
                { title: 'PE(TTM)', dataIndex: 'pe_ttm', sorter: (a, b) => (a.pe_ttm || 0) - (b.pe_ttm || 0), render: (v) => fmt(v) },
                { title: 'PB', dataIndex: 'pb', sorter: (a, b) => (a.pb || 0) - (b.pb || 0), render: (v) => fmt(v) },
                { title: 'PS', dataIndex: 'ps', render: (v) => fmt(v) },
                { title: 'ROE(%)', dataIndex: 'roe', sorter: (a, b) => (a.roe || 0) - (b.roe || 0), render: (v) => fmt(v) },
              ]}
            />
          </Card>
        </>
      )}
    </div>
  );
}

export default function ValuationPage() {
  return (
    <Card title="估值实验室">
      <Tabs
        items={[
          { key: 'dcf', label: 'DCF 估值', children: <DCFPanel /> },
          { key: 'comps', label: '可比公司', children: <CompsPanel /> },
        ]}
      />
    </Card>
  );
}
