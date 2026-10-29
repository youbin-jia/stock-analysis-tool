import assert from 'node:assert/strict';
import test from 'node:test';
import * as echarts from 'echarts';
import {
  buildMarketChart, getHistoryZoom, DEFAULT_OVERLAYS, DEFAULT_PANELS, OVERLAY_OPTIONS,
} from './marketScenarioChart.js';

const fields = [
  'ma5', 'ma10', 'ma20', 'ma60', 'ma120', 'ma250', 'dif', 'dea', 'macd',
  'rsi14', 'k', 'd', 'j', 'boll_upper', 'boll_mid', 'boll_lower', 'atr14',
];
const data = {
  last_date: '2026-10-29', last_price: 1234,
  history: ['2026-10-27', '2026-10-28', '2026-10-29'].map((date, i) => ({
    date, open: [1195, 1220, 1234][i], close: 1200 + i * 17,
    low: 1190 + i * 17, high: 1210 + i * 17,
    ...Object.fromEntries(fields.map((field, j) => [field, 10 + j + i])),
  })),
  forward_dates: ['2026-10-30', '2026-11-02'],
  scenarios: ['p05', 'p25', 'p50', 'p75', 'p95'].map((key, i) => ({
    key, values: [1200 + i * 10, 1210 + i * 12],
  })),
};

test('all indicator panels share dates, plot boundaries, crosshair and zoom', () => {
  const { option, height } = buildMarketChart(data, { zoom: { start: 20, end: 80 } });
  assert.equal(option.grid.length, 5);
  for (const axis of option.xAxis) {
    assert.deepEqual(axis.data, [...data.history.map((row) => row.date), ...data.forward_dates]);
    assert.equal(axis.axisLabel.formatter('1990-12-19'), '1990-12-19');
    assert.equal(axis.axisLabel.alignMinLabel, 'left');
    assert.equal(axis.axisLabel.alignMaxLabel, 'right');
  }
  for (const grid of option.grid) {
    assert.equal(grid.left, option.grid[0].left);
    assert.equal(grid.right, option.grid[0].right);
    assert.ok(grid.top + grid.height < height);
  }
  for (const zoom of option.dataZoom) {
    assert.deepEqual(zoom.xAxisIndex, [0, 1, 2, 3, 4]);
    assert.equal(zoom.start, 20);
    assert.equal(zoom.end, 80);
  }
  assert.deepEqual(option.axisPointer.link, [{ xAxisIndex: 'all' }]);
  assert.equal(option.yAxis[2].min, 0);
  assert.equal(option.yAxis[2].max, 100);
  assert.equal(option.yAxis[3].max, undefined, 'KDJ J must not be clamped to 100');
  assert.equal(option.yAxis[1].min({ min: 10 }), 0, 'MACD retains the zero baseline');
  assert.equal(option.yAxis[1].max({ max: -10 }), 0, 'MACD retains the zero baseline');
});

test('calendar range presets retain all source rows and the future scenario', () => {
  const dates = [
    '1990-12-19', '2021-10-28', '2021-10-29', '2023-10-30',
    '2025-10-28', '2025-10-29', '2026-04-28', '2026-04-29', '2026-10-29',
  ];
  const historyData = { ...data, history: dates.map((date) => ({ date, close: 1000 })) };
  for (const [range, start] of Object.entries({ all: 0, '5y': 20, '3y': 30, '1y': 50, '6m': 70 })) {
    const zoom = getHistoryZoom(historyData, range);
    assert.deepEqual(zoom, { start, end: 100 });
    const chart = buildMarketChart(historyData, { zoom });
    assert.equal(chart.option.xAxis[0].data[0], '1990-12-19');
    assert.equal(chart.option.series.find((item) => item.id === 'price').data.length, 11);
    assert.deepEqual(chart.option.dataZoom.map((item) => item.start), [start, start]);
  }
  assert.equal(historyData.history.length, 9);
});

