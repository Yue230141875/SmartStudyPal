<template>
  <div class="focus-detector" :class="{ 'fd-full': mode === 'full' }">
    <div class="fd-toggle" v-if="mode === 'compact'">
      <label class="fd-toggle-label">📷 专注检测</label>
      <button class="fd-toggle-btn" :class="{ active: isDetecting }" @click="toggleDetection">
        {{ isDetecting ? '停止' : '开启' }}
      </button>
    </div>

    <template v-if="mode === 'full'">
      <div class="fd-full-camera">
        <video ref="videoRef" autoplay playsinline class="fd-full-video" v-show="isDetecting"></video>
        <div class="fd-full-placeholder" v-show="!isDetecting">
          <span class="fd-ph-icon">📷</span>
          <p>点击下方按钮启动摄像头</p>
          <p class="fd-error-msg" v-if="cameraError">{{ cameraError }}</p>
        </div>
        <canvas ref="canvasRef" class="fd-canvas"></canvas>
      </div>
      <div class="fd-full-controls">
        <button class="fd-ctrl-btn start" @click="startDetection" :disabled="isDetecting">▶ 开始检测</button>
        <button class="fd-ctrl-btn stop" @click="stopDetection" :disabled="!isDetecting">■ 停止</button>
        <span class="fd-status-tag" :class="statusClass">{{ statusText }}</span>
      </div>
      <div class="fd-full-stats">
        <div class="fd-score-ring">
          <svg viewBox="0 0 100 100" class="fd-ring-svg">
            <circle cx="50" cy="50" r="42" fill="none" stroke="#eee" stroke-width="8" />
            <circle cx="50" cy="50" r="42" fill="none" :stroke="scoreColor" stroke-width="8"
              stroke-linecap="round" :stroke-dasharray="circumference"
              :stroke-dashoffset="dashOffset" transform="rotate(-90 50 50)" />
          </svg>
          <div class="fd-score-text">
            <span class="fd-score-num">{{ focusScore }}</span>
            <span class="fd-score-lbl">{{ focusLabel }}</span>
          </div>
        </div>
        <div class="fd-details">
          <div class="fd-detail-row">
            <span class="fd-detail-label">👁 眼部</span>
            <div class="fd-detail-bar"><div class="fd-detail-fill eye" :style="{ width: eyeScore + '%' }"></div></div>
            <span class="fd-detail-val">{{ eyeScore }}</span>
          </div>
          <div class="fd-detail-row">
            <span class="fd-detail-label">🧠 头部</span>
            <div class="fd-detail-bar"><div class="fd-detail-fill head" :style="{ width: headScore + '%' }"></div></div>
            <span class="fd-detail-val">{{ headScore }}</span>
          </div>
          <div class="fd-detail-row">
            <span class="fd-detail-label">🧍 身体</span>
            <div class="fd-detail-bar"><div class="fd-detail-fill body" :style="{ width: bodyScore + '%' }"></div></div>
            <span class="fd-detail-val">{{ bodyScore }}</span>
          </div>
          <div class="fd-detail-row">
            <span class="fd-detail-label">👤 人脸</span>
            <span class="fd-detail-tag" :class="faceDetected ? 'ok' : 'err'">{{ faceDetected ? '已检测' : '未检测' }}</span>
          </div>
          <div class="fd-detail-row">
            <span class="fd-detail-label">👁 眨眼</span>
            <span class="fd-detail-val">{{ blinkCount }}次</span>
          </div>
        </div>
      </div>
    </template>

    <template v-if="mode === 'compact'">
      <div class="fd-body" v-if="isDetecting">
        <div class="fd-camera-hidden">
          <video ref="videoRef" autoplay playsinline class="fd-video"></video>
          <canvas ref="canvasRef" class="fd-canvas"></canvas>
        </div>
        <div class="fd-stats">
          <div class="fd-score-ring">
            <svg viewBox="0 0 100 100" class="fd-ring-svg">
              <circle cx="50" cy="50" r="42" fill="none" stroke="#eee" stroke-width="8" />
              <circle cx="50" cy="50" r="42" fill="none" :stroke="scoreColor" stroke-width="8"
                stroke-linecap="round" :stroke-dasharray="circumference"
                :stroke-dashoffset="dashOffset" transform="rotate(-90 50 50)" />
            </svg>
            <div class="fd-score-text">
              <span class="fd-score-num">{{ focusScore }}</span>
              <span class="fd-score-lbl">{{ focusLabel }}</span>
            </div>
          </div>
          <div class="fd-details">
            <div class="fd-detail-row">
              <span class="fd-detail-label">👁 眼部</span>
              <div class="fd-detail-bar"><div class="fd-detail-fill eye" :style="{ width: eyeScore + '%' }"></div></div>
              <span class="fd-detail-val">{{ eyeScore }}</span>
            </div>
            <div class="fd-detail-row">
              <span class="fd-detail-label">🧠 头部</span>
              <div class="fd-detail-bar"><div class="fd-detail-fill head" :style="{ width: headScore + '%' }"></div></div>
              <span class="fd-detail-val">{{ headScore }}</span>
            </div>
            <div class="fd-detail-row">
              <span class="fd-detail-label">🧍 身体</span>
              <div class="fd-detail-bar"><div class="fd-detail-fill body" :style="{ width: bodyScore + '%' }"></div></div>
              <span class="fd-detail-val">{{ bodyScore }}</span>
            </div>
          </div>
        </div>
      </div>
      <div class="fd-placeholder" v-else>
      <span v-if="!cameraError">点击"开启"启动专注检测</span>
      <span class="fd-error-msg" v-else>{{ cameraError }}</span>
    </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, watch, onUnmounted } from 'vue'
