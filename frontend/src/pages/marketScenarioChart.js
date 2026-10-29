import dayjs from 'dayjs';

export const HISTORY_RANGE_OPTIONS = [
  { label: '近半年', value: '6m' },
  { label: '近1年', value: '1y' },
  { label: '近3年', value: '3y' },
  { label: '近5年', value: '5y' },
  { label: '全部历史', value: 'all' },
];

export function getHistoryZoom(data, range = 'all') {
  const months = { '6m': 6, '1y': 12, '3y': 36, '5y': 60 }[range];
  if (!months || !data?.history?.length) return { start: 0, end: 100 };
  const cutoff = dayjs(data.last_date).subtract(months, 'month').format('YYYY-MM-DD');
  const first = data.history.findIndex((row) => row.date >= cutoff);
  const last = data.history.length + data.forward_dates.length - 1;
  return { start: last > 0 ? Math.max(first, 0) / last * 100 : 0, end: 100 };
}

export const OVERLAY_OPTIONS = [
  ...[5, 10, 20, 60, 120, 250].map((period) => ({ label: `MA${period}`, value: `ma${period}` })),
  { label: 'BOLL', value: 'boll' },
];
export const PANEL_OPTIONS = [
  { label: 'MACD', value: 'macd' },
  { label: 'RSI', value: 'rsi' },
  { label: 'KDJ', value: 'kdj' },
  { label: 'ATR', value: 'atr' },
];
export const DEFAULT_OVERLAYS = ['ma5', 'ma20', 'ma60'];
export const DEFAULT_PANELS = PANEL_OPTIONS.map(({ value }) => value);

const MA_COLORS = ['#e7b44c', '#ec8c9c', '#4aa3ff', '#bd8af0', '#55c5b6', '#a8bb76'];
const PANELS = {
  macd: { lines: [['dif', 'DIF', '#e7b44c'], ['dea', 'DEA', '#4aa3ff']], guides: [0] },
  rsi: { lines: [['rsi14', 'RSI (14)', '#bd8af0']], guides: [30, 70] },
  kdj: {
    lines: [['k', 'K (9)', '#e7b44c'], ['d', 'D (3)', '#4aa3ff'], ['j', 'J (3)', '#ec8c9c']],
    guides: [20, 80],
  },
  atr: { lines: [['atr14', 'ATR (14)', '#55c5b6']], guides: [] },
};

