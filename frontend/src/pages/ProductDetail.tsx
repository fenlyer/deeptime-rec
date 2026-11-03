import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Row, Col, Card, Tag, Typography, Descriptions, Spin, Breadcrumb, Button, Divider,
} from 'antd'
import {
  ShoppingCartOutlined, StarOutlined, QuestionCircleOutlined,
} from '@ant-design/icons'
import { getProduct, getRecommend, Product, RecommendItem } from '../api'

const { Title, Text } = Typography

const channelColors: Record<string, string> = {
  temporal_cf: '#2f54eb', item_cf: '#722ed1', user_cf: '#13c2c2', hot: '#fa541c', content: '#52c41a',
}

const channelNames: Record<string, string> = {
  temporal_cf: '时序协同', item_cf: '物品协同', user_cf: '用户协同', hot: '热门', content: '内容相似',
}

export default function ProductDetail({ userId }: { userId: string }) {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [product, setProduct] = useState<Product | null>(null)
  const [similarItems, setSimilarItems] = useState<RecommendItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!id) return
    setLoading(true)
    Promise.all([
      getProduct(id),
      getRecommend({ user_id: userId, scene: `detail_${id}`, size: 6 }),
    ]).then(([prod, rec]) => {
      setProduct(prod)
      setSimilarItems(rec.items.length > 0 ? rec.items : [])
    }).finally(() => setLoading(false))
  }, [id, userId])

  if (loading) return <Spin size="large" style={{ display: 'block', margin: '120px auto' }} />
  if (!product) return <div>商品不存在</div>

  return (
    <div>
      <Breadcrumb style={{ marginBottom: 16 }} items={[
        { title: <a onClick={() => navigate('/')}>首页</a> },
        { title: product.category },
        { title: product.name },
      ]} />

      <Card style={{ borderRadius: 12, marginBottom: 24 }}>
        <Row gutter={[32, 24]}>
          <Col xs={24} md={10}>
            <div style={{ background: '#f5f5f5', borderRadius: 12, overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center', height: 360 }}>
              <img alt={product.name} src={product.image} style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }} />
            </div>
          </Col>
          <Col xs={24} md={14}>
            <Title level={3}>{product.name}</Title>
            <div style={{ marginBottom: 16 }}>
              {product.tags.map(t => <Tag key={t} color="blue">{t}</Tag>)}
            </div>

            <div style={{ background: '#fff7e6', padding: '16px 20px', borderRadius: 8, marginBottom: 20 }}>
              <Text style={{ fontSize: 28, fontWeight: 700, color: '#cf1322' }}>
                ¥{product.price.toLocaleString()}
              </Text>
              <Text type="secondary" style={{ marginLeft: 12 }}>含税价</Text>
            </div>

            <Descriptions column={2} size="small" bordered style={{ marginBottom: 20 }}>
              <Descriptions.Item label="品牌">{product.brand}</Descriptions.Item>
              <Descriptions.Item label="类目">{product.category}</Descriptions.Item>
              <Descriptions.Item label="库存">{product.stock} 件</Descriptions.Item>
              {Object.entries(product.params).slice(0, 4).map(([k, v]) => (
                <Descriptions.Item key={k} label={k}>{v}</Descriptions.Item>
              ))}
            </Descriptions>

            <Text type="secondary">{product.desc}</Text>

            <div style={{ marginTop: 20, display: 'flex', gap: 12 }}>
              <Button type="primary" size="large" icon={<ShoppingCartOutlined />}>
                立即询价
              </Button>
              <Button size="large" icon={<StarOutlined />}>收藏</Button>
            </div>
          </Col>
        </Row>
      </Card>

      {/* recommendation explanation section */}
      {similarItems.length > 0 && (
        <Card
          title={<span><QuestionCircleOutlined style={{ marginRight: 8 }} />为什么推荐这些商品？</span>}
          style={{ borderRadius: 12, marginBottom: 24 }}
        >
          {similarItems.map((item, idx) => (
            <div key={idx} style={{
              padding: '12px 16px', marginBottom: 8, background: '#f6ffed',
              borderRadius: 8, border: '1px solid #b7eb8f',
            }}>
              <Text strong style={{ color: '#389e0d' }}>#{idx + 1}</Text>
              <Text style={{ marginLeft: 12 }}>{item.explanation}</Text>
              <Tag color={channelColors[item.channel] || '#888'} style={{ marginLeft: 8 }}>
                {channelNames[item.channel] || item.channel}
              </Tag>
              <Text type="secondary" style={{ marginLeft: 8 }}>置信度: {(item.score * 100).toFixed(0)}%</Text>
            </div>
          ))}
        </Card>
      )}

      {/* similar products */}
      {similarItems.length > 0 && (
        <>
          <Divider orientation="left">看了又看</Divider>
          <Row gutter={[16, 16]}>
            {similarItems.map(item => (
              <Col key={item.product.id} xs={24} sm={12} md={8} lg={6}>
                <Card
                  hoverable
                  style={{ borderRadius: 12 }}
                  cover={
                    <div style={{ height: 160, overflow: 'hidden', background: '#f0f0f0', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <img alt={item.product.name} src={item.product.image} style={{ width: '100%', objectFit: 'cover' }} />
                    </div>
                  }
                  onClick={() => navigate(`/product/${item.product.id}`)}
                >
                  <Card.Meta
                    title={<Text ellipsis={{ tooltip: item.product.name }} style={{ fontSize: 13 }}>{item.product.name}</Text>}
                    description={
                      <div>
                        <Text strong style={{ color: '#1677ff' }}>¥{item.product.price.toLocaleString()}</Text>
                        <div style={{ marginTop: 4, background: '#f0f5ff', padding: '4px 8px', borderRadius: 4 }}>
                          <Text type="secondary" style={{ fontSize: 11 }}>💡 {item.explanation.slice(0, 24)}...</Text>
                        </div>
                      </div>
                    }
                  />
                </Card>
              </Col>
            ))}
          </Row>
        </>
      )}
    </div>
  )
}
