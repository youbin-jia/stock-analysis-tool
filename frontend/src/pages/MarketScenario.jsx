import { useState, useEffect, useMemo, useRef } from 'react';
import { Segmented, Select, Alert, Spin, Empty, Table, Tag, Button, Switch, Tooltip, Checkbox } from 'antd';
import { LineChartOutlined, ReloadOutlined, StockOutlined, ZoomOutOutlined } from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import axios from 'axios';
import { useTheme } from '../context/ThemeContext';
import MarketCloseReview from '../components/MarketCloseReview';
import {
  buildMarketChart, getHistoryZoom, HISTORY_RANGE_OPTIONS,
  DEFAULT_OVERLAYS, DEFAULT_PANELS, OVERLAY_OPTIONS, PANEL_OPTIONS,
} from './marketScenarioChart';
import './MarketScenario.css';

const REFRESH_MS = 15000;
const DEFAULT_INDEXES = [
  { code: 'sh000688', name: '科创50' }, { code: 'sh000001', name: '上证指数' },
  { code: 'sz399006', name: '创业板指' }, { code: 'sh000300', name: '沪深300' },
  { code: 'sz399001', name: '深证成指' }, { code: 'sh000905', name: '中证500' },
  { code: 'sh000852', name: '中证1000' },
];
const QUOTE_STATUS = {
  live: { color: 'success', label: '盘中行情' },
  delayed: { color: 'warning', label: '行情延迟' },
  closed: { color: 'default', label: '非交易时段' },
  historical: { color: 'warning', label: '历史日线' },
};

const number = (value, digits = 2) => (
  value == null || !Number.isFinite(Number(value))
    ? '—'
    : Number(value).toLocaleString('zh-CN', { minimumFractionDigits: digits, maximumFractionDigits: digits })
);
const signed = (value) => value == null ? '—' : `${value > 0 ? '+' : ''}${number(value)}`;
const changeColor = (value) => value == null || value === 0
  ? 'var(--text-primary)' : value > 0 ? 'var(--up-color)' : 'var(--down-color)';
const compact = (value, unit) => {
  if (value == null) return '—';
  if (value >= 1e8) return `${number(value / 1e8)} 亿${unit}`;
  if (value >= 1e4) return `${number(value / 1e4)} 万${unit}`;
  return `${number(value, 0)} ${unit}`;
};
const timestamp = (value) => value ? new Date(value).toLocaleString('zh-CN', {
  timeZone: 'Asia/Shanghai', hour12: false,
  year: 'numeric', month: '2-digit', day: '2-digit',
  hour: '2-digit', minute: '2-digit', second: '2-digit',
}) : '—';

function Metric({ label, value, color }) {
  return (
    <div className="market-metric">
      <dt>{label}</dt>
      <dd style={{ color }}>{value}</dd>
    </div>
  );
}

const FORWARD_OPTIONS = [
  { label: '1个月', value: 21 },
  { label: '2个月', value: 42 },
  { label: '3个月', value: 63 },
];

const VOL_OPTIONS = [
  { label: '近20日波动', value: 20 },
  { label: '近60日波动', value: 60 },
  { label: '近250日波动', value: 250 },
];

