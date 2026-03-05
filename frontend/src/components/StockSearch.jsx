import { useState, useEffect } from 'react';
import { AutoComplete, Input, message } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

function StockSearch({ onSearch }) {
  const [options, setOptions] = useState([]);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSearch = async (value) => {
    if (!value || value.length < 1) {
      setOptions([]);
      return;
    }

    setLoading(true);
    try {
      const response = await axios.get('/api/stocks/search', {
        params: { keyword: value }
      });
      const data = response.data;
      setOptions(
        data.map((item) => ({
          value: item.code,
          label: `${item.code} - ${item.name}`,
        }))
      );
    } catch (error) {
      console.error('搜索失败:', error);
      message.error('搜索失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSelect = (value) => {
    if (onSearch) {
      onSearch(value);
    } else {
      navigate(`/detail/${value}`);
    }
  };

  const handlePressEnter = (e) => {
    const value = e.target.value;
    if (value) {
      handleSelect(value);
    }
  };

  return (
    <AutoComplete
      style={{ width: 300 }}
      options={options}
      onSearch={handleSearch}
      onSelect={handleSelect}
      placeholder="搜索股票代码或名称"
      loading={loading}
    >
      <Input
        suffix={<SearchOutlined style={{ color: 'rgba(0,0,0,.45)' }} />}
        onPressEnter={handlePressEnter}
      />
    </AutoComplete>
  );
}

export default StockSearch;