export function buildMarketChart(data, {
  isDark = false,
  chartType = 'candlestick',
  overlays = DEFAULT_OVERLAYS,
  panels = DEFAULT_PANELS,
  zoom = { start: 0, end: 100 },
  legendSelected = {},
} = {}) {
  if (!data?.history?.length) return null;

  const textColor = isDark ? '#e8e8e8' : '#333333';
  const axisColor = isDark ? '#a0a0a0' : '#666666';
  const gridColor = isDark ? '#303030' : '#e8e8e8';
  const isCandlestick = chartType === 'candlestick';
  const upColor = isDark ? '#ff4d4f' : '#d93026';
  const downColor = isDark ? '#73d13d' : '#238636';
  const activePanels = PANEL_OPTIONS.filter(({ value }) => panels.includes(value));
  const dates = [...data.history.map((row) => row.date), ...data.forward_dates];
  const future = new Array(data.forward_dates.length).fill(null);
  const historySeries = (field) => [...data.history.map((row) => row[field] ?? null), ...future];
  const candles = data.history.map((row) => {
    const values = [row.open, row.close, row.low, row.high];
    return values.every(Number.isFinite) ? values : [null, null, null, null];
  });
  const forward = (key) => [
    ...new Array(data.history.length - 1).fill(null),
    data.last_price,
    ...data.scenarios.find((scenario) => scenario.key === key).values,
  ];
  const line = (id, name, values, color, axisIndex = 0, style = {}) => ({
    id, name, type: 'line', data: values,
    xAxisIndex: axisIndex, yAxisIndex: axisIndex,
    showSymbol: false, connectNulls: false,
    itemStyle: { color }, lineStyle: { width: 1.4, color, ...style },
  });
  const band = (lowKey, highKey, opacity, stack) => {
    const low = forward(lowKey);
    const high = forward(highKey);
    return [
      { id: `${stack}-base`, data: low, areaStyle: { opacity: 0 } },
      {
        id: `${stack}-span`,
        data: high.map((value, i) => value == null ? null : Number((value - low[i]).toFixed(2))),
        areaStyle: { color: `rgba(24,144,255,${opacity})` },
      },
    ].map((part) => ({
      ...part, type: 'line', stack, xAxisIndex: 0, yAxisIndex: 0,
      showSymbol: false, lineStyle: { opacity: 0 },
      tooltip: { show: false }, silent: true,
    }));
  };
  const series = [
    ...band('p05', 'p95', 0.08, 'outer'),
    ...band('p25', 'p75', 0.16, 'inner'),
    {
      ...(isCandlestick ? {
        id: 'price', name: 'K线', type: 'candlestick',
        xAxisIndex: 0, yAxisIndex: 0,
        data: [...candles, ...future.map(() => [null, null, null, null])],
        barMaxWidth: 12,
        itemStyle: {
          color: upColor, color0: downColor,
          borderColor: upColor, borderColor0: downColor, borderColorDoji: axisColor,
        },
      } : line('price', '实际走势', historySeries('close'), textColor, 0, { width: 2 })),
      markLine: {
        silent: true, symbol: 'none',
        lineStyle: { color: axisColor, type: 'dashed', opacity: 0.6 },
        label: { show: false },
        data: [{ xAxis: data.last_date }],
      },
      markPoint: {
        symbol: 'circle', symbolSize: 6, label: { show: false },
        itemStyle: { color: '#4aa3ff' },
        data: [{ coord: [data.last_date, data.last_price], value: data.last_price }],
      },
    },
    line('p95', '极端乐观', forward('p95'), '#ff4d4f', 0, { type: 'dotted', width: 1 }),
    line('p75', '乐观', forward('p75'), '#ff7875', 0, { type: 'dashed', width: 1 }),
    line('p50', '中性', forward('p50'), '#4aa3ff', 0, { type: 'dashed', width: 2 }),
    line('p25', '悲观', forward('p25'), '#83c97d', 0, { type: 'dashed', width: 1 }),
    line('p05', '极端悲观', forward('p05'), '#52c41a', 0, { type: 'dotted', width: 1 }),
  ];
  [5, 10, 20, 60, 120, 250].forEach((period, i) => {
    if (overlays.includes(`ma${period}`)) {
      series.push(line(`ma${period}`, `MA${period}`, historySeries(`ma${period}`), MA_COLORS[i]));
    }
  });
  if (overlays.includes('boll')) {
    [
      ['boll_upper', 'BOLL 上轨', '#55c5b6'],
      ['boll_mid', 'BOLL 中轨', '#e7b44c'],
      ['boll_lower', 'BOLL 下轨', '#55c5b6'],
    ].forEach(([field, name, color]) => {
      series.push(line(field, name, historySeries(field), color, 0, { type: 'dashed', width: 1 }));
    });
  }

  const grid = [{ left: 56, right: 16, top: 42, height: 280 }];
  const title = [];
  const legend = [{
    id: 'price-legend', type: 'scroll', top: 0, left: 0, right: 0,
    data: series.filter((item) => item.name).map((item) => item.name),
    selected: legendSelected,
    textStyle: { color: axisColor, fontSize: 11 },
    pageTextStyle: { color: axisColor },
    pageIconColor: axisColor,
    itemWidth: 14, itemHeight: 8,
  }];
  let bottom = 322;
  activePanels.forEach(({ value, label }, i) => {
    const axisIndex = i + 1;
    const panel = PANELS[value];
    const top = bottom + 50;
    grid.push({ left: 56, right: 16, top, height: 108 });
    title.push({
      text: label, left: 0, top: top - 28, padding: 0,
      textStyle: { color: textColor, fontSize: 12, fontWeight: 500 },
    });
    const panelSeries = panel.lines.map(([field, name, color]) => (
      line(field, name, historySeries(field), color, axisIndex)
    ));
    if (value === 'macd') {
      panelSeries.unshift({
        id: 'macd', name: 'MACD', type: 'bar', data: historySeries('macd'),
        xAxisIndex: axisIndex, yAxisIndex: axisIndex, barMaxWidth: 6,
        itemStyle: { color: ({ value: amount }) => amount >= 0 ? '#ef5350' : '#26a69a' },
      });
    }
    panelSeries[0].markLine = {
      silent: true, symbol: 'none',
      lineStyle: { color: axisColor, type: 'dashed', opacity: 0.45 },
      label: { show: false },
      data: panel.guides.map((level) => ({ yAxis: level })),
    };
    legend.push({
      id: `${value}-legend`, type: 'scroll', left: 64, right: 0, top: top - 32,
      data: panelSeries.map((item) => item.name), selectedMode: false,
      itemWidth: 12, itemHeight: 7, itemGap: 12,
      textStyle: { color: axisColor, fontSize: 10 },
      pageTextStyle: { color: axisColor }, pageIconColor: axisColor,
    });
    series.push(...panelSeries);
    bottom = top + 108;
  });

  const xAxis = grid.map((_, i) => ({
    id: `x-${i}`, gridIndex: i, type: 'category', data: dates,
    boundaryGap: isCandlestick, min: 'dataMin', max: 'dataMax',
    axisLine: { onZero: false, lineStyle: { color: gridColor } },
    axisTick: { show: false }, splitLine: { show: false },
    axisLabel: {
      show: i === 0 || i === grid.length - 1,
      color: axisColor, fontSize: 10, hideOverlap: true,
      showMinLabel: true, showMaxLabel: true, alignMinLabel: 'left', alignMaxLabel: 'right',
      formatter: (value) => value,
    },
    axisPointer: { label: { show: i === grid.length - 1 } },
  }));
  const yAxis = grid.map((_, i) => ({
    id: `y-${i}`, gridIndex: i, type: 'value', scale: true, splitNumber: i === 0 ? 4 : 2,
    ...(activePanels[i - 1]?.value === 'rsi' ? { min: 0, max: 100 } : {}),
    ...(activePanels[i - 1]?.value === 'macd' ? {
      min: ({ min }) => Math.min(min, 0), max: ({ max }) => Math.max(max, 0),
    } : {}),
    axisLine: { show: false }, axisTick: { show: false },
    axisLabel: {
      color: axisColor, fontSize: 10, hideOverlap: true,
      formatter: (value) => Number(value.toFixed(2)).toLocaleString('en-US'),
    },
    splitLine: { lineStyle: { color: gridColor } },
    axisPointer: { label: { precision: 2 } },
  }));
  const axisIndexes = grid.map((_, i) => i);
  const seriesById = new Map(series.filter((item) => item.name).map((item) => [item.id, item]));

  return {
    height: bottom + 64,
    option: {
      animation: false,
      title, legend, grid, xAxis, yAxis, series,
      axisPointer: { link: [{ xAxisIndex: 'all' }] },
      tooltip: {
        trigger: 'axis', confine: true, renderMode: 'richText',
        axisPointer: { type: 'cross' },
        backgroundColor: isDark ? 'rgba(30,30,30,0.96)' : 'rgba(255,255,255,0.96)',
        borderColor: gridColor, textStyle: { color: textColor, fontSize: 11 },
        formatter: (params) => {
          const points = params.filter((point) => seriesById.has(point.seriesId))
            .sort((a, b) => a.seriesIndex - b.seriesIndex);
          const lines = points.flatMap((point) => {
            if (isCandlestick && point.seriesId === 'price') {
              const values = candles[point.dataIndex];
              if (!values?.every(Number.isFinite)) return [];
              const [open, close, low, high] = values;
              return [
                `开盘  ${open.toFixed(2)}`, `收盘  ${close.toFixed(2)}`,
                `最高  ${high.toFixed(2)}`, `最低  ${low.toFixed(2)}`,
              ];
            }
            return Number.isFinite(point.value)
              ? [`${point.marker || ''} ${seriesById.get(point.seriesId).name}  ${point.value.toFixed(2)}`]
              : [];
          });
          return lines.length ? [points[0].axisValue, ...lines].join('\n') : '';
        },
      },
      dataZoom: [
        {
          id: 'inside', type: 'inside', xAxisIndex: axisIndexes, ...zoom,
          zoomOnMouseWheel: 'ctrl', moveOnMouseWheel: false, preventDefaultMouseMove: false,
        },
        {
          id: 'slider', type: 'slider', xAxisIndex: axisIndexes, ...zoom,
          left: 56, right: 16, height: 20, bottom: 8,
          borderColor: gridColor, textStyle: { color: axisColor },
          fillerColor: isDark ? 'rgba(74,163,255,0.16)' : 'rgba(22,119,255,0.08)',
          handleStyle: { color: '#4aa3ff' },
          showDataShadow: false,
        },
      ],
    },
  };
}
