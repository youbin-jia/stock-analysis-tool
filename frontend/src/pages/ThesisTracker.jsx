import { useEffect, useState } from 'react';
import {
  Card, Table, Button, Modal, Form, Input, InputNumber, Select, message,
  Tag, Space, Popconfirm, Alert, Tabs, Empty, Tooltip
} from 'antd';
import axios from 'axios';

export default function ThesisTracker() {
  const [data, setData] = useState([]);
  const [checks, setChecks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form] = Form.useForm();

  const load = async () => {
    setLoading(true);
    try {
      const [r1, r2] = await Promise.all([
        axios.get('/api/thesis'),
        axios.get('/api/thesis/_/check-all?status=active'),
      ]);
      setData(r1.data.data || []);
      setChecks(r2.data.data || []);
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    setModalOpen(true);
  };

  const openEdit = (row) => {
    setEditing(row);
    form.setFieldsValue({
      ...row,
      triggers: (row.triggers || []).join('\n'),
    });
    setModalOpen(true);
  };

  const submit = async () => {
    const v = await form.validateFields();
    const payload = {
      ...v,
      triggers: (v.triggers || '').split('\n').map(s => s.trim()).filter(Boolean),
    };
    try {
      if (editing) {
        await axios.patch(`/api/thesis/${editing.id}`, payload);
        message.success('已更新');
      } else {
        await axios.post('/api/thesis', payload);
        message.success('已创建');
      }
      setModalOpen(false);
      load();
    } catch (e) {
      message.error(e.response?.data?.detail || e.message);
    }
  };

  const remove = async (id) => {
    await axios.delete(`/api/thesis/${id}`);
    message.success('已删除');
    load();
  };

  const statusTag = (s) => {
    const map = { active: ['blue', '持有'], closed: ['green', '已平仓'], invalidated: ['red', '逻辑被证伪'] };
    const [c, l] = map[s] || ['default', s];
    return <Tag color={c}>{l}</Tag>;
  };

  const checkMap = Object.fromEntries(checks.map(c => [c.id, c]));

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '代码', dataIndex: 'code', width: 100 },
    { title: '名称', dataIndex: 'name', width: 120 },
    { title: '标题', dataIndex: 'title', render: (v, row) => (
      <Tooltip title={row.thesis}><span>{v}</span></Tooltip>
    )},
    { title: '买入', dataIndex: 'buy_price', width: 80 },
    { title: '目标', dataIndex: 'target_price', width: 80 },
    { title: '止损', dataIndex: 'stop_loss', width: 80 },
    { title: '现价', width: 80, render: (_, row) => checkMap[row.id]?.current_price ?? '—' },
    { title: '触发信号', render: (_, row) => {
      const c = checkMap[row.id];
      if (!c) return '—';
      return (
        <Space direction="vertical" size={0}>
          {c.signals?.map((s, i) => <Tag key={i} color={
            s.includes('击穿') ? 'red' : s.includes('触达') ? 'green' : 'default'
          }>{s}</Tag>)}
        </Space>
      );
    }},
    { title: '状态', dataIndex: 'status', width: 100, render: statusTag },
    { title: '操作', width: 160, render: (_, row) => (
      <Space>
        <Button size="small" onClick={() => openEdit(row)}>编辑</Button>
        <Popconfirm title="确认删除？" onConfirm={() => remove(row.id)}>
          <Button size="small" danger>删除</Button>
        </Popconfirm>
      </Space>
    )},
  ];

  return (
    <Card title="投资观点跟踪（IC Memo 草稿）" extra={
      <Space>
        <Button onClick={load}>刷新</Button>
        <Button type="primary" onClick={openCreate}>+ 新建观点</Button>
      </Space>
    }>
      <Alert
        type="info"
        showIcon
        message="把'我为什么买'写下来，并设定可证伪的触发条件。系统会按实时价检查目标/止损是否触达。"
        style={{ marginBottom: 16 }}
      />

      <Table
        rowKey="id"
        loading={loading}
        dataSource={data}
        columns={columns}
        expandable={{
          expandedRowRender: (row) => (
            <div style={{ padding: 8 }}>
              <div><strong>投资逻辑：</strong></div>
              <div style={{ whiteSpace: 'pre-wrap', marginBottom: 8 }}>{row.thesis}</div>
              {row.horizon && <div><strong>持有周期：</strong>{row.horizon}</div>}
              {row.triggers?.length > 0 && (
                <div>
                  <strong>关键触发条件：</strong>
                  <ul>{row.triggers.map((t, i) => <li key={i}>{t}</li>)}</ul>
                </div>
              )}
            </div>
          )
        }}
      />

      <Modal
        title={editing ? `编辑 #${editing.id}` : '新建投资观点'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={submit}
        width={680}
        destroyOnClose
      >
        <Form form={form} layout="vertical" initialValues={{ status: 'active' }}>
          <Form.Item label="股票代码" name="code" rules={[{ required: true }]}><Input placeholder="如 600519" /></Form.Item>
          <Form.Item label="名称" name="name"><Input placeholder="可选" /></Form.Item>
          <Form.Item label="标题（一句话）" name="title" rules={[{ required: true }]}><Input placeholder="如：白酒龙头估值修复" /></Form.Item>
          <Form.Item label="投资逻辑" name="thesis" rules={[{ required: true }]}>
            <Input.TextArea rows={5} placeholder="写清楚：1) 为什么现在买；2) 关键假设是什么；3) 时间窗口" />
          </Form.Item>
          <Space style={{ display: 'flex' }} size="large">
            <Form.Item label="买入价" name="buy_price"><InputNumber step={0.01} /></Form.Item>
            <Form.Item label="目标价" name="target_price"><InputNumber step={0.01} /></Form.Item>
            <Form.Item label="止损价" name="stop_loss"><InputNumber step={0.01} /></Form.Item>
            <Form.Item label="持有周期" name="horizon"><Input placeholder="如 6-12 个月" /></Form.Item>
          </Space>
          <Form.Item label="关键触发条件（一行一条）" name="triggers">
            <Input.TextArea rows={3} placeholder="Q3 净利同比转正&#10;PE-TTM 回升至 30 以上" />
          </Form.Item>
          <Form.Item label="状态" name="status">
            <Select options={[
              { value: 'active', label: '持有' },
              { value: 'closed', label: '已平仓' },
              { value: 'invalidated', label: '逻辑被证伪' },
            ]} />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
}
