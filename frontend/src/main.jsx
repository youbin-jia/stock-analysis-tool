import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { ThemeProvider, useTheme } from './context/ThemeContext';
import App from './App';
import './index.css';

function ThemedApp() {
  const { isDark } = useTheme();
  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        algorithm: isDark ? undefined : undefined,
        token: {
          colorBgBase: isDark ? '#141414' : '#ffffff',
          colorTextBase: isDark ? '#e8e8e8' : '#1f1f1f',
          colorBorder: isDark ? '#303030' : '#f0f0f0',
          colorBgContainer: isDark ? '#141414' : '#ffffff',
          colorBgElevated: isDark ? '#1f1f1f' : '#ffffff',
        },
      }}
    >
      <App />
    </ConfigProvider>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <ThemeProvider>
        <ThemedApp />
      </ThemeProvider>
    </BrowserRouter>
  </React.StrictMode>
);
