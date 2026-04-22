import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Table, Select, Segmented, Tag, Statistic, Row, Col, Empty, Spin, Tooltip } from 'antd';
import { FireOutlined, RiseOutlined, FallOutlined, InfoCircleOutlined } from '@ant-design/icons';
import axios from 'axios';
import { useTheme } from '../context/ThemeContext';

const SECTOR_SORT_OPTIONS = [
  { label: '日涨幅', value: 'daily' },
  { label: '5日涨幅', value: '5day' },
  { label: '月涨幅', value: 'month' },
  { label: '3月涨幅', value: '3month' },
  { label: '年涨幅', value: 'year' },
];

const FUND_TYPE_OPTIONS = [
  { label: '全部', value: '全部' },
  { label: '股票型', value: '股票型' },
  { label: '混合型', value: '混合型' },
  { label: '债券型', value: '债券型' },
  { label: '指数型', value: '指数型' },
  { label: 'QDII', value: 'QDII' },
  { label: 'FOF', value: 'FOF' },
];

const FUND_SORT_OPTIONS = [
  { label: '日涨幅', value: 'daily' },
  { label: '近1周', value: 'week' },
  { label: '近1月', value: 'month' },
  { label: '近3月', value: '3month' },
  { label: '近6月', value: '6month' },
  { label: '近1年', value: 'year' },
  { label: '成立来', value: 'total' },
];

