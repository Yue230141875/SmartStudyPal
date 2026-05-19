import request from './request'

export function detectFocus(imageFile) {
  const formData = new FormData()
  formData.append('image', imageFile)
  return request.post('/vision/detect', formData, {
    headers: { 'Content-Type': undefined },
  })
}

export function getLatestSnapshot() {
  return request.get('/vision/snapshot')
}

export function getVisionConfig() {
  return request.get('/vision/config')
}

export function startDetection() {
  return request.post('/vision/start')
}

export function stopDetection() {
  return request.post('/vision/stop')
}

export function getFocusStatus() {
  return request.get('/vision/status')
}

export function createVisionWebSocket() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return new WebSocket(`${protocol}//localhost:8000/api/vision/stream`)
}
