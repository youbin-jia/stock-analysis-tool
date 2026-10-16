import { useEffect, useState } from 'react';
import {
  Alert,
  Card,
  Col,
  Collapse,
  Descriptions,
  Empty,
  List,
  Progress,
  Row,
  Skeleton,
  Table,
  Tag,
  Tooltip,
  Typography,
} from 'antd';
import { InfoCircleOutlined } from '@ant-design/icons';
import axios from 'axios';
import { useTheme } from '../context/ThemeContext';

const { Text } = Typography;

const FAMILY_COLORS = {
  trend: 'blue',
  momentum: 'purple',
  volatility: 'cyan',
  breakout: 'geekblue',
};

const QUALITY_META = {
  good: { color: 'green', text: '充足' },
  weak: { color: 'orange', text: '偏少' },
  insufficient: { color: 'red', text: '不足' },
};

function StrategySignalPanel({ stockCode }) {
  const { isDark } = useTheme();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  // 信号色刻意不用涨跌色：A股红涨绿跌，红色的"卖出"标记无法阅读
  const buyColor = isDark ? '#4aa3ff' : '#1677ff';
  const sellColor = isDark ? '#faad14' : '#d48806';
  const neutralColor = isDark ? '#a6a6a6' : '#8c8c8c';

  const verdictColor = {
    买入: buyColor,
    卖出: sellColor,
    观望: neutralColor,
  };

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setData(null);

    axios
      .get(`/api/strategy/signals/${stockCode}`, {
        params: { period: '1y', frequency: 'd' },
      })
      .then((res) => {
        if (!cancelled) setData(res.data);
      })
      .catch(() => {
        if (!cancelled) setData(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [stockCode]);

  if (loading) {
    return (
      <Card style={{ marginBottom: 20, borderRadius: 12, background: 'var(--bg-card)' }}>
        <Skeleton active paragraph={{ rows: 4 }} />
      </Card>
    );
  }

  // 面板是补充信息，拿不到数据时静默隐藏，绝不阻塞主页面
  if (!data || !data.composite) return null;

  const { composite, risk_levels: risk, strategies = [], warnings = [] } = data;
  const color = verdictColor[composite.verdict] || neutralColor;

  const columns = [
    {
      title: '策略',
      dataIndex: 'name',
      width: 150,
      render: (name, row) => (
        <Tooltip title={row.description}>
          <span>{name}</span>
        </Tooltip>
      ),
    },
    {
      title: '类别',
      dataIndex: 'family_name',
      width: 100,
      render: (t, row) => <Tag color={FAMILY_COLORS[row.family]}>{t}</Tag>,
    },
    {
      title: '当前状态',
      dataIndex: 'detail',
      width: 260,
      render: (detail, row) => {
        const map = { bullish: buyColor, bearish: sellColor, neutral: neutralColor };
        return (
          <span style={{ color: map[row.status] }}>{detail}</span>
        );
      },
    },
    {
      title: '最近信号',
      dataIndex: 'last_signal',
      width: 150,
      render: (s) =>
        s ? (
          <span style={{ color: s.signal === 'buy' ? buyColor : sellColor }}>
            {s.signal === 'buy' ? '买入' : '卖出'} · {s.bars_ago} 根前
          </span>
        ) : (
          <Text type="secondary">—</Text>
        ),
    },
    {
      title: '回测胜率(买)',
      dataIndex: 'backtest',
      width: 150,
      render: (b) => {
        if (!b || !b.buy || !b.buy.signal_count) return <Text type="secondary">—</Text>;
        const pct = Math.round(b.buy.win_rate * 100);
        return (
          <span>
            <Progress
              percent={pct}
              size="small"
              status="normal"
              strokeColor={pct >= 55 ? buyColor : pct >= 45 ? neutralColor : sellColor}
              style={{ width: 90, marginRight: 8 }}
            />
            <Text type="secondary">n={b.buy.signal_count}</Text>
          </span>
        );
      },
    },
    {
      title: '平均收益',
      dataIndex: 'backtest',
      key: 'avg',
      width: 100,
      render: (b) =>
        b && b.buy && b.buy.signal_count ? (
          <span style={{ color: b.buy.avg_return >= 0 ? buyColor : sellColor }}>
            {b.buy.avg_return.toFixed(2)}%
          </span>
        ) : (
          <Text type="secondary">—</Text>
        ),
    },
    {
      title: '样本',
      dataIndex: 'backtest',
      key: 'quality',
      width: 80,
      render: (b) => {
        if (!b || !b.buy || !b.buy.signal_count) return <Text type="secondary">—</Text>;
        const meta = QUALITY_META[b.buy.sample_quality] || QUALITY_META.insufficient;
        return <Tag color={meta.color}>{meta.text}</Tag>;
      },
    },
  ];

  return (
    <Card
      style={{ marginBottom: 20, borderRadius: 12, background: 'var(--bg-card)' }}
      styles={{ body: { padding: '20px 24px' } }}
    >
      <Row gutter={[24, 20]}>
        {/* 综合结论 */}
        <Col xs={24} md={7}>
          <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginBottom: 8 }}>
            技术策略综合信号
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <Progress
              type="dashboard"
              size={110}
              percent={composite.confidence}
              strokeColor={color}
              format={(p) => (
                <span style={{ color, fontSize: 20, fontWeight: 600 }}>{p}</span>
              )}
            />
            <div>
              <Tag
                color={color}
                style={{ fontSize: 16, padding: '4px 14px', marginBottom: 8 }}
              >
                {composite.verdict}
              </Tag>
              <div style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>
                置信度（回测胜率加权）
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginTop: 4 }}>
                多方 {composite.buy_score} / 空方 {composite.sell_score}
              </div>
            </div>
          </div>
          <div style={{ marginTop: 12, fontSize: 12, color: 'var(--text-secondary)' }}>
            {composite.regime?.detail}
          </div>
        </Col>

        {/* 触发的策略 */}
        <Col xs={24} md={9}>
          <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginBottom: 8 }}>
            近期触发（{composite.reasons?.length || 0}）
          </div>
          {composite.reasons?.length ? (
            <List
              size="small"
              dataSource={composite.reasons}
              renderItem={(r) => (
                <List.Item style={{ padding: '6px 0', borderBlockEnd: 'none' }}>
                  <div style={{ width: '100%' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <Tag color={FAMILY_COLORS[r.family]} style={{ margin: 0 }}>
                        {r.family_name}
                      </Tag>
                      <span
                        style={{
                          color: r.signal === 'buy' ? buyColor : sellColor,
                          fontWeight: 600,
                        }}
                      >
                        {r.signal === 'buy' ? '买' : '卖'}
                      </span>
                      <span style={{ color: 'var(--text-primary)' }}>{r.strategy_name}</span>
                      <Tooltip title={r.detail}>
                        <InfoCircleOutlined style={{ color: 'var(--text-tertiary)' }} />
                      </Tooltip>
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginTop: 2 }}>
                      {r.date} · {r.bars_ago} 根前 · 历史胜率{' '}
                      {(r.backtest_win_rate * 100).toFixed(0)}%（n={r.backtest_count}）
                    </div>
                  </div>
                </List.Item>
              )}
            />
          ) : (
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description="近期无策略信号触发"
              style={{ margin: '20px 0' }}
            />
          )}
        </Col>

        {/* 风控参考 */}
        <Col xs={24} md={8}>
          <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginBottom: 8 }}>
            风控参考位
          </div>
          {risk ? (
            <Descriptions
              column={1}
              size="small"
              items={[
                {
                  key: 'stop',
                  label: '止损位',
                  children: (
                    <span style={{ color: sellColor }}>
                      {risk.stop_loss}（{risk.stop_loss_pct}%）
                    </span>
                  ),
                },
                {
                  key: 'target',
                  label: '止盈位',
                  children: (
                    <span style={{ color: buyColor }}>
                      {risk.take_profit}（+{risk.take_profit_pct}%）
                    </span>
                  ),
                },
                {
                  key: 'atr',
                  label: 'ATR(14)',
                  children: `${risk.atr}（占价格 ${risk.atr_pct}%）`,
                },
                { key: 'rr', label: '盈亏比', children: `1 : ${risk.risk_reward}` },
                { key: 'basis', label: '计算依据', children: risk.basis },
              ]}
            />
          ) : (
            <Text type="secondary">数据不足，无法计算</Text>
          )}
        </Col>
      </Row>

      {warnings.length > 0 && (
        <Alert
          type="info"
          showIcon
          style={{ marginTop: 12 }}
          message={warnings.join('；')}
        />
      )}

      <Collapse
        ghost
        style={{ marginTop: 8 }}
        items={[
          {
            key: 'detail',
            label: `各策略明细与回测统计（${strategies.length} 个策略）`,
            children: (
              <>
                <Table
                  rowKey="key"
                  size="small"
                  pagination={false}
                  columns={columns}
                  dataSource={strategies}
                  scroll={{ x: 900 }}
                />
                <div
                  style={{ marginTop: 10, fontSize: 12, color: 'var(--text-tertiary)' }}
                >
                  回测口径：{data.methodology?.entry_rule}，{data.methodology?.exit_rule}，
                  {data.methodology?.cost_model}。{data.methodology?.note}
                </div>
              </>
            ),
          },
        ]}
      />

      <Alert
        type="warning"
        showIcon
        banner
        style={{ marginTop: 8 }}
        message={data.disclaimer}
      />
    </Card>
  );
}

export default StrategySignalPanel;
