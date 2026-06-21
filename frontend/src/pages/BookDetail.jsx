import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card, Tag, Rate, Typography, Space, Spin, Button, Row, Col, Divider, Tabs, Empty,
} from 'antd';
import {
  ArrowLeftOutlined, BookOutlined, UserOutlined, CalendarOutlined,
  BulbOutlined, ThunderboltOutlined, FunctionOutlined, CheckCircleOutlined,
} from '@ant-design/icons';
import axios from 'axios';

const { Title, Paragraph, Text } = Typography;

export default function BookDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [book, setBook] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    axios.get(`/api/books/${id}`)
      .then(r => setBook(r.data))
      .catch(e => console.error(e))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <Spin />;
  if (!book) return <Empty description="未找到该书籍" />;

  const tabItems = [
    {
      key: 'principles',
      label: <span><BulbOutlined /> 核心经验 ({book.core_principles.length})</span>,
      children: (
        <Row gutter={[16, 16]}>
          {book.core_principles.map((p, i) => (
            <Col key={i} xs={24} lg={12}>
              <Card
                style={{ background: 'var(--bg-card)', height: '100%' }}
                title={
                  <Space>
                    <Text style={{ color: '#1677ff', fontWeight: 700 }}>#{i + 1}</Text>
                    <Text style={{ color: 'var(--text-primary)' }}>{p.title}</Text>
                  </Space>
                }
              >
                <Paragraph style={{ color: 'var(--text-secondary)' }}>
                  {p.content}
                </Paragraph>
                <Divider style={{ margin: '12px 0' }} />
                <div style={{
                  background: 'rgba(82, 196, 26, 0.08)',
                  borderLeft: '3px solid #52c41a',
                  padding: '8px 12px',
                  borderRadius: 4,
                }}>
                  <Text strong style={{ color: '#52c41a' }}>
                    <CheckCircleOutlined /> 可执行做法：
                  </Text>
                  <div style={{ color: 'var(--text-primary)', marginTop: 4 }}>
                    {p.actionable}
                  </div>
                </div>
              </Card>
            </Col>
          ))}
        </Row>
      ),
    },
    {
      key: 'quant',
      label: <span><FunctionOutlined /> 量化规则 ({book.quant_rules.length})</span>,
      children: (
        <Row gutter={[16, 16]}>
          {book.quant_rules.map((r, i) => (
            <Col key={i} xs={24} md={12}>
              <Card style={{ background: 'var(--bg-card)' }}>
                <Title level={5} style={{ color: 'var(--text-primary)', margin: 0 }}>
                  <ThunderboltOutlined style={{ color: '#faad14' }} /> {r.name}
                </Title>
                <div style={{
                  margin: '12px 0',
                  padding: '10px 14px',
                  background: 'rgba(22, 119, 255, 0.08)',
                  borderRadius: 6,
                  fontFamily: 'Menlo, Monaco, Consolas, monospace',
                  fontSize: 14,
                  color: 'var(--text-primary)',
                }}>
                  {r.formula}
                </div>
                <Text type="secondary">应用场景：{r.use_case}</Text>
              </Card>
            </Col>
          ))}
        </Row>
      ),
    },
  ];

  return (
    <div>
      <Button
        type="text"
        icon={<ArrowLeftOutlined />}
        onClick={() => navigate('/books')}
        style={{ marginBottom: 12, color: 'var(--text-secondary)' }}
      >
        返回书籍库
      </Button>

      <Card style={{ marginBottom: 16, background: 'var(--bg-card)' }}>
        <Row gutter={24} align="middle">
          <Col flex="auto">
            <Title level={3} style={{ marginBottom: 4, color: 'var(--text-primary)' }}>
              <BookOutlined /> {book.title}
            </Title>
            <Text type="secondary">{book.title_en}</Text>
            <div style={{ marginTop: 12 }}>
              <Space size="middle" wrap>
                <Text style={{ color: 'var(--text-secondary)' }}>
                  <UserOutlined /> {book.author}
                </Text>
                <Text style={{ color: 'var(--text-secondary)' }}>
                  <CalendarOutlined /> {book.year}
                </Text>
                <Tag color="blue">{book.school}</Tag>
                <Rate disabled defaultValue={book.rating} style={{ fontSize: 14 }} />
              </Space>
            </div>
            <div style={{ marginTop: 12 }}>
              {book.tags.map(t => <Tag key={t}>{t}</Tag>)}
            </div>
          </Col>
        </Row>
        <Divider style={{ margin: '16px 0' }} />
        <Paragraph style={{ color: 'var(--text-secondary)', fontSize: 14, marginBottom: 0 }}>
          {book.summary}
        </Paragraph>
      </Card>

      <Tabs items={tabItems} defaultActiveKey="principles" />
    </div>
  );
}
