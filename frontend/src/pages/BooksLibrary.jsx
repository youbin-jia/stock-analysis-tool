import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card, Row, Col, Tag, Input, Select, Rate, Empty, Spin, Typography, Space, Badge,
} from 'antd';
import { BookOutlined, SearchOutlined, UserOutlined } from '@ant-design/icons';
import axios from 'axios';

const { Title, Paragraph, Text } = Typography;
const { Search } = Input;

const SCHOOL_COLORS = {
  '价值投资': 'blue',
  '成长投资': 'green',
  '价值投资 / 风险管理': 'purple',
  '有效市场 / 被动投资': 'cyan',
  '被动投资': 'cyan',
  '技术分析 / 投机': 'orange',
  '行为金融': 'magenta',
};

export default function BooksLibrary() {
  const navigate = useNavigate();
  const [books, setBooks] = useState([]);
  const [schools, setSchools] = useState([]);
  const [tags, setTags] = useState([]);
  const [loading, setLoading] = useState(true);
  const [school, setSchool] = useState(null);
  const [tag, setTag] = useState(null);
  const [keyword, setKeyword] = useState('');

  const fetchBooks = async () => {
    setLoading(true);
    try {
      const params = {};
      if (school) params.school = school;
      if (tag) params.tag = tag;
      if (keyword) params.keyword = keyword;
      const { data } = await axios.get('/api/books/', { params });
      setBooks(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    axios.get('/api/books/schools').then(r => setSchools(r.data));
    axios.get('/api/books/tags').then(r => setTags(r.data));
  }, []);

  useEffect(() => { fetchBooks(); }, [school, tag, keyword]);

  return (
    <div>
      <div style={{ marginBottom: 20 }}>
        <Title level={3} style={{ color: 'var(--text-primary)', marginBottom: 4 }}>
          <BookOutlined /> 投资智慧库
        </Title>
        <Text type="secondary">
          经典投资著作的核心思想与可执行经验总结，为投资决策与代码分析提供方法论参考。
        </Text>
      </div>

      <Card style={{ marginBottom: 16, background: 'var(--bg-card)' }}>
        <Space wrap size="middle" style={{ width: '100%' }}>
          <Search
            placeholder="搜索书名 / 作者"
            allowClear
            onSearch={setKeyword}
            onChange={(e) => !e.target.value && setKeyword('')}
            style={{ width: 260 }}
            prefix={<SearchOutlined />}
          />
          <Select
            placeholder="按流派筛选"
            allowClear
            value={school}
            onChange={setSchool}
            style={{ width: 220 }}
            options={schools.map(s => ({ label: s, value: s }))}
          />
          <Select
            placeholder="按标签筛选"
            allowClear
            value={tag}
            onChange={setTag}
            style={{ width: 200 }}
            options={tags.map(t => ({ label: `${t.tag} (${t.count})`, value: t.tag }))}
          />
          <Text type="secondary">共 {books.length} 本</Text>
        </Space>
      </Card>

      <Spin spinning={loading}>
        {books.length === 0 ? (
          <Empty />
        ) : (
          <Row gutter={[16, 16]}>
            {books.map(b => (
              <Col key={b.id} xs={24} sm={12} lg={8} xxl={6}>
                <Card
                  hoverable
                  onClick={() => navigate(`/books/${b.id}`)}
                  style={{ height: '100%', background: 'var(--bg-card)' }}
                  styles={{ body: { display: 'flex', flexDirection: 'column', height: '100%' } }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                    <Title level={5} style={{ margin: 0, color: 'var(--text-primary)' }}>
                      {b.title}
                    </Title>
                    <Rate disabled defaultValue={b.rating} style={{ fontSize: 12 }} />
                  </div>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {b.title_en} · {b.year}
                  </Text>
                  <div style={{ margin: '8px 0' }}>
                    <Text style={{ color: 'var(--text-secondary)' }}>
                      <UserOutlined /> {b.author}
                    </Text>
                  </div>
                  <div style={{ marginBottom: 8 }}>
                    <Tag color={SCHOOL_COLORS[b.school] || 'default'}>{b.school}</Tag>
                  </div>
                  <Paragraph
                    style={{ color: 'var(--text-secondary)', fontSize: 13, flex: 1 }}
                    ellipsis={{ rows: 4 }}
                  >
                    {b.summary}
                  </Paragraph>
                  <div style={{ marginTop: 8, display: 'flex', gap: 12 }}>
                    <Badge count={b.principle_count} color="#1677ff" overflowCount={99}>
                      <Tag>核心经验</Tag>
                    </Badge>
                    <Badge count={b.quant_rule_count} color="#52c41a" overflowCount={99}>
                      <Tag>量化规则</Tag>
                    </Badge>
                  </div>
                  <div style={{ marginTop: 8 }}>
                    {b.tags.slice(0, 4).map(t => (
                      <Tag key={t} style={{ marginBottom: 4 }}>{t}</Tag>
                    ))}
                  </div>
                </Card>
              </Col>
            ))}
          </Row>
        )}
      </Spin>
    </div>
  );
}
