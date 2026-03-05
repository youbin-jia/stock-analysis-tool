# 股票和基金分析工具

一个专业的A股股票分析和查看工具，支持实时数据获取、多股票对比、任意时段分析。

## 功能特性

- 📊 **实时行情**：获取A股实时行情数据，每30秒自动刷新
- 📈 **历史K线**：查看任意时间段的历史K线图，支持缩放和拖拽
- 🔍 **股票搜索**：支持按代码和名称搜索股票
- 📊 **多股对比**：对比多只股票的价格走势和收益率
- 💾 **数据持久化**：SQLite存储历史数据，避免重复API调用
- ⚡ **Redis缓存**：实时数据缓存30秒，大幅降低API调用频率

## 技术栈

### 后端
- FastAPI - Web框架
- akshare - A股数据源
- SQLAlchemy - ORM框架
- SQLite - 历史数据存储
- Redis - 实时数据缓存
- APScheduler - 定时任务

### 前端
- React 18 - UI框架
- Vite - 构建工具
- Ant Design - UI组件库
- ECharts - 图表库
- Axios - HTTP客户端

## 快速开始

### 1. 克隆项目

```bash
cd /Users/youbin.jia/Code/stock-analysis-tool
```

### 2. 启动 Redis

```bash
redis-server
```

或者使用 Docker:

```bash
docker run -d -p 6379:6379 redis:7-alpine
```

### 3. 启动后端

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```

### 4. 启动前端

```bash
cd frontend
npm install
npm run dev
```

### 5. 访问应用

打开浏览器访问 http://localhost:5173

## API文档

启动后端后，访问 http://localhost:8000/docs 查看完整的API文档。

### 主要API接口

- `GET /api/stocks/realtime/{code}` - 获取实时行情
- `GET /api/stocks/history/{code}` - 获取历史K线数据
- `GET /api/stocks/info/{code}` - 获取股票信息
- `GET /api/stocks/list` - 获取股票列表
- `GET /api/stocks/search?keyword=xxx` - 搜索股票
- `GET /api/comparison?codes=xxx,yyy` - 多股票对比

## 数据持久化策略

### Redis 缓存
- 实时行情缓存：30秒过期
- 历史数据缓存：1小时过期

### SQLite 存储
- 历史K线数据永久存储
- 按交易日增量更新
- 自动创建索引优化查询

### 定时任务
- 实时数据：每30秒更新（交易时间）
- 历史数据：每日15:30更新

## Docker 部署

```bash
docker-compose up -d
```

访问 http://localhost

## 项目结构

```
stock-analysis-tool/
├── backend/                 # 后端服务
│   ├── api/                # API 路由
│   ├── services/           # 业务逻辑
│   ├── models/             # 数据模型
│   ├── tasks/              # 定时任务
│   ├── data/               # 数据存储
│   └── main.py             # 应用入口
├── frontend/               # 前端应用
│   ├── src/
│   │   ├── components/     # 组件
│   │   ├── pages/         # 页面
│   │   └── main.jsx       # 入口
│   └── package.json
└── docker-compose.yml
```

## 注意事项

- akshare 是免费数据源，无需API key
- 实时数据有一定延迟（通常几秒到几分钟）
- 首次运行时会自动初始化数据库
- 建议配置环境变量 `REDIS_URL` 指定Redis地址

## License

MIT