test('range presets handle short histories, empty data and leap-year month ends', () => {
  assert.deepEqual(getHistoryZoom(null, '1y'), { start: 0, end: 100 });
  assert.deepEqual(getHistoryZoom(data, '5y'), { start: 0, end: 100 });
  const leapYear = {
    last_date: '2024-08-31',
    history: ['2024-02-28', '2024-02-29', '2024-03-01', '2024-08-31'].map((date) => ({ date })),
    forward_dates: ['2024-09-02'],
  };
  assert.deepEqual(getHistoryZoom(leapYear, '6m'), { start: 25, end: 100 });
});

test('actual indicators are daily sequences and never projected into the future', () => {
  const { option } = buildMarketChart(data, { overlays: OVERLAY_OPTIONS.map(({ value }) => value) });
  for (const field of fields) {
    const series = option.series.find((item) => item.id === field);
    assert.ok(series, field);
    assert.deepEqual(series.data, [...data.history.map((row) => row[field]), null, null]);
    assert.equal(series.data.length, option.xAxis[0].data.length);
  }
  const price = option.series.find((item) => item.id === 'price');
  assert.deepEqual(price.data.slice(-2), [[null, null, null, null], [null, null, null, null]]);
  const forecast = option.series.find((item) => item.id === 'p50');
  assert.deepEqual(forecast.data.slice(0, 3), [null, null, data.last_price]);
});

test('daily candles use open/close/low/high, fixed red-up/green-down and no projected bars', () => {
  for (const isDark of [false, true]) {
    const { option } = buildMarketChart(data, { isDark });
    const price = option.series.find((series) => series.id === 'price');
    assert.equal(price.type, 'candlestick');
    assert.deepEqual(price.data.slice(0, 3), [
      [1195, 1200, 1190, 1210], [1220, 1217, 1207, 1227], [1234, 1234, 1224, 1244],
    ]);
    assert.deepEqual(price.data.slice(3), [[null, null, null, null], [null, null, null, null]]);
    assert.equal(price.itemStyle.color, isDark ? '#ff4d4f' : '#d93026');
    assert.equal(price.itemStyle.color0, isDark ? '#73d13d' : '#238636');
    assert.equal(price.itemStyle.borderColorDoji, isDark ? '#a0a0a0' : '#666666');
    assert.ok(option.xAxis.every((axis) => axis.boundaryGap === true));
    assert.deepEqual(price.markPoint.data[0].coord, [data.last_date, data.last_price]);
  }
});

test('line mode retains closing prices, zoom, indicators and scenario paths', () => {
  const options = { zoom: { start: 25, end: 90 }, legendSelected: { MA20: false } };
  const candle = buildMarketChart(data, options);
  const line = buildMarketChart(data, { ...options, chartType: 'line' });
  const price = line.option.series.find((series) => series.id === 'price');
  assert.equal(price.type, 'line');
  assert.deepEqual(price.data, [1200, 1217, 1234, null, null]);
  assert.deepEqual(line.option.dataZoom, candle.option.dataZoom);
  assert.equal(line.option.legend[0].selected.MA20, false);
  const seriesData = (option) => option.series.filter((series) => series.id !== 'price')
    .map(({ id, type, data: values, xAxisIndex, yAxisIndex }) => ({ id, type, values, xAxisIndex, yAxisIndex }));
  assert.deepEqual(
    seriesData(line.option),
    seriesData(candle.option),
  );
  assert.equal(line.height, candle.height);
});

