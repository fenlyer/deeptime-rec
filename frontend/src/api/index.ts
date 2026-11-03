import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

export interface Product {
  id: string
  name: string
  category: string
  brand: string
  price: number
  image: string
  tags: string[]
  params: Record<string, string>
  stock: number
  desc: string
}

export interface RecommendItem {
  product: Product
  score: number
  channel: string
  explanation: string
}

export interface UserProfile {
  id: string
  name: string
  industry: string
  company: string
  company_scale: string
  role: string
  long_term_tags: string[]
  short_term_tags: string[]
  avatar: string
}

export interface Interaction {
  user_id: string
  product_id: string
  action: string
  timestamp: string
}

export const getProducts = (params: { page?: number; size?: number; category?: string; brand?: string; keyword?: string }) =>
  api.get('/products', { params }).then(r => r.data)

export const getProduct = (id: string) =>
  api.get(`/products/${id}`).then(r => r.data)

export const getRecommend = (params: { user_id: string; scene: string; size?: number }) =>
  api.get('/recommend', { params }).then(r => r.data)

export const search = (params: { q: string; user_id: string; page?: number; size?: number }) =>
  api.get('/search', { params }).then(r => r.data)

export const getUser = (id: string) =>
  api.get(`/users/${id}`).then(r => r.data)

export const getUsers = () =>
  api.get('/users').then(r => r.data)
