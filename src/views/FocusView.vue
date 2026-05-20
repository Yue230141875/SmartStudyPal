<template>
  <div class="focus-view">
    <div class="focus-top">
      <div class="camera-container">
        <video ref="videoRef" autoplay playsinline class="camera-video" v-show="isDetecting"></video>
        <div class="camera-placeholder" v-show="!isDetecting">
          <el-icon :size="48"><VideoCamera /></el-icon>
          <p>点击"开始检测"启动摄像头</p>
        </div>
        <canvas ref="canvasRef" class="camera-canvas" v-show="false"></canvas>
      </div>
      <div class="camera-controls">
        <el-button type="primary" @click="startDetection" :disabled="isDetecting" size="small">
          <el-icon><VideoCamera /></el-icon> 开始
        </el-button>
        <el-button type="danger" @click="stopDetection" :disabled="!isDetecting" size="small">
          <el-icon><VideoPause /></el-icon> 停止
        </el-button>
        <el-tag :type="statusType" size="small" style="margin-left: 8px">{{ statusLabel }}</el-tag>
        <el-tag v-if="!visionAvailable" type="warning" size="small" style="margin-left: 4px">视觉模块受限</el-tag>
      </div>
    </div>
    <div class="focus-bottom">
      <div class="score-section">
        <el-progress
          type="dashboard"
          :percentage="focusScore"
          :color="scoreColor"
          :width="120"
          :stroke-width="10"
        >
          <template #default>
            <div class="score-inner">
              <span class="score-number">{{ focusScore }}</span>
              <span class="score-label">{{ focusLabel }}</span>
            </div>
          </template>
        </el-progress>
      </div>
      <div class="detail-section">
        <div class="detail-item">
          <span class="detail-label">眼部</span>
          <el-progress :percentage="eyeScore" :stroke-width="6" color="#409eff" />
        </div>
        <div class="detail-item">
          <span class="detail-label">头部</span>
          <el-progress :percentage="headScore" :stroke-width="6" color="#67c23a" />
        </div>
        <div class="detail-item">
          <span class="detail-label">身体</span>
          <el-progress :percentage="bodyScore" :stroke-width="6" color="#e6a23c" />
        </div>
        <div class="detail-item">
          <span class="detail-label">人脸</span>
          <el-tag size="small" :type="faceDetected ? 'success' : 'danger'">{{ faceDetected ? '已检测' : '未检测' }}</el-tag>
        </div>
        <div class="detail-item">
          <span class="detail-label">眨眼</span>
          <span class="detail-value">{{ blinkCount }}次</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onUnmounted } from 'vue'
import { VideoCamera, VideoPause } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { detectFocus } from '../api/vision'

const videoRef = ref(null)
const canvasRef = ref(null)
const isDetecting = ref(false)
const focusScore = ref(0)
const focusLabel = ref('未检测')
const eyeScore = ref(0)
const headScore = ref(0)
const bodyScore = ref(0)
const faceDetected = ref(false)
const blinkCount = ref(0)
const visionAvailable = ref(true)
const lastError = ref('')

let stream = null
let captureInterval = null
let errorCount = 0

const statusType = computed(() => {
  if (!isDetecting.value) return 'info'
  if (focusScore.value >= 75) return 'success'
  if (focusScore.value >= 50) return 'warning'
  return 'danger'
})

const statusLabel = computed(() => {
  if (!isDetecting.value) return '未启动'
  if (lastError.value) return '检测异常'
  return focusLabel.value
})

const scoreColor = computed(() => {
  if (focusScore.value >= 75) return '#67c23a'
  if (focusScore.value >= 50) return '#e6a23c'
  return '#f56c6c'
})

async function startDetection() {
  try {
    console.log('startDetection: trying to get user media...')
    stream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } })
    console.log('startDetection: got stream:', stream)
    if (videoRef.value) {
      videoRef.value.srcObject = stream
      console.log('startDetection: video element set')
    }
    isDetecting.value = true
    errorCount = 0
    lastError.value = ''
    ElMessage.success('摄像头已启动')
    console.log('startDetection: setting capture interval...')
    captureInterval = setInterval(captureAndDetect, 3000)
    console.log('startDetection: interval set, waiting 3 seconds for first capture')
  } catch (err) {
    console.error('startDetection error:', err)
    ElMessage.error('无法访问摄像头: ' + err.message)
  }
}

