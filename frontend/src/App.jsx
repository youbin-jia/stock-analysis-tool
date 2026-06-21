import { Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { Layout, Menu, Breadcrumb, Button } from 'antd';
import {
  FundOutlined,
  BarChartOutlined,
  BankOutlined,
  SunOutlined,
  MoonOutlined,
  FallOutlined,
  FireOutlined,
  ExperimentOutlined,
  TrophyOutlined,
  GlobalOutlined,
  ReadOutlined,
} from '@ant-design/icons';
import StockDetail from './pages/StockDetail';
import ComparisonPage from './pages/ComparisonPage';
import FundDetail from './pages/FundDetail';
import FundComparisonPage from './pages/FundComparisonPage';
import LowPositionFunds from './pages/LowPositionFunds';
import HotSectors from './pages/HotSectors';
import QuantAnalysis from './pages/QuantAnalysis';
import StyleInsight from './pages/StyleInsight';
import StyleTops from './pages/StyleTops';
import PolicyInsight from './pages/PolicyInsight';
import BooksLibrary from './pages/BooksLibrary';
import BookDetail from './pages/BookDetail';
import StockSearch from './components/StockSearch';
import FundSearch from './components/FundSearch';
import { useTheme } from './context/ThemeContext';

const { Header, Content, Sider } = Layout;

function App() {
  const location = useLocation();
  const navigate = useNavigate();
  const { isDark, toggleTheme } = useTheme();
  const pathSegments = location.pathname.split('/').filter(Boolean);

  const isFundRoute = pathSegments[0] === 'fund' || pathSegments[0] === 'fund-comparison' || pathSegments[0] === 'low-position-funds' || pathSegments[0] === 'hot-sectors' || pathSegments[0] === 'quant-analysis' || pathSegments[0] === 'style-insight' || pathSegments[0] === 'style-tops' || pathSegments[0] === 'policy' || pathSegments[0] === 'books';

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
      key: 'hot-sectors',
      icon: <FireOutlined />,
      label: '热门板块',
      onClick: () => navigate('/hot-sectors'),
    },
    {
      key: 'quant-analysis',
      icon: <ExperimentOutlined />,
      label: '量化分析',
      onClick: () => navigate('/quant-analysis'),
    },
    {
      key: 'style-insight',
      icon: <TrophyOutlined />,
      label: '流派洞察',
      onClick: () => navigate('/style-insight'),
    },
    {
      key: 'style-tops',
      icon: <TrophyOutlined />,
      label: '流派Top榜',
      onClick: () => navigate('/style-tops'),
    },
    {
      key: 'policy',
      icon: <GlobalOutlined />,
      label: '政策风向',
      onClick: () => navigate('/policy'),
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
    {
      key: 'books',
      icon: <ReadOutlined />,
      label: '投资智慧',
      onClick: () => navigate('/books'),
    },
  ];

  const getSelectedKey = () => {
    if (pathSegments[0] === 'detail') return 'detail';
    if (pathSegments[0] === 'comparison') return 'comparison';
    if (pathSegments[0] === 'hot-sectors') return 'hot-sectors';
    if (pathSegments[0] === 'quant-analysis') return 'quant-analysis';
    if (pathSegments[0] === 'style-insight') return 'style-insight';
    if (pathSegments[0] === 'style-tops') return 'style-tops';
    if (pathSegments[0] === 'policy') return 'policy';
    if (pathSegments[0] === 'fund') return 'fund';
    if (pathSegments[0] === 'fund-comparison') return 'fund-comparison';
    if (pathSegments[0] === 'low-position-funds') return 'low-position';
    if (pathSegments[0] === 'books') return 'books';
    return 'detail';
  };

  const getBreadcrumbItems = () => {
    const items = [{ title: '首页' }];
    const key = getSelectedKey();
    if (key === 'detail') items.push({ title: '股票详情' });
    else if (key === 'comparison') items.push({ title: '股票对比' });
    else if (key === 'hot-sectors') items.push({ title: '热门板块' });
    else if (key === 'quant-analysis') items.push({ title: '量化分析' });
    else if (key === 'style-insight') items.push({ title: '流派洞察' });
    else if (key === 'style-tops') items.push({ title: '流派Top榜' });
    else if (key === 'policy') items.push({ title: '政策风向' });
    else if (key === 'fund') items.push({ title: '基金详情' });
    else if (key === 'fund-comparison') items.push({ title: '基金对比' });
    else if (key === 'low-position') items.push({ title: '低位基金' });
    else if (key === 'books') items.push({ title: '投资智慧' });
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
              <Route path="/hot-sectors" element={<HotSectors />} />
              <Route path="/quant-analysis" element={<QuantAnalysis />} />
              <Route path="/style-insight" element={<StyleInsight />} />
              <Route path="/style-tops" element={<StyleTops />} />
              <Route path="/policy" element={<PolicyInsight />} />
              <Route path="/fund/:code" element={<FundDetail />} />
              <Route path="/fund-comparison" element={<FundComparisonPage />} />
              <Route path="/low-position-funds" element={<LowPositionFunds />} />
              <Route path="/books" element={<BooksLibrary />} />
              <Route path="/books/:id" element={<BookDetail />} />
            </Routes>
          </Content>
        </Layout>
      </Layout>
    </Layout>
  );
}

export default App;
