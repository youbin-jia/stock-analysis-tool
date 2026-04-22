import { useLocation } from 'react-router-dom';
import { useState, useEffect } from 'react';
import FundComparison from '../components/FundComparison';

function FundComparisonPage() {
  const location = useLocation();
  const [initialCodes, setInitialCodes] = useState([]);

  useEffect(() => {
    if (location.state?.code) {
      setInitialCodes([location.state.code]);
    }
  }, [location.state]);

  return (
    <div>
      <FundComparison initialCodes={initialCodes} />
    </div>
  );
}

export default FundComparisonPage;
