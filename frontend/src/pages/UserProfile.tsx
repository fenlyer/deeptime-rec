import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, Tag, Typography, Timeline, Descriptions, Spin, Avatar, Row, Col } from 'antd'
import { ClockCircleOutlined, EyeOutlined, StarOutlined, ShoppingCartOutlined, MessageOutlined, TagOutlined } from '@ant-design/icons'
import { getUser, UserProfile as UserType, Interaction } from '../api'

const { Title, Text } = Typography

const actionConfig: Record<string, { color: string; icon: React.ReactNode; label: string }> = {
  view: { color: 'blue', icon: <EyeOutlined />, label: '浏览' },
  inquiry: { color: 'orange', icon: <MessageOutlined />, label: '询价' },
  favorite: { color: 'gold', icon: <StarOutlined />, label: '收藏' },
  purchase: { color: 'green', icon: <ShoppingCartOutlined />, label: '采购' },
}

export default function UserProfile() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [user, setUser] = useState<UserType | null>(null)
  const [history, setHistory] = useState<Interaction[]>([])
  const [longTags, setLongTags] = useState<string[]>([])
  const [shortTags, setShortTags] = useState<string[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!id) return
    setLoading(true)
    getUser(id).then(data => {
      setUser(data.user)
      setHistory(data.history)
      setLongTags(data.long_term_tags)
      setShortTags(data.short_term_tags)
    }).finally(() => setLoading(false))
  }, [id])

  if (loading) return <Spin size="large" style={{ display: 'block', margin: '120px auto' }} />
  if (!user) return <div>用户不存在</div>

  return (
    <div>
      <Card style={{ borderRadius: 12, marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
          <Avatar size={80} src={user.avatar} style={{ background: '#1677ff' }}>
            {user.name[0]}
          </Avatar>
          <div>
            <Title level={3} style={{ margin: 0 }}>{user.name}</Title>
            <Text type="secondary">{user.role} · {user.company}</Text>
          </div>
        </div>

        <Descriptions style={{ marginTop: 20 }} column={3} size="small">
          <Descriptions.Item label="行业">{user.industry}</Descriptions.Item>
          <Descriptions.Item label="公司规模">{user.company_scale}</Descriptions.Item>
          <Descriptions.Item label="角色">{user.role}</Descriptions.Item>
        </Descriptions>
      </Card>

      <Row gutter={[24, 24]}>
        <Col xs={24} md={14}>
          <Card title={<span><ClockCircleOutlined style={{ marginRight: 8 }} />行为时间线</span>} style={{ borderRadius: 12 }}>
            <Timeline
              items={history.map(h => {
                const cfg = actionConfig[h.action] || { color: 'gray', icon: null, label: h.action }
                return {
                  color: cfg.color,
                  dot: cfg.icon,
                  children: (
                    <div>
                      <Tag color={cfg.color}>{cfg.label}</Tag>
                      <Text
                        style={{ cursor: 'pointer', color: '#1677ff' }}
                        onClick={() => navigate(`/product/${h.product_id}`)}
                      >
                        商品 {h.product_id}
                      </Text>
                      <div><Text type="secondary" style={{ fontSize: 12 }}>{new Date(h.timestamp).toLocaleString('zh-CN')}</Text></div>
                    </div>
                  ),
                }
              })}
            />
          </Card>
        </Col>

        <Col xs={24} md={10}>
          <Card title={<span><TagOutlined style={{ marginRight: 8 }} />长期兴趣标签</span>} style={{ borderRadius: 12, marginBottom: 16 }}>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {longTags.map(t => <Tag key={t} color="blue" style={{ fontSize: 14, padding: '4px 12px' }}>{t}</Tag>)}
            </div>
          </Card>

          <Card title={<span><TagOutlined style={{ marginRight: 8, color: '#fa541c' }} />短期活跃品类</span>} style={{ borderRadius: 12 }}>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {shortTags.map(t => <Tag key={t} color="orange" style={{ fontSize: 14, padding: '4px 12px' }}>{t}</Tag>)}
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  )
}