test('candlestick tooltip reports OHLC without confusing data indices, gaps or future values', () => {
  const { option } = buildMarketChart(data);
  const text = option.tooltip.formatter([
    { seriesId: 'price', axisValue: '2026-10-28', dataIndex: 1, value: [1220, 1217, 1207, 1227], seriesIndex: 4 },
    { seriesId: 'ma5', axisValue: '2026-10-28', value: 11, seriesIndex: 10 },
  ]);
  assert.equal(text, '2026-10-28\n开盘  1220.00\n收盘  1217.00\n最高  1227.00\n最低  1207.00\n MA5  11.00');
  assert.equal(option.tooltip.formatter([
    { seriesId: 'price', axisValue: '2026-10-30', dataIndex: 3, value: [null, null, null, null] },
    { seriesId: 'p50', axisValue: '2026-10-30', value: 1200 },
  ]), '2026-10-30\n 中性  1200.00');

  const missing = buildMarketChart({ ...data, history: [{ date: data.last_date, close: 1234 }] });
  assert.deepEqual(missing.option.series.find((series) => series.id === 'price').data[0], [null, null, null, null]);
  assert.equal(missing.option.tooltip.formatter([
    { seriesId: 'price', dataIndex: 0, value: [null, 1234, null, null] },
  ]), '');
});

test('live candle refresh updates OHLC in place and preserves historical bars and zoom', () => {
  const changed = {
    ...data, last_price: 1240,
    history: data.history.map((row, i) => i === 2 ? { ...row, close: 1240, high: 1250, low: 1220 } : row),
  };
  const zoom = { start: 30, end: 100 };
  const first = buildMarketChart(data, { zoom }).option;
  const next = buildMarketChart(changed, { zoom }).option;
  const firstPrice = first.series.find((series) => series.id === 'price');
  const nextPrice = next.series.find((series) => series.id === 'price');
  assert.deepEqual(firstPrice.data.slice(0, 2), nextPrice.data.slice(0, 2));
  assert.deepEqual(nextPrice.data[2], [1234, 1240, 1220, 1250]);
  assert.equal(nextPrice.data.length, firstPrice.data.length);
  assert.deepEqual(first.dataZoom, next.dataZoom);
});

test('ECharts supplies the original candle index to tooltips after zoom and mode changes', () => {
  const chart = echarts.init(null, null, { renderer: 'svg', ssr: true, width: 1100, height: 1100 });
  try {
    for (const chartType of ['candlestick', 'line', 'candlestick']) {
      const { option } = buildMarketChart(data, { chartType, zoom: { start: 20, end: 100 } });
      chart.setOption(option, { notMerge: true });
      const price = chart.getModel().getSeriesByIndex(option.series.findIndex((series) => series.id === 'price'));
      const point = price.getDataParams(price.getData().indexOfRawIndex(1));
      assert.equal(point.dataIndex, 1);
      const text = option.tooltip.formatter([{ ...point, axisValue: '2026-10-28' }]);
      assert.ok(text.includes(chartType === 'candlestick' ? '开盘  1220.00' : '实际走势  1217.00'));
      assert.ok(chart.getOption().dataZoom.every((item) => item.start === 20 && item.end === 100));
    }
  } finally {
    chart.dispose();
  }
});

test('panel toggles rebuild contiguous axes without stale curves', () => {
  const { option, height } = buildMarketChart(data, { panels: ['kdj'], overlays: [] });
  assert.equal(option.grid.length, 2);
  assert.deepEqual(option.title.map((title) => title.text), ['KDJ']);
  assert.ok(!option.series.some((series) => ['macd', 'rsi14', 'atr14', ...DEFAULT_OVERLAYS].includes(series.id)));
  assert.equal(option.series.find((series) => series.id === 'j').yAxisIndex, 1);
  assert.ok(height < buildMarketChart(data).height);
  const priceOnly = buildMarketChart(data, { panels: [], overlays: [] });
  assert.equal(priceOnly.option.grid.length, 1);
  assert.ok(priceOnly.option.series.every((series) => series.yAxisIndex === 0));
});

test('missing warmup points stay null and selected legend state is preserved', () => {
  const short = { ...data, history: [{ date: data.last_date, close: data.last_price }] };
  const { option } = buildMarketChart(short, { legendSelected: { MA20: false } });
  assert.deepEqual(option.series.find((series) => series.id === 'ma20').data, [null, null, null]);
  assert.equal(option.legend[0].selected.MA20, false);
  assert.equal(buildMarketChart(null), null);
});

