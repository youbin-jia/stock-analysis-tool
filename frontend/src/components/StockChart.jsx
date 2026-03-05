import { useEffect, useState } from 'react';
import ReactECharts from 'echarts-for-react';
import { Spin, Select, Card } from 'antd';

const { Option } = Select;

function StockChart({ stockCode, stockName }) {
  const [chartData, setChartData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState('1y');

  const periodOptions = [
    { value: '1m', label: '近1月' },
    { value: '3m', label: '近3月' },
    { value: '6m', label: '近6月' },
    { value: '1y', label: '近1年' },
    { value: 'all', label: '全部' },
  ];

  useEffect(() => {
    fetchChartData();
  }, [stockCode, period]);

  const fetchChartData = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`/api/stocks/history/${stockCode}`, {
        params: { period }
      });
      setChartData(response.data);
    } catch (error) {
      console.error('获取历史数据失败:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading || !chartData || chartData.length === 0) {
    return <Spin tip="加载中..." />;
  }

  // 准备数据
  const dates = chartData.map((item) => item.date);
  const openData = chartData.map((item) => item.open);
  const closeData = chartData.map((item) => item.close);
  const lowData = chartData.map((item) => item.low);
  const highData = chartData.map((item) => item.high);
  const volumeData = chartData.map((item) => item.volume);

  // 判断涨跌颜色
  const firstPrice = chartData[0].open;
  const lastPrice = chartData[chartData.length - 1].close;
  const isUp = lastPrice >= firstPrice;

  const option = {
    title: {
      text: stockName,
      left: 'center'
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      }
    },
    legend: {
      data: ['K线', '成交量'],
      top: 30
    },
    grid: [
      {
        left: '10%',
        right: '10%',
        top: 80,
        height: '50%'
      },
      {
        left: '10%',
        right: '10%',
        top: '65%',
        height: '15%'
      }
    ],
    xAxis: [
      {
        type: 'category',
        data: dates,
        scale: true,
        boundaryGap: false,
        axisLine: { onZero: false },
        splitLine: { show: false },
        min: 'dataMin',
        max: 'dataMax'
      },
      {
        type: 'category',
        gridIndex: 1,
        data: dates,
        scale: true,
        boundaryGap: false,
        axisLine: { onZero: false },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: { show: false },
        min: 'dataMin',
        max: 'dataMax'
      }
    ],
    yAxis: [
      {
        scale: true,
        splitArea: {
          show: true
        }
      },
      {
        scale: true,
        gridIndex: 1,
        splitNumber: 2,
        axisLabel: { show: false },
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: { show: false }
      }
    ],
    dataZoom: [
      {
        type: 'inside',
        xAxisIndex: [0, 1],
        start: 0,
        end: 100
      },
      {
        show: true,
        xAxisIndex: [0, 1],
        type: 'slider',
        top: '90%',
        start: 0,
        end: 100
      }
    ],
    series: [
      {
        name: 'K线',
        type: 'candlestick',
        data: chartData.map((item) => [
          item.open,
          item.close,
          item.low,
          item.high
        ]),
        itemStyle: {
          color: isUp ? '#ef232a' : '#14b143',
          color0: isUp ? '#14b143' : '#ef232a',
          borderColor: isUp ? '#ef232a' : '#14b143',
          borderColor0: isUp ? '#14b143' : '#ef232a'
        }
      },
      {
        name: '成交量',
        type: 'bar',
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: volumeData,
        itemStyle: {
          color: function (params) {
            const index = params.dataIndex;
            const open = openData[index];
            const close = closeData[index];
            return close >= open ? '#ef232a' : '#14b143';
          }
        }
      }
    ]
  };

  return (
    <Card>
      <div style={{ marginBottom: 16 }}>
        <Select
          value={period}
          onChange={setPeriod}
          style={{ width: 120 }}
        >
          {periodOptions.map((opt) => (
            <Option key={opt.value} value={opt.value}>
              {opt.label}
            </Option>
          ))}
        </Select>
      </div>
      <ReactECharts option={option} style={{ height: 500 }} />
    </Card>
  );
}

import axios from 'axios';

export default StockChart;