import { detectFocus } from '../api/vision'

const props = defineProps({
  mode: { type: String, default: 'compact', validator: v => ['compact', 'full'].includes(v) },
  autoStart: { type: Boolean, default: false },
  intervalMs: { type: Number, default: 3000 },
})

const emit = defineEmits(['score-update', 'detection-change'])

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
const cameraError = ref('')

let stream = null
let captureInterval = null

const circumference = 2 * Math.PI * 42
const dashOffset = computed(() => circumference * (1 - focusScore.value / 100))
const scoreColor = computed(() => {
  if (focusScore.value >= 65) return '#67c23a'
  if (focusScore.value >= 45) return '#e6a23c'
  if (focusScore.value >= 25) return '#ff9d4d'
  return '#f56c6c'
})

const statusClass = computed(() => {
  if (!isDetecting.value) return 'idle'
  if (focusScore.value >= 65) return 'good'
  if (focusScore.value >= 45) return 'warn'
  if (focusScore.value >= 25) return 'bad'
  return 'bad'
})

const statusText = computed(() => {
  if (!isDetecting.value) return '未启动'
  return focusLabel.value
})

async function startDetection() {
  cameraError.value = ''
  try {
    stream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } })
    if (videoRef.value) videoRef.value.srcObject = stream
    isDetecting.value = true
    emit('detection-change', true)
    captureInterval = setInterval(captureAndDetect, props.intervalMs)
  } catch (err) {
    isDetecting.value = false
    emit('detection-change', false)
    if (err.name === 'NotAllowedError' || err.message?.includes('Permission denied')) {
      cameraError.value = '摄像头权限被拒绝，请点击地址栏左侧📷图标允许访问'
    } else if (err.name === 'NotFoundError') {
      cameraError.value = '未检测到摄像头设备'
    } else if (err.name === 'NotReadableError' || err.name === 'AbortError') {
      cameraError.value = '摄像头被其他程序占用，请关闭后重试'
    } else {
      cameraError.value = `启动失败: ${err.message || err.name}`
    }
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
  emit('detection-change', false)
}

function toggleDetection() {
  if (isDetecting.value) stopDetection()
  else startDetection()
}

async function captureAndDetect() {
  if (!videoRef.value || !canvasRef.value) return
  const video = videoRef.value
  if (video.videoWidth === 0) return

  const canvas = canvasRef.value
  canvas.width = video.videoWidth
  canvas.height = video.videoHeight
  const ctx = canvas.getContext('2d')
  ctx.drawImage(video, 0, 0)

  canvas.toBlob(async (blob) => {
    if (!blob) return
    try {
      const file = new File([blob], 'frame.jpg', { type: 'image/jpeg' })
      const res = await detectFocus(file)
      if (res.success && res.data) {
        const d = res.data
        focusScore.value = Math.round(d.focus_score || 0)
        focusLabel.value = d.focus_level || '未知'
        eyeScore.value = Math.round(d.eye_score || 0)
        headScore.value = Math.round(d.head_score || 0)
        bodyScore.value = Math.round(d.body_score || 0)
        faceDetected.value = d.face_detected || false
        blinkCount.value = d.blink_count || 0
        emit('score-update', {
          focusScore: focusScore.value,
          focusLabel: focusLabel.value,
          eyeScore: eyeScore.value,
          headScore: headScore.value,
          bodyScore: bodyScore.value,
        })
      }
    } catch (e) {
      console.warn('专注检测请求失败:', e.message)
    }
  }, 'image/jpeg', 0.8)
}

watch(() => props.autoStart, (val) => {
  if (val && !isDetecting.value) startDetection()
  else if (!val && isDetecting.value) stopDetection()
})

onUnmounted(() => {
  stopDetection()
})

defineExpose({ startDetection, stopDetection, isDetecting, focusScore, focusLabel })
</script>

<style scoped>
.focus-detector {
  border: 1px solid #e8e4dc;
  border-radius: 12px;
  overflow: hidden;
  background: rgba(255,255,255,0.6);
}