function stopDetection() {
  if (stream) {
    stream.getTracks().forEach(track => track.stop())
    stream = null
  }
  if (captureInterval) {
    clearInterval(captureInterval)
    captureInterval = null
  }
  isDetecting.value = false
  ElMessage.info('专注检测已停止')
}

async function captureAndDetect() {
  console.log('captureAndDetect: called, lastError:', lastError.value)
  if (!videoRef.value || !canvasRef.value) {
    console.log('captureAndDetect: videoRef or canvasRef is null')
    return
  }

  const video = videoRef.value
  if (video.videoWidth === 0 || video.videoHeight === 0) {
    console.log('captureAndDetect: video dimensions are 0')
    return
  }

  const canvas = canvasRef.value
  canvas.width = video.videoWidth
  canvas.height = video.videoHeight
  const ctx = canvas.getContext('2d')
  ctx.drawImage(video, 0, 0)

  canvas.toBlob(async (blob) => {
    if (!blob) {
      console.log('captureAndDetect: blob is null')
      return
    }
    try {
      console.log('captureAndDetect: sending request...')
      const file = new File([blob], 'frame.jpg', { type: 'image/jpeg' })
      console.log('captureAndDetect: file created, size:', file.size)
      const res = await detectFocus(file)
      console.log('captureAndDetect: response received:', res)
      console.log('captureAndDetect: data:', JSON.stringify(res.data, null, 2))
      console.log('captureAndDetect: checking success:', res.success, 'data:', res.data)
      if (res.success && res.data) {
        const d = res.data
        console.log('captureAndDetect: parsing data:', d)
        focusScore.value = Math.round(d.focus_score || 0)
        focusLabel.value = d.focus_level || '未知'
        eyeScore.value = Math.round(d.eye_score || 0)
        headScore.value = Math.round(d.head_score || 0)
        bodyScore.value = Math.round(d.body_score || 0)
        faceDetected.value = d.face_detected || false
        blinkCount.value = d.blink_count || 0
        visionAvailable.value = d.vision_available !== false
        lastError.value = ''
        errorCount = 0
        console.log('captureAndDetect: updated scores - focus:', focusScore.value, 'eye:', eyeScore.value, 'head:', headScore.value, 'body:', bodyScore.value)
      } else {
        errorCount++
        lastError.value = res.message || '检测失败'
        console.error('captureAndDetect: API返回失败 - success:', res.success, 'data:', res.data, 'message:', res.message)
        if (errorCount === 1) {
          console.warn('专注检测API返回失败:', res.message)
        }
      }
    } catch (e) {
      errorCount++
      lastError.value = e.message || '网络错误'
      if (errorCount <= 3) {
        console.warn('专注检测请求失败:', e.message)
      }
    }
  }, 'image/jpeg', 0.8)
}

onUnmounted(() => {
  stopDetection()
})
</script>

<style scoped>
.focus-view {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.focus-top {
  display: flex;
  flex-direction: column;
  align-items: center;
}
.camera-container {
  position: relative;
  width: 100%;
  min-height: 260px;
  background: #1a1a2e;
  border-radius: 10px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}
.camera-video {
  width: 100%;
  max-height: 300px;
  object-fit: contain;
}
.camera-placeholder {
  color: #909399;
  text-align: center;
}
.camera-placeholder p {
  margin-top: 8px;
  font-size: 13px;
}
.camera-canvas {
  display: none;
}
.camera-controls {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: center;
}
.focus-bottom {
  display: flex;
  gap: 20px;
  align-items: center;
}
.score-section {
  flex-shrink: 0;
}
.score-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
}
.score-number {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
}
.score-label {
  font-size: 12px;
  color: #909399;
}
.detail-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.detail-item {
  display: flex;
  align-items: center;
  gap: 8px;
}
.detail-label {
  min-width: 36px;
  font-size: 12px;
  color: #606266;
}
.detail-value {
  font-size: 12px;
  color: #303133;
}
.detail-item .el-progress {
  flex: 1;
}
</style>
