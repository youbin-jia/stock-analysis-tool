import { Routes, Route, Navigate } from 'react-router-dom';
import { Layout, Menu, Typography } from 'antd';
import { HomeOutlined, BarChartOutlined, SearchOutlined } from '@ant-design/icons';
import { useState } from 'react';
import StockDetail from './pages/StockDetail';
import ComparisonPage from './pages/ComparisonPage';
import StockSearch from './components/StockSearch';

const { Header, Content, Sider } = Layout;
const { Title } = Typography;

function App() {
  const [currentPage, setCurrentPage] = useState('detail');

  const menuItems = [
    {
      key: 'detail',
      icon: <HomeOutlined />,
      label: '股票详情',
    },
    {
      key: 'comparison',
      icon: <BarChartOutlined />,
      label: '对比分析',
    },
  ];

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ background: '#1890ff', padding: '0 24px', display: 'flex', alignItems: 'center' }}>
        <Title level={3} style={{ color: 'white', margin: 0 }}>
          股票分析工具
        </Title>
        <div style={{ marginLeft: 'auto' }}>
          <StockSearch onSearch={(code) => setCurrentPage(`detail/${code}`)} />
        </div>
      </Header>
      <Layout>
        <Sider width={200} style={{ background: '#fff' }}>
          <Menu
            mode="inline"
            selectedKeys={[currentPage.split('/')[0]]}
            style={{ height: '100%', borderRight: 0 }}
            items={menuItems}
            onClick={({ key }) => setCurrentPage(key)}
          />
        </Sider>
        <Layout style={{ padding: '24px' }}>
          <Content
            style={{
              background: '#fff',
              padding: 24,
              margin: 0,
              minHeight: 280,
              borderRadius: 8,
            }}
          >
            <Routes>
              <Route path="/" element={<Navigate to="/detail/600519" replace />} />
              <Route path="/detail/:code" element={<StockDetail />} />
              <Route path="/comparison" element={<ComparisonPage />} />
            </Routes>
          </Content>
        </Layout>
      </Layout>
    </Layout>
  );
}

export default App;