function MarketScenario() {
  const { isDark } = useTheme();
  const [indexes, setIndexes] = useState(DEFAULT_INDEXES);
  const [indexCode, setIndexCode] = useState('sh000688');
  const [forwardDays, setForwardDays] = useState(42);
  const [volWindow, setVolWindow] = useState(60);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [error, setError] = useState(null);
  const [overlays, setOverlays] = useState(DEFAULT_OVERLAYS);
  const [panels, setPanels] = useState(DEFAULT_PANELS);
  const [historyRange, setHistoryRange] = useState('all');
  const [chartType, setChartType] = useState('candlestick');
  const historyRangeRef = useRef('all');
  const autoRefreshRef = useRef(true);
  const refreshRef = useRef(null);
  const chartRef = useRef(null);
  const zoomRef = useRef({ start: 0, end: 100 });
  const legendRef = useRef({});

  useEffect(() => {
    const controller = new AbortController();
    axios
      .get('/api/market/indexes', { signal: controller.signal, timeout: 10000 })
      .then((res) => setIndexes(res.data))
      .catch(() => {});
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    let inFlight = false;
    zoomRef.current = { start: 0, end: 100 };
    if (historyRangeRef.current === 'custom') {
      historyRangeRef.current = 'all';
      setHistoryRange('all');
    }
    setData(null);
    setError(null);
    setLoading(true);

    const load = async (force = false) => {
      if (inFlight || !active) return;
      inFlight = true;
      setRefreshing(true);
      try {
        const res = await axios.get('/api/market/scenario', {
          params: { index_code: indexCode, forward_days: forwardDays, vol_window: volWindow, refresh: force },
          signal: controller.signal,
          timeout: 20000,
        });
        if (active) {
          if (historyRangeRef.current !== 'custom') {
            zoomRef.current = getHistoryZoom(res.data, historyRangeRef.current);
          }
          setData(res.data);
          setError(null);
        }
      } catch (err) {
        if (active && !axios.isCancel(err)) {
          setError('行情刷新失败，已保留上次数据。');
        }
      } finally {
        inFlight = false;
        if (active) {
          setLoading(false);
          setRefreshing(false);
        }
      }
    };

    refreshRef.current = () => load(true);
    load();
    const timer = window.setInterval(() => {
      if (autoRefreshRef.current && !document.hidden) load();
    }, REFRESH_MS);
    const onVisible = () => {
      if (!document.hidden && autoRefreshRef.current) load();
    };
    document.addEventListener('visibilitychange', onVisible);
    return () => {
      active = false;
      controller.abort();
      window.clearInterval(timer);
      document.removeEventListener('visibilitychange', onVisible);
      refreshRef.current = null;
    };
  }, [indexCode, forwardDays, volWindow]);

  useEffect(() => {
    autoRefreshRef.current = autoRefresh;
    if (autoRefresh) refreshRef.current?.();
  }, [autoRefresh]);

  const chart = useMemo(() => buildMarketChart(data, {
    isDark, chartType, overlays, panels, zoom: zoomRef.current, legendSelected: legendRef.current,
  }), [data, isDark, chartType, overlays, panels]);

  const quote = data?.quote;
  const indicators = data?.indicators || {};
  const isCurrentDate = data?.last_date === data?.generated_at?.slice(0, 10);
  const status = QUOTE_STATUS[quote?.status] || QUOTE_STATUS.historical;
  const recordZoom = (event) => {
    const next = event.batch?.[0] || event;
    if (Number.isFinite(next.start) && Number.isFinite(next.end)) {
      zoomRef.current = { start: next.start, end: next.end };
      const range = next.start === 0 && next.end === 100 ? 'all' : 'custom';
      historyRangeRef.current = range;
      setHistoryRange(range);
    }
  };
  const chartEvents = useMemo(() => ({
    datazoom: recordZoom,
    legendselectchanged: (event) => { legendRef.current = event.selected; },
  }), []);
  const changeHistoryRange = (range) => {
    historyRangeRef.current = range;
    setHistoryRange(range);
    zoomRef.current = getHistoryZoom(data, range);
    chartRef.current?.getEchartsInstance().dispatchAction({
      type: 'dataZoom', ...zoomRef.current,
    }, { silent: true });
  };

  return (
    <div className="market-scenario">
      <header className="market-toolbar">
        <div className="market-controls">
          <h1>指数情景</h1>
          <Select
            aria-label="选择指数"
            value={indexCode}
            onChange={setIndexCode}
            className="market-index-select"
            options={indexes.map((i) => ({ label: i.name, value: i.code }))}
          />
        </div>
        <div className="market-refresh">
          <span>自动刷新 · 15 秒</span>
          <Switch size="small" aria-label="自动刷新" checked={autoRefresh} onChange={setAutoRefresh} />
          <Tooltip title="立即刷新行情">
            <Button
              aria-label="立即刷新行情"
              icon={<ReloadOutlined spin={refreshing} />}
              disabled={refreshing}
              onClick={() => refreshRef.current?.()}
            />
          </Tooltip>
        </div>
      </header>
      {error && <Alert type="error" showIcon message={data ? error : '行情加载失败，请重试。'} />}
      {quote?.status === 'historical' && (
        <Alert type="warning" showIcon message={`实时行情暂不可用，当前显示 ${data.last_date} 历史日线。`} />
      )}
      {quote?.status === 'delayed' && (
        <Alert type="warning" showIcon message={`行情源尚未更新，报价时间：${timestamp(quote.timestamp)}。`} />
      )}

      <Spin spinning={loading}>
        {data ? (
          <>
            <section className="market-section market-quote" aria-label="指数行情">
              <div className="market-price-block">
                <div className="market-name">
                  <h2>{data.index_name}</h2>
                  <span>{data.index_code.toUpperCase()}</span>
                  <Tag color={error ? 'error' : !autoRefresh ? 'default' : status.color}>
                    {error ? '刷新失败' : !autoRefresh ? '已暂停刷新' : status.label}
                  </Tag>
                </div>
                <div className="market-price" style={{ color: changeColor(quote?.change_percent) }}>
                  <strong data-testid="index-price">{number(data.last_price)}</strong>
                  <span>{signed(quote?.change_percent)}%</span>
                  <span>{signed(quote?.change)}</span>
                </div>
                <div className="market-quote-time">
                  行情时间 {quote?.timestamp ? timestamp(quote.timestamp) : data.last_date}
                </div>
                <div className="market-quote-time">
                  {quote?.source || '历史日线'} · 检查于 <span data-testid="checked-at">{timestamp(data.generated_at)}</span>
                </div>
              </div>
              <dl className="market-quote-metrics">
                <Metric label="前收" value={number(quote?.prev_close)} />
                <Metric label={isCurrentDate ? '今开' : '开盘'} value={number(quote?.open)} />
                <Metric label="最高" value={number(quote?.high)} color={changeColor(quote?.high - quote?.prev_close)} />
                <Metric label="最低" value={number(quote?.low)} color={changeColor(quote?.low - quote?.prev_close)} />
                <Metric label="涨跌幅" value={`${signed(quote?.change_percent)}%`} color={changeColor(quote?.change_percent)} />
                <Metric label="振幅" value={quote?.amplitude == null ? '—' : `${number(quote.amplitude)}%`} />
                <Metric label="成交量" value={compact(quote?.volume, '手')} />
                <Metric label="成交额" value={compact(quote?.amount, '元')} />
              </dl>
            </section>

            <MarketCloseReview indexCode={indexCode} autoRefresh={autoRefresh} />

            <section className="market-section" aria-label="指数与指标走势">
              <div className="market-section-heading market-scenario-options">
                <h3>日线走势与情景区间</h3>
                <div className="market-controls">
                  <Segmented aria-label="推演周期" options={FORWARD_OPTIONS} value={forwardDays} onChange={setForwardDays} />
                  <Segmented aria-label="波动率窗口" options={VOL_OPTIONS} value={volWindow} onChange={setVolWindow} />
                </div>
              </div>
              <dl className="market-scenario-summary">
                <Metric label={`年化波动率 · ${data.vol_window} 日`} value={`${number(data.annualized_vol, 1)}%`} />
                <Metric label="波动率数据截至" value={data.volatility_as_of} />
                <Metric label={`推演终点 · ${data.forward_days} 日后`} value={data.forward_dates.at(-1)} />
                <Metric
                  label="终点 50% 情景区间"
                  value={`${number(data.scenarios.find((s) => s.key === 'p25')?.end_value)} ~ ${number(data.scenarios.find((s) => s.key === 'p75')?.end_value)}`}
                />
              </dl>
              <div className="market-history-controls">
                <Segmented
                  aria-label="图表类型"
                  options={[
                    { label: 'K线', value: 'candlestick', icon: <StockOutlined /> },
                    { label: '走势', value: 'line', icon: <LineChartOutlined /> },
                  ]}
                  value={chartType}
                  onChange={setChartType}
                />
                <Segmented
                  aria-label="历史区间"
                  options={HISTORY_RANGE_OPTIONS}
                  value={historyRange}
                  onChange={changeHistoryRange}
                />
                <span className="market-history-coverage" data-testid="history-coverage">
                  可用日线 {data.history_start || data.history[0]?.date} 至 {data.last_date}
                  {' · '}{number(data.history_count ?? data.history.length, 0)} 个交易日
                </span>
                {historyRange === 'custom' && <Tag>自定义区间</Tag>}
              </div>
              <div className="market-chart-controls">
                <div className="market-chart-selection" role="group" aria-label="主图叠加">
                  <span>主图</span>
                  <Checkbox.Group options={OVERLAY_OPTIONS} value={overlays} onChange={setOverlays} />
                </div>
                <div className="market-chart-selection" role="group" aria-label="指标副图">
                  <span>副图</span>
                  <Checkbox.Group options={PANEL_OPTIONS} value={panels} onChange={setPanels} />
                  <Tooltip title="重置图表缩放">
                    <Button aria-label="重置图表缩放" size="small" icon={<ZoomOutOutlined />} onClick={() => changeHistoryRange('all')} />
                  </Tooltip>
                </div>
              </div>
              <div
                className="market-chart"
                role="img"
                aria-label={`${data.index_name}${chartType === 'candlestick' ? '日K线' : '日线走势'}与${PANEL_OPTIONS.filter((panel) => panels.includes(panel.value)).map((panel) => panel.label).join('、')}指标走势`}
                style={{ height: chart?.height || 386 }}
              >
                {chart ? (
                  <ReactECharts
                    ref={chartRef}
                    option={chart.option}
                    onEvents={chartEvents}
                    style={{ height: '100%', width: '100%' }}
                    notMerge
                    lazyUpdate
                  />
                ) : <Empty />}
              </div>
            </section>

            <section className="market-section" aria-label="主要技术指标">
              <div className="market-section-heading">
                <h3>最新指标读数</h3>
                <span>截至 {data.last_date}{quote?.is_intraday ? ' · 盘中值' : ''}</span>
              </div>
              <dl className="market-ma-grid">
                {[5, 10, 20, 60, 120, 250].map((period) => (
                  <Metric key={period} label={`MA${period}`} value={number(indicators[`ma${period}`])} />
                ))}
              </dl>
              <div className="market-indicator-groups">
                <div className="market-indicator-group">
                  <h4>MACD <span>(12, 26, 9)</span></h4>
                  <dl>
                    <Metric label="DIF" value={number(indicators.dif)} />
                    <Metric label="DEA" value={number(indicators.dea)} />
                    <Metric label="MACD" value={signed(indicators.macd)} color={changeColor(indicators.macd)} />
                  </dl>
                </div>
                <div className="market-indicator-group">
                  <h4>KDJ <span>(9, 3, 3)</span></h4>
                  <dl>
                    <Metric label="K" value={number(indicators.k)} />
                    <Metric label="D" value={number(indicators.d)} />
                    <Metric label="J" value={number(indicators.j)} />
                  </dl>
                </div>
                <div className="market-indicator-group">
                  <h4>布林带 <span>(20, 2)</span></h4>
                  <dl>
                    <Metric label="上轨" value={number(indicators.boll_upper)} />
                    <Metric label="中轨" value={number(indicators.boll_mid)} />
                    <Metric label="下轨" value={number(indicators.boll_lower)} />
                  </dl>
                </div>
                <div className="market-indicator-group">
                  <h4>强弱与波动</h4>
                  <dl className="market-two-metrics">
                    <Metric label="RSI (14)" value={number(indicators.rsi14)} />
                    <Metric label="ATR (14)" value={number(indicators.atr14)} />
                  </dl>
                </div>
              </div>
            </section>

            <div className="market-tables">
              <section className="market-section">
                <h3>终点情景</h3>
                <Table
                  size="small"
                  pagination={false}
                  rowKey="key"
                  dataSource={data.scenarios}
                  columns={[
                    { title: '情景', dataIndex: 'label' },
                    {
                      title: '累计概率', dataIndex: 'probability',
                      render: (v) => `${(v * 100).toFixed(0)}%`,
                    },
                    { title: '点位', dataIndex: 'end_value', render: (v) => number(v) },
                    {
                      title: '较现价', dataIndex: 'end_change_pct',
                      render: (v) => <span style={{ color: changeColor(v) }}>{signed(v)}%</span>,
                    },
                  ]}
                />
              </section>
              <section className="market-section">
                <h3>关键位置</h3>
                <Table
                  size="small"
                  pagination={false}
                  rowKey="name"
                  dataSource={data.levels}
                  columns={[
                    { title: '位置', dataIndex: 'name' },
                    { title: '点位', dataIndex: 'value', render: (v) => number(v) },
                    {
                      title: '现价相对', dataIndex: 'distance_pct',
                      render: (v) => <span style={{ color: changeColor(v) }}>{signed(v)}%</span>,
                    },
                  ]}
                />
              </section>
            </div>
            <footer className="market-disclaimer">
              历史波动率、零漂移假设下的情景区间，非方向预测，不构成投资建议。
              未来日期仅排除周末，未调整法定节假日；免费行情可能存在延迟。
            </footer>
          </>
        ) : (
          <div className="market-empty">
            {!loading && (
              <Empty description="暂无指数数据">
                <Button icon={<ReloadOutlined />} onClick={() => refreshRef.current?.()}>重试</Button>
              </Empty>
            )}
          </div>
        )}
      </Spin>
      {!data && !loading && <MarketCloseReview indexCode={indexCode} autoRefresh={autoRefresh} />}
    </div>
  );
}

export default MarketScenario;
