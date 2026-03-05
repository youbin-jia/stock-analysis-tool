import { useLocation } from 'react-router-dom';
import { useState, useEffect } from 'react';
import StockComparison from '../components/StockComparison';

function ComparisonPage() {
  const location = useLocation();
  const [initialCodes, setInitialCodes] = useState([]);

  useEffect(() => {
    if (location.state?.code) {
      setInitialCodes([location.state.code]);
    }
  }, [location.state]);

  return (
    <div>
      <h2>股票对比分析</h2>
      <StockComparison initialCodes={initialCodes} />
    </div>
  );
}

export default ComparisonPage;
