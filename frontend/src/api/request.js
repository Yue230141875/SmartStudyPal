import axios from 'axios'

const request = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

request.interceptors.request.use(
  (config) => {
    console.log('Request:', config.method.toUpperCase(), config.url)
    return config
  },
  (error) => Promise.reject(error)
)

request.interceptors.response.use(
  (response) => {
    console.log('Response:', response.status, response.config.url)
    const data = response.data
    if (data.success === false) {
      console.error('API返回失败:', data.message)
      return Promise.reject(new Error(data.message || '请求失败'))
    }
    return data
  },
  (error) => {
    console.error('API请求错误:', error.message)
    if (error.response) {
      console.error('  状态码:', error.response.status)
      console.error('  响应:', error.response.data)
    }
    return Promise.reject(error)
  }
)

export default request
