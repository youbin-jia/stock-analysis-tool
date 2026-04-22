import { useState, useEffect, useCallback } from 'react';
import { AutoComplete, Input } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

function FundSearch({ onSearch, style = {} }) {
  const [allFunds, setAllFunds] = useState([]);
  const [options, setOptions] = useState([]);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    axios.get('/api/funds/list')
      .then((res) => {
        setAllFunds(res.data || []);
      })
      .catch(() => {
        setAllFunds([]);
      });
  }, []);

  const filterFunds = useCallback((value) => {
    if (!value || value.length === 0) {
      return [];
    }
    const lower = value.toLowerCase();
    return allFunds
      .filter(
        (item) =>
          item.code.includes(lower) ||
          item.name.toLowerCase().includes(lower)
      )
      .slice(0, 20);
  }, [allFunds]);

  const handleSearch = (value) => {
    const filtered = filterFunds(value);
    setOptions(
      filtered.map((item) => ({
        value: item.code,
        label: (
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ fontWeight: 500 }}>{item.name}</span>
            <span style={{ color: '#888', fontSize: 12 }}>{item.code}</span>
          </div>
        ),
      }))
    );
  };

  const handleSelect = (value) => {
    if (onSearch) {
      onSearch(value);
    } else {
      navigate(`/fund/${value}`);
    }
    setOptions([]);
  };

  const handlePressEnter = (e) => {
    const value = e.target.value;
    if (value) {
      handleSelect(value);
    }
  };

  return (
    <AutoComplete
      style={{ width: 280, ...style }}
      options={options}
      onSearch={handleSearch}
      onSelect={handleSelect}
      placeholder="搜索基金代码或名称"
      loading={loading}
    >
      <Input
        prefix={<SearchOutlined style={{ color: '#bfbfbf' }} />}
        onPressEnter={handlePressEnter}
        style={{ borderRadius: 20, background: 'var(--bg-input)', border: 'none' }}
      />
    </AutoComplete>
  );
}

export default FundSearch;
