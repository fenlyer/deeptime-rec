import { useEffect, useState } from 'react'
import { Row, Col, Card, Tag, Typography, Spin, Empty, Tabs, Select } from 'antd'
import {
  FireOutlined, ClockCircleOutlined, ThunderboltOutlined,
  NodeIndexOutlined, TeamOutlined, FileTextOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { getRecommend, getProducts, RecommendItem, Product } from '../api'

const { Meta } = Card
const { Text, Title } = Typography

const channelIcons: Record<string, React.ReactNode> = {
  temporal_cf: <ClockCircleOutlined />,
  item_cf: <NodeIndexOutlined />,
  user_cf: <TeamOutlined />,
  hot: <FireOutlined />,
  content: <FileTextOutlined />,
}

const channelNames: Record<string, string> = {
  temporal_cf: '时序协同',
  item_cf: '物品协同',
  user_cf: '用户协同',
  hot: '热门召回',
  content: '内容相似',
}

const channelColors: Record<string, string> = {
  temporal_cf: '#2f54eb',
  item_cf: '#722ed1',
  user_cf: '#13c2c2',
  hot: '#fa541c',
  content: '#52c41a',
}

function ProductCard({ item, onClick }: { item: RecommendItem; onClick: () => void }) {
  return (
    <Card
      hoverable
      style={{ height: '100%', borderRadius: 12, overflow: 'hidden' }}
      cover={
        <div style={{ height: 180, overflow: 'hidden', background: '#f0f0f0', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <img alt={item.product.name} src={item.product.image} style={{ width: '100%', objectFit: 'cover' }} />
        </div>
      }
      onClick={onClick}
    >
      <Meta
        title={<Text ellipsis={{ tooltip: item.product.name }}>{item.product.name}</Text>}
        description={
          <div>
            <div style={{ marginBottom: 8 }}>
              <Text strong style={{ color: '#1677ff', fontSize: 16 }}>
                ¥{item.product.price.toLocaleString()}
              </Text>
              <Text type="secondary" style={{ marginLeft: 8 }}>{item.product.brand}</Text>
            </div>
            <Tag color={channelColors[item.channel] || '#888'} icon={channelIcons[item.channel]}>
              {channelNames[item.channel] || item.channel}
            </Tag>
            <div style={{ marginTop: 8, background: '#fff7e6', padding: '6px 10px', borderRadius: 6, border: '1px solid #ffe58f' }}>
              <Text type="secondary" style={{ fontSize: 12 }}>💡 {item.explanation}</Text>
            </div>
          </div>
        }
      />
    </Card>
  )
}

export default function Home({ userId }: { userId: string }) {
  const [recItems, setRecItems] = useState<RecommendItem[]>([])
  const [hotItems, setHotItems] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    setLoading(true)
    Promise.all([
      getRecommend({ user_id: userId, scene: 'home', size: 12 }),
      getProducts({ page: 1, size: 8 }),
    ]).then(([rec, hot]) => {
      setRecItems(rec.items)
      setHotItems(hot.items)
    }).finally(() => setLoading(false))
  }, [userId])

  if (loading) return <Spin size="large" style={{ display: 'block', margin: '120px auto' }} />

  return (
    <div>
      <Title level={3} style={{ marginBottom: 24 }}>
        <ThunderboltOutlined style={{ color: '#1677ff', marginRight: 8 }} />
        为你推荐
        <Text type="secondary" style={{ fontSize: 14, marginLeft: 12 }}>
          基于多路召回 · 深度排序 · 可解释推荐
        </Text>
      </Title>

      {recItems.length === 0 ? (
        <Empty description="暂无推荐数据" />
      ) : (
        <Row gutter={[16, 16]}>
          {recItems.map(item => (
            <Col key={item.product.id} xs={24} sm={12} md={8} lg={6}>
              <ProductCard item={item} onClick={() => navigate(`/product/${item.product.id}`)} />
            </Col>
          ))}
        </Row>
      )}

      <Title level={3} style={{ marginTop: 48, marginBottom: 24 }}>
        <FireOutlined style={{ color: '#fa541c', marginRight: 8 }} />
        热门商品
      </Title>
      <Row gutter={[16, 16]}>
        {hotItems.map(p => (
          <Col key={p.id} xs={24} sm={12} md={8} lg={6}>
            <Card
              hoverable
              style={{ borderRadius: 12 }}
              cover={
                <div style={{ height: 180, overflow: 'hidden', background: '#f0f0f0', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <img alt={p.name} src={p.image} style={{ width: '100%', objectFit: 'cover' }} />
                </div>
              }
              onClick={() => navigate(`/product/${p.id}`)}
            >
              <Meta
                title={<Text ellipsis={{ tooltip: p.name }}>{p.name}</Text>}
                description={
                  <div>
                    <Text strong style={{ color: '#1677ff' }}>¥{p.price.toLocaleString()}</Text>
                    <div style={{ marginTop: 4 }}>
                      {p.tags.slice(0, 2).map(t => <Tag key={t} color="orange">{t}</Tag>)}
                    </div>
                  </div>
                }
              />
            </Card>
          </Col>
        ))}
      </Row>
    </div>
  )
}
