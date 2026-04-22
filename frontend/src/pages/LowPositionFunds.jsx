import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Table, Button, Spin, Tag, Statistic, Row, Col, Empty, Tooltip } from 'antd';
import { ReloadOutlined, FallOutlined, RiseOutlined, InfoCircleOutlined } from '@ant-design/icons';
import axios from 'axios';
import { useTheme } from '../context/ThemeContext';

function LowPositionFunds() {
  const { isDark } = useTheme();
  const navigate = useNavigate();
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [updatedAt, setUpdatedAt] = useState(null);
  const [scanned, setScanned] = useState(0);

  const fetchData = async (refresh = false) => {
    setLoading(true);
    try {
      const response = await axios.get('/api/funds/low-position', {
        params: { limit: 50, refresh },
      });
      const result = response.data;
      if (result.scanning) {
        setScanning(true);
        setData([]);
      } else {
        setScanning(false);
        setData(result.data || []);
        setUpdatedAt(result.updated_at);
        setScanned(result.scanned || 0);
      }
    } catch (error) {
      console.error('获取低位基金数据失败:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData(false);
  }, []);

  // 扫描中时轮询结果
  useEffect(() => {
    if (!scanning) return;
    const timer = setInterval(() => {
      fetchData(false);
    }, 10000);
    return () => clearInterval(timer);
  }, [scanning]);

  const handleRefresh = () => {
    fetchData(true);
  };

  const columns = [
    {
      title: '排名',
      dataIndex: 'rank',
      width: 60,
      render: (_, __, index) => (
        <span style={{ fontWeight: 700, fontSize: 14, color: index < 3 ? '#ff4d4f' : 'var(--text-primary)' }}>
          {index + 1}
        </span>
      ),
    },
    {
      title: '基金',
      dataIndex: 'name',
      render: (_, record) => (
        <div
          style={{ cursor: 'pointer' }}
          onClick={() => navigate(`/fund/${record.code}`)}
        >
          <div
            style={{
              fontWeight: 600,
              color: 'var(--accent)',
              fontSize: 14,
              textDecoration: 'none',
            }}
          >
            {record.name}
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>
            {record.code}
            {record.fund_type && (
              <Tag size="small" style={{ marginLeft: 6, fontSize: 11 }}>
                {record.fund_type}
              </Tag>
            )}
          </div>
        </div>
      ),
    },
    {
      title: (
        <Tooltip title="当前净值较历史最高净值的回撤幅度，越大表示跌得越深">
          <span>历史回撤 <InfoCircleOutlined style={{ fontSize: 12, opacity: 0.6 }} /></span>
        </Tooltip>
      ),
      dataIndex: 'drawdown',
      width: 120,
      sorter: (a, b) => a.drawdown - b.drawdown,
      defaultSortOrder: 'descend',
      render: (val) => (
        <span style={{ color: '#ff4d4f', fontWeight: 700, fontSize: 15 }}>
          <FallOutlined style={{ marginRight: 4 }} />
          {val}%
        </span>
      ),
    },
    {
      title: '历史百分位',
      dataIndex: 'percentile',
      width: 120,
      render: (val) => {
        let color = '#ff4d4f';
        if (val > 30) color = '#faad14';
        if (val > 70) color = '#52c41a';
        return (
          <span style={{ color, fontWeight: 600 }}>
            {val}%
          </span>
        );
      },
    },
    {
      title: '当前净值',
      dataIndex: 'current',
      width: 100,
      render: (val) => <span style={{ fontVariantNumeric: 'tabular-nums' }}>{val}</span>,
    },
    {
      title: '历史最高',
      dataIndex: 'peak',
      width: 100,
      render: (val, record) => (
        <Tooltip title={`最高点日期: ${record.peak_date}`}>
          <span style={{ fontVariantNumeric: 'tabular-nums' }}>{val}</span>
        </Tooltip>
      ),
    },
    {
      title: '历史最低',
      dataIndex: 'trough',
      width: 100,
      render: (val) => <span style={{ fontVariantNumeric: 'tabular-nums' }}>{val}</span>,
    },
    {
      title: '历史长度',
      dataIndex: 'history_days',
      width: 100,
      render: (val) => `${Math.round(val / 365)}年`,
    },
  ];

  return (
    <div>
      <Card
        style={{ marginBottom: 20, borderRadius: 12, background: 'var(--bg-card)' }}
        styles={{ body: { padding: '20px 28px' } }}
      >
        <Row justify="space-between" align="middle">
          <Col>
            <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--text-primary)' }}>
              历史低位基金扫描
            </div>
            <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 4 }}>
              扫描全市场基金（排除货币型），找出当前处于历史低位、回撤幅度最大的前50只基金
            </div>
          </Col>
          <Col>
            <Button
              type="primary"
              icon={<ReloadOutlined />}
              loading={loading}
              onClick={handleRefresh}
              size="large"
            >
              刷新数据
            </Button>
          </Col>
        </Row>

        <Row gutter={24} style={{ marginTop: 20 }}>
          <Col span={8}>
            <Statistic
              title="扫描基金数量"
              value={scanned}
              suffix="只"
              valueStyle={{ color: 'var(--text-primary)', fontWeight: 700 }}
            />
          </Col>
          <Col span={8}>
            <Statistic
              title="筛选结果"
              value={data.length}
              suffix="只"
              valueStyle={{ color: '#ff4d4f', fontWeight: 700 }}
            />
          </Col>
          <Col span={8}>
            <Statistic
              title="更新时间"
              value={updatedAt ? new Date(updatedAt).toLocaleString('zh-CN') : '-'}
              valueStyle={{ color: 'var(--text-secondary)', fontSize: 14, fontWeight: 500 }}
            />
          </Col>
        </Row>
      </Card>

      {scanning ? (
        <Card style={{ borderRadius: 12, background: 'var(--bg-card)', textAlign: 'center', padding: 80 }}>
          <Spin size="large" />
          <div style={{ marginTop: 20, color: 'var(--text-secondary)', fontSize: 15 }}>
            正在扫描全市场基金数据，请稍候...
          </div>
          <div style={{ marginTop: 8, color: 'var(--text-tertiary)', fontSize: 13 }}>
            全市场扫描约需 3-5 分钟，可关闭页面稍后回来查看结果
          </div>
        </Card>
      ) : data.length > 0 ? (
        <Card style={{ borderRadius: 12, background: 'var(--bg-card)' }} styles={{ body: { padding: '16px 20px' } }}>
          <Table
            columns={columns}
            dataSource={data}
            rowKey="code"
            pagination={false}
            size="middle"
            scroll={{ x: 900 }}
          />
        </Card>
      ) : (
        <Card style={{ borderRadius: 12, background: 'var(--bg-card)' }}>
          <Empty
            description="暂无数据，点击上方刷新按钮开始扫描"
            style={{ padding: 60 }}
          />
        </Card>
      )}
    </div>
  );
}

export default LowPositionFunds;