function HotSectors() {
  const { isDark } = useTheme();
  const navigate = useNavigate();

  // 板块状态
  const [sectorType, setSectorType] = useState('industry');
  const [sectorSortBy, setSectorSortBy] = useState('daily');
  const [sectors, setSectors] = useState([]);
  const [sectorLoading, setSectorLoading] = useState(false);

  // 基金状态
  const [fundType, setFundType] = useState('全部');
  const [fundSortBy, setFundSortBy] = useState('daily');
  const [funds, setFunds] = useState([]);
  const [fundLoading, setFundLoading] = useState(false);

  const fetchSectors = async () => {
    setSectorLoading(true);
    try {
      const response = await axios.get(`/api/sectors/${sectorType}`, {
        params: { sort_by: sectorSortBy },
      });
      setSectors(response.data || []);
    } catch (error) {
      console.error('获取板块数据失败:', error);
    } finally {
      setSectorLoading(false);
    }
  };

  const fetchFunds = async () => {
    setFundLoading(true);
    try {
      const response = await axios.get('/api/sectors/funds', {
        params: { fund_type: fundType, sort_by: fundSortBy, limit: 50 },
      });
      setFunds(response.data || []);
    } catch (error) {
      console.error('获取基金排行失败:', error);
    } finally {
      setFundLoading(false);
    }
  };

  useEffect(() => {
    fetchSectors();
  }, [sectorType, sectorSortBy]);

  useEffect(() => {
    fetchFunds();
  }, [fundType, fundSortBy]);

  const renderChange = (val, suffix = '%') => {
    if (val == null) return <span style={{ color: 'var(--text-tertiary)' }}>-</span>;
    const color = val > 0 ? '#ff4d4f' : val < 0 ? '#52c41a' : 'var(--text-primary)';
    const icon = val > 0 ? <RiseOutlined style={{ marginRight: 2 }} /> : val < 0 ? <FallOutlined style={{ marginRight: 2 }} /> : null;
    return (
      <span style={{ color, fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>
        {icon}{val > 0 ? '+' : ''}{val}{suffix}
      </span>
    );
  };

  const sectorColumns = [
    {
      title: '排名',
      width: 55,
      render: (_, __, index) => (
        <span style={{ fontWeight: 700, fontSize: 14, color: index < 3 ? '#ff4d4f' : 'var(--text-primary)' }}>
          {index + 1}
        </span>
      ),
    },
    {
      title: '板块名称',
      dataIndex: 'name',
      width: 120,
      render: (val) => (
        <span style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: 14 }}>{val}</span>
      ),
    },
    {
      title: '均价',
      dataIndex: 'price',
      width: 80,
      render: (val) => <span style={{ fontVariantNumeric: 'tabular-nums' }}>{val}</span>,
    },
    {
      title: '日涨幅',
      dataIndex: 'change_percent',
      width: 100,
      sorter: (a, b) => (a.change_percent || 0) - (b.change_percent || 0),
      defaultSortOrder: sectorSortBy === 'daily' ? 'descend' : null,
      render: (val) => renderChange(val),
    },
    {
      title: '涨跌额',
      dataIndex: 'change_amount',
      width: 80,
      render: (val) => renderChange(val, ''),
    },
    {
      title: (
        <Tooltip title="板块成交额">
          <span>成交额 <InfoCircleOutlined style={{ fontSize: 11, opacity: 0.5 }} /></span>
        </Tooltip>
      ),
      dataIndex: 'total_market_cap',
      width: 110,
      render: (val) => {
        if (!val) return '-';
        if (val >= 1e12) return `${(val / 1e12).toFixed(1)}万亿`;
        if (val >= 1e8) return `${(val / 1e8).toFixed(1)}亿`;
        if (val >= 1e4) return `${(val / 1e4).toFixed(0)}万`;
        return val.toFixed(0);
      },
    },
    {
      title: '领涨股',
      dataIndex: 'leading_stock',
      width: 120,
      render: (val, record) => (
        <div>
          <span style={{ color: 'var(--accent)', fontWeight: 500 }}>{val}</span>
          {record.leading_stock_change != null && (
            <span style={{ marginLeft: 6, fontSize: 12 }}>
              {renderChange(record.leading_stock_change)}
            </span>
          )}
        </div>
      ),
    },
    ...(sectorSortBy !== 'daily'
      ? [
          {
            title: '历史涨幅',
            dataIndex: 'historical_change',
            width: 100,
            sorter: (a, b) => (a.historical_change || 0) - (b.historical_change || 0),
            render: (val) => renderChange(val),
          },
        ]
      : []),
  ];

  const fundColumns = [
    {
      title: '排名',
      width: 55,
      render: (_, __, index) => (
        <span style={{ fontWeight: 700, fontSize: 14, color: index < 3 ? '#ff4d4f' : 'var(--text-primary)' }}>
          {index + 1}
        </span>
      ),
    },
    {
      title: '基金',
      dataIndex: 'name',
      width: 180,
      render: (_, record) => (
        <div style={{ cursor: 'pointer' }} onClick={() => navigate(`/fund/${record.code}`)}>
          <div style={{ fontWeight: 600, color: 'var(--accent)', fontSize: 14 }}>{record.name}</div>
          <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>
            {record.code}
            {record.fund_type && (
              <Tag size="small" style={{ marginLeft: 6, fontSize: 11 }}>{record.fund_type}</Tag>
            )}
          </div>
        </div>
      ),
    },
    {
      title: '最新净值',
      dataIndex: 'nav',
      width: 90,
      render: (val) => <span style={{ fontVariantNumeric: 'tabular-nums' }}>{val ?? '-'}</span>,
    },
    {
      title: '日涨幅',
      dataIndex: 'daily_change',
      width: 90,
      sorter: (a, b) => (a.daily_change || 0) - (b.daily_change || 0),
      defaultSortOrder: fundSortBy === 'daily' ? 'descend' : null,
      render: (val) => renderChange(val),
    },
    {
      title: '近1周',
      dataIndex: 'week_change',
      width: 85,
      render: (val) => renderChange(val),
    },
    {
      title: '近1月',
      dataIndex: 'month_change',
      width: 85,
      render: (val) => renderChange(val),
    },
    {
      title: '近3月',
      dataIndex: 'three_month_change',
      width: 85,
      render: (val) => renderChange(val),
    },
    {
      title: '近1年',
      dataIndex: 'year_change',
      width: 85,
      render: (val) => renderChange(val),
    },
    {
      title: '成立来',
      dataIndex: 'total_change',
      width: 90,
      render: (val) => renderChange(val),
    },
  ];

  return (
    <div>
      {/* 板块卡片 */}
      <Card
        style={{ marginBottom: 20, borderRadius: 12, background: 'var(--bg-card)' }}
        styles={{ body: { padding: '20px 28px' } }}
      >
        <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
          <Col>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <FireOutlined style={{ fontSize: 22, color: '#ff4d4f' }} />
              <span style={{ fontSize: 20, fontWeight: 700, color: 'var(--text-primary)' }}>
                热门板块
              </span>
            </div>
            <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 4 }}>
              实时行业板块涨跌排行，数据来源新浪财经
            </div>
          </Col>
          <Col>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <Segmented
                value={sectorType}
                onChange={setSectorType}
                options={[
                  { label: '行业板块', value: 'industry' },
                  { label: '概念板块', value: 'concept' },
                ]}
              />
              <Select
                value={sectorSortBy}
                onChange={setSectorSortBy}
                options={SECTOR_SORT_OPTIONS}
                style={{ width: 110 }}
                size="middle"
              />
            </div>
          </Col>
        </Row>

        <Row gutter={24} style={{ marginBottom: 16 }}>
          <Col span={8}>
            <Statistic
              title="板块数量"
              value={sectors.length}
              suffix="个"
              valueStyle={{ color: 'var(--text-primary)', fontWeight: 700 }}
            />
          </Col>
          <Col span={8}>
            <Statistic
              title="上涨板块"
              value={sectors.filter((s) => s.change_percent > 0).length}
              suffix="个"
              valueStyle={{ color: '#ff4d4f', fontWeight: 700 }}
            />
          </Col>
          <Col span={8}>
            <Statistic
              title="下跌板块"
              value={sectors.filter((s) => s.change_percent < 0).length}
              suffix="个"
              valueStyle={{ color: '#52c41a', fontWeight: 700 }}
            />
          </Col>
        </Row>

        {sectorLoading ? (
          <div style={{ textAlign: 'center', padding: 60 }}>
            <Spin size="large" />
            <div style={{ marginTop: 12, color: 'var(--text-secondary)' }}>加载板块数据...</div>
          </div>
        ) : sectors.length > 0 ? (
          <Table
            columns={sectorColumns}
            dataSource={sectors}
            rowKey="code"
            pagination={false}
            size="middle"
            scroll={{ x: 800 }}
          />
        ) : (
          <Empty description="暂无板块数据" style={{ padding: 40 }} />
        )}
      </Card>

      {/* 基金排行卡片 */}
      <Card
        style={{ borderRadius: 12, background: 'var(--bg-card)' }}
        styles={{ body: { padding: '20px 28px' } }}
      >
        <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
          <Col>
            <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)' }}>
              基金涨幅排行
            </div>
            <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 4 }}>
              按基金类型筛选，按涨幅排序，数据来源东方财富
            </div>
          </Col>
          <Col>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <Select
                value={fundType}
                onChange={setFundType}
                options={FUND_TYPE_OPTIONS}
                style={{ width: 110 }}
              />
              <Select
                value={fundSortBy}
                onChange={setFundSortBy}
                options={FUND_SORT_OPTIONS}
                style={{ width: 110 }}
              />
            </div>
          </Col>
        </Row>

        {fundLoading ? (
          <div style={{ textAlign: 'center', padding: 60 }}>
            <Spin size="large" />
            <div style={{ marginTop: 12, color: 'var(--text-secondary)' }}>加载基金排行...</div>
          </div>
        ) : funds.length > 0 ? (
          <Table
            columns={fundColumns}
            dataSource={funds}
            rowKey="code"
            pagination={{ pageSize: 20, showSizeChanger: false }}
            size="middle"
            scroll={{ x: 1000 }}
          />
        ) : (
          <Empty description="暂无基金数据" style={{ padding: 40 }} />
        )}
      </Card>
    </div>
  );
}

export default HotSectors;
