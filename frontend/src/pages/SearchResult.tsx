import { useEffect, useState } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { List, Card, Tag, Typography, Spin, Empty, Alert } from 'antd'
import { search as searchApi, Product } from '../api'

const { Text, Title } = Typography

export default function SearchResult({ userId }: { userId: string }) {
  const [params] = useSearchParams()
  const q = params.get('q') || ''
  const navigate = useNavigate()
  const [results, setResults] = useState<{ product: Product; score: number }[]>([])
  const [explanation, setExplanation] = useState('')
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!q) return
    setLoading(true)
    searchApi({ q, user_id: userId, size: 50 }).then(data => {
      setResults(data.items)
      setTotal(data.total)
      setExplanation(data.explanation)
    }).finally(() => setLoading(false))
  }, [q, userId])

  if (loading) return <Spin size="large" style={{ display: 'block', margin: '120px auto' }} />

  return (
    <div>
      <Title level={3}>
        搜索：<Text style={{ color: '#1677ff' }}>"{q}"</Text>
        <Text type="secondary" style={{ fontSize: 14, marginLeft: 12 }}>共 {total} 个结果</Text>
      </Title>

      {explanation && (
        <Alert
          message="搜索解释"
          description={explanation}
          type="info"
          showIcon
          style={{ marginBottom: 20, borderRadius: 8 }}
        />
      )}

      {results.length === 0 ? (
        <Empty description={`未找到与 "${q}" 相关的商品`} />
      ) : (
        <List
          dataSource={results}
          renderItem={({ product, score }) => (
            <Card
              hoverable
              style={{ marginBottom: 12, borderRadius: 12 }}
              onClick={() => navigate(`/product/${product.id}`)}
            >
              <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
                <div style={{ width: 120, height: 90, borderRadius: 8, overflow: 'hidden', background: '#f0f0f0', flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <img alt={product.name} src={product.image} style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'cover' }} />
                </div>
                <div style={{ flex: 1 }}>
                  <Text strong style={{ fontSize: 16 }}>{product.name}</Text>
                  <div style={{ marginTop: 4 }}>
                    <Text type="secondary">{product.brand} · {product.category}</Text>
                    <Tag style={{ marginLeft: 8 }} color="green">匹配度 {(score * 100).toFixed(0)}%</Tag>
                  </div>
                  <div style={{ marginTop: 4 }}>
                    <Text type="secondary" style={{ fontSize: 12 }}>{product.desc}</Text>
                  </div>
                </div>
                <Text strong style={{ color: '#1677ff', fontSize: 18, flexShrink: 0 }}>
                  ¥{product.price.toLocaleString()}
                </Text>
              </div>
            </Card>
          )}
        />
      )}
    </div>
  )
}
