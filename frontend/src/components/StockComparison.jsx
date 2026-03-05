import { useState, useEffect } from 'react';
import ReactECharts from 'echarts-for-react';
import { Spin, Select, Card, Space, Button, message } from 'antd';
import { PlusOutlined, CloseOutlined } from '@ant-design/icons';

const { Option } = Select;

function StockComparison({ initialCodes = [] }) {
  const [selectedStocks, setSelectedStocks] = useState([]);
  const [chartData, setChartData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [period, setPeriod] = useState('1y');
  const [normalize, setNormalize] = useState(true);

  const periodOptions = [
    { value: '1m', label: '近1月' },
    { value: '3m', label: '近3月' },
    { value: '6m', label: '近6月' },
    { value: '1y', label: '近1年' },
    { value: 'all', label: '全部' },
  ];

  const colors = ['#1890ff', '#52c41a', '#faad14', '#f5222d', '#722ed1', '#eb2f96', '#fa8c16', '#13c2c2'];

  useEffect(() => {
    if (initialCodes.length > 0) {
      const initStocks = initialCodes.map((code) => ({ code, name: code }));
      setSelectedStocks(initStocks);
      fetchComparisonData();
    }
  }, []);

  useEffect(() => {
    if (selectedStocks.length > 0) {
      fetchComparisonData();
    }
  }, [period, normalize, selectedStocks]);

  const fetchComparisonData = async () => {
    if (selectedStocks.length === 0) return;

    setLoading(true);
    try {
      const codes = selectedStocks.map((s) => s.code).join(',');
      const response = await axios.get('/api/comparison', {
        params: {
          codes,
          period,
          normalize
        }
      });
      setChartData(response.data);
    } catch (error) {
      console.error('获取对比数据失败:', error);
      message.error('获取对比数据失败');
    } finally {
      setLoading(false);
    }
  };

  const handleAddStock = async (code) => {
    if (!code || selectedStocks.some((s) => s.code === code)) return;

    try {
      const response = await axios.get(`/api/stocks/info/${code}`);
      const stockInfo = response.data;
      setSelectedStocks([...selectedStocks, stockInfo]);
    } catch (error) {
      message.error('获取股票信息失败');
    }
  };

  const handleRemoveStock = (code) => {
    setSelectedStocks(selectedStocks.filter((s) => s.code !== code));
  };

  if (loading) {
    return <Spin tip="加载中..." />;
  }

  if (!chartData || chartData.stocks.length === 0) {
    return (
      <Card>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Select
            showSearch
            style={{ width: 300 }}
            placeholder="选择要对比的股票"
            optionFilterProp="label"
            filterOption={(input, option) =>
              option.label.toLowerCase().indexOf(input.toLowerCase()) >= 0
            }
            onSelect={handleAddStock}
          >
            <Option value="600519">600519 - 贵州茅台</Option>
            <Option value="000858">000858 - 五粮液</Option>
            <Option value="601318">601318 - 中国平安</Option>
            <Option value="000333">000333 - 美的集团</Option>
            <Option value="601888">601888 - 中国中免</Option>
            <Option value="600036">600036 - 招商银行</Option>
          </Select>
        </Space>
      </Card>
    );
  }

  // 准备图表数据
  const dates = chartData.stocks[0]?.data.map((item) => item.date) || [];
  const series = chartData.stocks.map((stock, index) => ({
    name: stock.name,
    type: 'line',
    data: stock.data.map((item) => item.value),
    smooth: true,
    symbol: 'none',
    lineStyle: {
      width: 2,
      color: colors[index % colors.length]
    },
    itemStyle: {
      color: colors[index % colors.length]
    }
  }));

  const option = {
    title: {
      text: normalize ? '股票收益率对比' : '股票价格对比',
      left: 'center'
    },
    tooltip: {
      trigger: 'axis',
      formatter: function (params) {
        let result = params[0].axisValue + '<br/>';
        params.forEach((param) => {
          const value = param.value.toFixed(2);
          const unit = normalize ? '%' : '元';
          result += `${param.marker} ${param.seriesName}: ${value}${unit}<br/>`;
        });
        return result;
      }
    },
    legend: {
      data: chartData.stocks.map((s) => s.name),
      top: 30
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: 80,
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: dates
    },
    yAxis: {
      type: 'value',
      name: normalize ? '收益率 (%)' : '价格 (元)',
      axisLabel: {
        formatter: function (value) {
          return normalize ? value.toFixed(2) + '%' : value.toFixed(2);
        }
      }
    },
    dataZoom: [
      {
        type: 'inside',
        start: 0,
        end: 100
      },
      {
        type: 'slider',
        bottom: 10,
        start: 0,
        end: 100
      }
    ],
    series
  };

  return (
    <Card>
      <Space direction="vertical" style={{ width: '100%' }}>
        <Space>
          <Select
            showSearch
            style={{ width: 300 }}
            placeholder="添加股票进行对比"
            optionFilterProp="label"
            filterOption={(input, option) =>
              option.label.toLowerCase().indexOf(input.toLowerCase()) >= 0
            }
            onSelect={handleAddStock}
          >
            <Option value="600519">600519 - 贵州茅台</Option>
            <Option value="000858">000858 - 五粮液</Option>
            <Option value="601318">601318 - 中国平安</Option>
            <Option value="000333">000333 - 美的集团</Option>
            <Option value="601888">601888 - 中国中免</Option>
            <Option value="600036">600036 - 招商银行</Option>
          </Select>
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
          <Select
            value={normalize}
            onChange={setNormalize}
            style={{ width: 120 }}
          >
            <Option value={true}>收益率</Option>
            <Option value={false}>原始价格</Option>
          </Select>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => fetchComparisonData()}
          >
            刷新数据
          </Button>
        </Space>
        <div>
          {selectedStocks.map((stock) => (
            <span key={stock.code} style={{ marginRight: 16 }}>
              {stock.name} ({stock.code})
              <Button
                type="link"
                danger
                size="small"
                icon={<CloseOutlined />}
                onClick={() => handleRemoveStock(stock.code)}
              >
                移除
              </Button>
            </span>
          ))}
        </div>
        <ReactECharts option={option} style={{ height: 500 }} />
      </Space>
    </Card>
  );
}

import axios from 'axios';

export default StockComparison;
