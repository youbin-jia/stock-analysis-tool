import { Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { Layout, Menu, Breadcrumb, Button } from 'antd';
import {
  FundOutlined,
  BarChartOutlined,
  BankOutlined,
  SunOutlined,
  MoonOutlined,
  FallOutlined,
} from '@ant-design/icons';
import StockDetail from './pages/StockDetail';
import ComparisonPage from './pages/ComparisonPage';
import FundDetail from './pages/FundDetail';
import FundComparisonPage from './pages/FundComparisonPage';
import LowPositionFunds from './pages/LowPositionFunds';
import StockSearch from './components/StockSearch';
import FundSearch from './components/FundSearch';
import { useTheme } from './context/ThemeContext';

const { Header, Content, Sider } = Layout;

function App() {
  const location = useLocation();
  const navigate = useNavigate();
  const { isDark, toggleTheme } = useTheme();
  const pathSegments = location.pathname.split('/').filter(Boolean);

  const isFundRoute = pathSegments[0] === 'fund' || pathSegments[0] === 'fund-comparison' || pathSegments[0] === 'low-position-funds';

  const menuItems = [
    {
      key: 'detail',
      icon: <FundOutlined />,
      label: '股票详情',
      onClick: () => navigate('/detail/600519'),
    },
    {
      key: 'comparison',
      icon: <BarChartOutlined />,
      label: '股票对比',
      onClick: () => navigate('/comparison'),
    },
    {
      key: 'fund',
      icon: <BankOutlined />,
      label: '基金详情',
      onClick: () => navigate('/fund/000001'),
    },
    {
      key: 'fund-comparison',
      icon: <BarChartOutlined />,
      label: '基金对比',
      onClick: () => navigate('/fund-comparison'),
    },
    {
      key: 'low-position',
      icon: <FallOutlined />,
      label: '低位基金',
      onClick: () => navigate('/low-position-funds'),
    },
  ];

  const getSelectedKey = () => {
    if (pathSegments[0] === 'detail') return 'detail';
    if (pathSegments[0] === 'comparison') return 'comparison';
    if (pathSegments[0] === 'fund') return 'fund';
    if (pathSegments[0] === 'fund-comparison') return 'fund-comparison';
    if (pathSegments[0] === 'low-position-funds') return 'low-position';
    return 'detail';
  };

  const getBreadcrumbItems = () => {
    const items = [{ title: '首页' }];
    const key = getSelectedKey();
    if (key === 'detail') items.push({ title: '股票详情' });
    else if (key === 'comparison') items.push({ title: '股票对比' });
    else if (key === 'fund') items.push({ title: '基金详情' });
    else if (key === 'fund-comparison') items.push({ title: '基金对比' });
    else if (key === 'low-position') items.push({ title: '低位基金' });
    return items;
  };

  return (
    <Layout style={{ minHeight: '100vh', background: 'var(--bg-primary)' }}>
      <Header
        style={{
          position: 'fixed',
          top: 0,
          zIndex: 100,
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 32px',
          background: 'var(--bg-header)',
          boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
          borderBottom: '1px solid var(--border-color)',
          height: 56,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <FundOutlined style={{ fontSize: 22, color: 'var(--accent)' }} />
          <span
            style={{
              fontSize: 18,
              fontWeight: 600,
              color: 'var(--text-primary)',
              cursor: 'pointer',
            }}
            onClick={() => navigate('/')}
          >
            股票分析工具
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          {isFundRoute ? (
            <FundSearch
              onSearch={(code) => navigate(`/fund/${code}`)}
            />
          ) : (
            <StockSearch
              onSearch={(code) => navigate(`/detail/${code}`)}
            />
          )}
          <Button
            type="text"
            icon={isDark ? <SunOutlined /> : <MoonOutlined />}
            onClick={toggleTheme}
            style={{ color: 'var(--text-secondary)' }}
          />
        </div>
      </Header>

      <Layout style={{ marginTop: 56 }}>
        <Sider
          width={200}
          style={{
            background: 'var(--bg-sider)',
            position: 'fixed',
            height: 'calc(100vh - 56px)',
            left: 0,
            top: 56,
            borderRight: '1px solid var(--border-color)',
          }}
        >
          <Menu
            mode="inline"
            selectedKeys={[getSelectedKey()]}
            style={{ height: '100%', borderRight: 0, paddingTop: 8 }}
            items={menuItems}
          />
        </Sider>

        <Layout style={{ marginLeft: 200, padding: '20px 28px' }}>
          <Breadcrumb
            items={getBreadcrumbItems()}
            style={{ marginBottom: 16 }}
          />
          <Content>
            <Routes>
              <Route path="/" element={<Navigate to="/detail/600519" replace />} />
              <Route path="/detail/:code" element={<StockDetail />} />
              <Route path="/comparison" element={<ComparisonPage />} />
              <Route path="/fund/:code" element={<FundDetail />} />
              <Route path="/fund-comparison" element={<FundComparisonPage />} />
              <Route path="/low-position-funds" element={<LowPositionFunds />} />
            </Routes>
          </Content>
        </Layout>
      </Layout>
    </Layout>
  );
}

export default App;
