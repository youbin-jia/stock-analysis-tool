import { useEffect, useRef, useState } from 'react';
import { Alert, Button, Collapse, Spin, Tag, Tooltip } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import axios from 'axios';

const REFRESH_MS = 60000;
const TREND_COLOR = { bullish: 'red', bearish: 'green', neutral: 'default' };
const STATE_LABEL = { ready: '当日复盘', waiting_close: '待收盘更新', pending_data: '最近可用复盘' };
const number = (value) => Number(value).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const percent = (value) => `${value > 0 ? '+' : ''}${number(value)}%`;

export default function MarketCloseReview({ indexCode, autoRefresh }) {
  const [snapshot, setSnapshot] = useState(null);
  const [refreshing, setRefreshing] = useState(true);
  const [error, setError] = useState(null);
  const refreshRef = useRef(null);
  const autoRefreshRef = useRef(autoRefresh);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    let inFlight = false;
    setSnapshot(null);
    setError(null);
    const load = async (force = false) => {
      if (inFlight || !active) return;
      inFlight = true;
      setRefreshing(true);
      try {
        const response = await axios.get('/api/market/close-review', {
          params: { index_code: indexCode, refresh: force },
          signal: controller.signal, timeout: 30000,
        });
        if (active) {
          setSnapshot(response.data);
          setError(null);
        }
      } catch (err) {
        if (active && !axios.isCancel(err)) setError('收盘复盘暂时无法更新，未覆盖已有结论。');
      } finally {
        inFlight = false;
        if (active) setRefreshing(false);
      }
    };
    refreshRef.current = () => load(true);
    load();
    const timer = window.setInterval(() => {
      if (autoRefreshRef.current && !document.hidden) load();
    }, REFRESH_MS);
    const onVisible = () => {
      if (autoRefreshRef.current && !document.hidden) load();
    };
    document.addEventListener('visibilitychange', onVisible);
    return () => {
      active = false;
      controller.abort();
      window.clearInterval(timer);
      document.removeEventListener('visibilitychange', onVisible);
      refreshRef.current = null;
    };
  }, [indexCode]);

  useEffect(() => {
    autoRefreshRef.current = autoRefresh;
    if (autoRefresh) refreshRef.current?.();
  }, [autoRefresh]);

  const report = snapshot?.report;
  return (
    <section className="market-section market-close-review" aria-label="收盘复盘">
      <div className="market-section-heading">
        <div className="market-controls">
          <h3>收盘复盘</h3>
          {report && <time data-testid="review-date" dateTime={report.trade_date}>{report.trade_date}</time>}
          {snapshot && <Tag data-testid="review-state">{STATE_LABEL[snapshot.state]}</Tag>}
        </div>
        <div className="market-review-refresh">
          <span>{snapshot?.schedule || '北京时间 15:30；16:30、17:30 补查'}</span>
          <Tooltip title="刷新收盘复盘">
            <Button
              aria-label="刷新收盘复盘" size="small"
              icon={<ReloadOutlined spin={refreshing} />}
              disabled={refreshing} onClick={() => refreshRef.current?.()}
            />
          </Tooltip>
        </div>
      </div>
      {(error || snapshot?.error) && <Alert showIcon type="warning" message={error || snapshot.error} />}
      {snapshot?.state !== 'ready' && snapshot?.message && (
        <p className="market-review-status">{snapshot.message}</p>
      )}
      {!snapshot && refreshing && <div className="market-review-loading"><Spin size="small" /></div>}
      {report ? (
        <>
          <div className="market-review-summary">
            <div className="market-review-verdict">
              <Tag color={TREND_COLOR[report.trend]} data-testid="review-verdict">{report.verdict}</Tag>
              <strong>{report.stance}</strong>
              <p>{report.summary}</p>
            </div>
            <dl className="market-review-metrics">
              <div><dt>收盘点位</dt><dd>{number(report.close)}</dd></div>
              <div><dt>当日涨跌</dt><dd>{percent(report.change_percent)}</dd></div>
              <div><dt>近5日涨跌</dt><dd>{percent(report.change_5d)}</dd></div>
              <div><dt>ATR / 收盘</dt><dd>{number(report.atr_percent)}%</dd></div>
            </dl>
          </div>
          <dl className="market-review-strategies">
            {report.strategies.map((strategy) => (
              <div key={strategy.title}>
                <dt>{strategy.title}</dt><dd>{strategy.detail}</dd>
              </div>
            ))}
          </dl>
          <Collapse
            ghost
            items={[{
              key: 'evidence',
              label: '判断依据、关键位置与风险',
              children: (
                <div className="market-review-details">
                  <dl className="market-review-evidence">
                    {report.evidence.map((item) => (
                      <div key={item.key}>
                        <dt>{item.name}</dt>
                        <dd>{item.detail}{item.signal && <span className="market-review-signal">当日信号：{item.signal}</span>}</dd>
                      </div>
                    ))}
                  </dl>
                  <dl className="market-review-levels">
                    {report.levels.map((level) => (
                      <div key={level.name}>
                        <dt>{level.name} · {level.role}</dt><dd>{number(level.value)}</dd>
                      </div>
                    ))}
                  </dl>
                  <ul>{report.risks.map((risk) => <li key={risk}>{risk}</li>)}</ul>
                  <p>{report.methodology}</p>
                  <p className="market-review-provenance">
                    {report.source} · 生成于 {new Date(report.generated_at).toLocaleString('zh-CN', {
                      timeZone: 'Asia/Shanghai', hour12: false,
                    })}
                  </p>
                </div>
              ),
            }]}
          />
          <p className="market-review-disclaimer">{report.disclaimer}</p>
        </>
      ) : !refreshing && (
        <p className="market-review-status">暂无完整收盘复盘，等待可验证的日线数据。</p>
      )}
    </section>
  );
}