.fd-toggle {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 14px;
  background: rgba(139,105,20,0.08);
  border-bottom: 1px solid #e8e4dc;
}
.fd-toggle-label {
  font-size: 13px;
  font-weight: 600;
  color: #5c4033;
}
.fd-toggle-btn {
  padding: 3px 14px;
  border: 1px solid #8b6914;
  border-radius: 12px;
  background: transparent;
  color: #8b6914;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}
.fd-toggle-btn.active {
  background: #8b6914;
  color: #fff;
}
.fd-toggle-btn:hover {
  opacity: 0.85;
}

.fd-camera-hidden { display: none; }
.fd-video { display: none; }
.fd-canvas { display: none; }

.fd-body {
  padding: 10px;
}
.fd-stats {
  display: flex;
  align-items: center;
  gap: 16px;
}
.fd-score-ring {
  position: relative;
  width: 80px;
  height: 80px;
  flex-shrink: 0;
}
.fd-ring-svg {
  width: 100%;
  height: 100%;
}
.fd-score-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
}
.fd-score-num {
  font-size: 20px;
  font-weight: 700;
  color: #3d2b1f;
  line-height: 1;
}
.fd-score-lbl {
  font-size: 10px;
  color: #7a6555;
  margin-top: 2px;
}
.fd-details {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.fd-detail-row {
  display: flex;
  align-items: center;
  gap: 6px;
}
.fd-detail-label {
  font-size: 11px;
  min-width: 40px;
  color: #7a6555;
}
.fd-detail-bar {
  flex: 1;
  height: 6px;
  background: #eee;
  border-radius: 3px;
  overflow: hidden;
}
.fd-detail-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.5s ease;
}
.fd-detail-fill.eye { background: #409eff; }
.fd-detail-fill.head { background: #67c23a; }
.fd-detail-fill.body { background: #e6a23c; }
.fd-detail-val {
  font-size: 11px;
  min-width: 24px;
  text-align: right;
  color: #3d2b1f;
  font-weight: 600;
}
.fd-detail-tag {
  font-size: 11px;
  padding: 1px 8px;
  border-radius: 8px;
  font-weight: 600;
}
.fd-detail-tag.ok {
  background: rgba(103,194,58,0.15);
  color: #67c23a;
}
.fd-detail-tag.err {
  background: rgba(245,108,108,0.15);
  color: #f56c6c;
}
.fd-placeholder {
  padding: 16px;
  text-align: center;
  font-size: 12px;
  color: #aaa;
}

/* ===== Full mode ===== */
.fd-full {
  border: none;
  background: transparent;
}

.fd-full-camera {
  width: 100%;
  min-height: 220px;
  background: #1a1a2e;
  border-radius: 10px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}
.fd-full-video {
  width: 100%;
  max-height: 280px;
  object-fit: contain;
  display: block;
}
.fd-full-placeholder {
  color: #909399;
  text-align: center;
}
.fd-ph-icon {
  font-size: 40px;
  display: block;
  margin-bottom: 8px;
}
.fd-full-placeholder p {
  font-size: 13px;
  margin: 0;
}
.fd-error-msg {
  color: #f56c6c;
  font-size: 12px;
  margin-top: 6px;
  max-width: 280px;
  line-height: 1.4;
}

.fd-full-controls {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  justify-content: center;
}
.fd-ctrl-btn {
  padding: 5px 16px;
  border: 1px solid #8b6914;
  border-radius: 14px;
  background: transparent;
  color: #8b6914;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}
.fd-ctrl-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.fd-ctrl-btn.start:not(:disabled):hover,
.fd-ctrl-btn.stop:not(:disabled):hover {
  background: #8b6914;
  color: #fff;
}
.fd-status-tag {
  font-size: 11px;
  padding: 2px 10px;
  border-radius: 10px;
  font-weight: 600;
}
.fd-status-tag.idle { background: #f0f0f0; color: #999; }
.fd-status-tag.good { background: rgba(103,194,58,0.15); color: #67c23a; }
.fd-status-tag.warn { background: rgba(230,162,60,0.15); color: #e6a23c; }
.fd-status-tag.bad { background: rgba(245,108,108,0.15); color: #f56c6c; }

.fd-full-stats {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-top: 12px;
}
.fd-full-stats .fd-score-ring {
  width: 100px;
  height: 100px;
}
.fd-full-stats .fd-score-num {
  font-size: 26px;
}
.fd-full-stats .fd-score-lbl {
  font-size: 11px;
}
.fd-full-stats .fd-details {
  gap: 8px;
}
.fd-full-stats .fd-detail-label {
  font-size: 12px;
  min-width: 44px;
}
.fd-full-stats .fd-detail-bar {
  height: 8px;
  border-radius: 4px;
}
.fd-full-stats .fd-detail-fill {
  border-radius: 4px;
}
.fd-full-stats .fd-detail-val {
  font-size: 12px;
}
</style>
