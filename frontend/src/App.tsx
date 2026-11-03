import { Routes, Route, Link, useNavigate } from 'react-router-dom'
import { Layout, Menu, Input, Avatar, Dropdown, Space, Typography } from 'antd'
import { SearchOutlined, HomeOutlined, UserOutlined, ShoppingOutlined } from '@ant-design/icons'
import { useState, useEffect } from 'react'
import Home from './pages/Home'
import ProductDetail from './pages/ProductDetail'
import SearchResult from './pages/SearchResult'
import UserProfile from './pages/UserProfile'
import { getUsers } from './api'

const { Header, Content } = Layout

function App() {
  const navigate = useNavigate()
  const [searchValue, setSearchValue] = useState('')
  const [users, setUsers] = useState<{ id: string; name: string; role: string; industry: string }[]>([])
  const [currentUser, setCurrentUser] = useState<{ id: string; name: string }>(() => {
    const saved = localStorage.getItem('currentUser')
    return saved ? JSON.parse(saved) : { id: 'U001', name: '张工' }
  })

  useEffect(() => {
    getUsers().then(setUsers).catch(() => {})
  }, [])

  const handleSearch = (value: string) => {
    if (value.trim()) {
      navigate(`/search?q=${encodeURIComponent(value.trim())}&user_id=${currentUser.id}`)
    }
  }

  const handleUserSwitch = (user: { id: string; name: string }) => {
    setCurrentUser(user)
    localStorage.setItem('currentUser', JSON.stringify(user))
    window.location.reload()
  }

  const userMenuItems = users.map(u => ({
    key: u.id,
    label: `${u.name} · ${u.role}`,
    onClick: () => handleUserSwitch(u),
  }))

  return (
    <Layout style={{ minHeight: '100vh', background: '#f5f5f5' }}>
      <Header style={{ display: 'flex', alignItems: 'center', background: '#001529', padding: '0 24px', gap: 24 }}>
        <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: 8, textDecoration: 'none' }}>
          <ShoppingOutlined style={{ fontSize: 24, color: '#1677ff' }} />
          <Typography.Text style={{ color: '#fff', fontSize: 18, fontWeight: 700, whiteSpace: 'nowrap' }}>
            工业资产商城
          </Typography.Text>
        </Link>

        <Menu
          theme="dark"
          mode="horizontal"
          style={{ flex: 1, minWidth: 0 }}
          items={[
            { key: 'home', icon: <HomeOutlined />, label: <Link to="/">首页推荐</Link> },
          ]}
        />

        <Input.Search
          placeholder="搜索工业设备..."
          value={searchValue}
          onChange={e => setSearchValue(e.target.value)}
          onSearch={handleSearch}
          style={{ maxWidth: 360 }}
          prefix={<SearchOutlined />}
        />

        <Dropdown menu={{ items: userMenuItems }} trigger={['click']}>
          <Space style={{ cursor: 'pointer', color: '#fff' }}>
            <Avatar size="small" icon={<UserOutlined />} style={{ background: '#1677ff' }} />
            <span>{currentUser.name}</span>
          </Space>
        </Dropdown>
      </Header>

      <Content style={{ padding: '24px 48px' }}>
        <Routes>
          <Route path="/" element={<Home userId={currentUser.id} />} />
          <Route path="/product/:id" element={<ProductDetail userId={currentUser.id} />} />
          <Route path="/search" element={<SearchResult userId={currentUser.id} />} />
          <Route path="/user/:id" element={<UserProfile />} />
        </Routes>
      </Content>
    </Layout>
  )
}

export default App