test('live refresh changes latest indicator point and retains preceding curve', () => {
  const changed = {
    ...data,
    history: data.history.map((row, i) => i === 2 ? { ...row, dif: 90 } : row),
  };
  const first = buildMarketChart(data).option.series.find((series) => series.id === 'dif');
  const next = buildMarketChart(changed).option.series.find((series) => series.id === 'dif');
  assert.deepEqual(first.data.slice(0, 2), next.data.slice(0, 2));
  assert.equal(next.data[2], 90);
});

test('tooltip has one date and omits unavailable and synthetic band values', () => {
  const { option } = buildMarketChart(data);
  const text = option.tooltip.formatter([
    { seriesId: 'p50', axisValue: '2026-10-30', value: 1200, marker: '' },
    { seriesId: 'rsi14', axisValue: '2026-10-30', value: null, marker: '' },
    { seriesId: 'outer-span', axisValue: '2026-10-30', value: 40, marker: '' },
  ]);
  assert.equal(text, '2026-10-30\n 中性  1200.00');
  assert.equal(option.tooltip.formatter([{ seriesId: 'dif', value: null }]), '');
});

test('ECharts renders and replaces all panel combinations without stale axes', () => {
  const chart = echarts.init(null, null, { renderer: 'svg', ssr: true, width: 1100, height: 1100 });
  try {
    for (const chartType of ['candlestick', 'line', 'candlestick']) {
      for (const panels of [DEFAULT_PANELS, ['rsi', 'atr'], [], ['kdj'], DEFAULT_PANELS]) {
        const { option, height } = buildMarketChart(data, { chartType, panels });
        chart.resize({ width: 1100, height });
        chart.setOption(option, { notMerge: true });
        assert.equal(chart.getOption().grid.length, panels.length + 1);
        assert.equal(chart.getOption().series.filter((series) => series.id === 'price').length, 1);
        assert.equal(chart.getOption().series.find((series) => series.id === 'price').type, chartType);
        const svg = chart.renderToSVGString();
        assert.ok(svg.includes('<path'), 'chart contains rendered data paths');
        assert.ok(!svg.includes('NaN'), `non-finite coordinates: ${svg.match(/.{0,80}NaN.{0,80}/g)}`);
      }
    }
  } finally {
    chart.dispose();
  }
});

test('long histories render without dropping early index or indicator points', () => {
  const dateAt = (i) => new Date(Date.UTC(1990, 11, 19) + i * 86400000).toISOString().slice(0, 10);
  const history = Array.from({ length: 8751 }, (_, i) => ({
    ...data.history[0], date: dateAt(i), close: 1000 + i / 10,
    open: 999 + i / 10, low: 998 + i / 10, high: 1002 + i / 10,
  }));
  const longData = {
    ...data, history, last_date: dateAt(8750), last_price: history.at(-1).close,
    forward_dates: [dateAt(8751), dateAt(8752)],
  };
  const { option, height } = buildMarketChart(longData);
  assert.equal(option.xAxis[0].data[0], '1990-12-19');
  assert.equal(option.xAxis[0].data.length, 8753);
  assert.deepEqual(option.series.find((item) => item.id === 'price').data[0], [999, 1000, 998, 1002]);
  assert.equal(option.series.find((item) => item.id === 'rsi14').data.length, 8753);
  const chart = echarts.init(null, null, { renderer: 'svg', ssr: true, width: 1100, height });
  try {
    chart.setOption(option);
    const svg = chart.renderToSVGString();
    assert.ok(svg.includes('1990-12-19'));
    assert.ok(!svg.includes('NaN'));
    chart.dispatchAction({ type: 'dataZoom', ...getHistoryZoom(longData, '1y') }, { silent: true });
    assert.ok(chart.getOption().dataZoom.every((item) => item.start > 0));
    chart.dispatchAction({ type: 'dataZoom', ...getHistoryZoom(longData) }, { silent: true });
    assert.ok(chart.getOption().dataZoom.every((item) => item.start === 0 && item.end === 100));
  } finally {
    chart.dispose();
  }
});
