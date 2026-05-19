<template>
  <div class="white-noise-player">
    <el-card>
      <template #header>
        <span>白噪音</span>
      </template>
      <div class="noise-grid">
        <div
          v-for="noise in noiseList"
          :key="noise.name"
          class="noise-item"
          :class="{ active: activeNoise === noise.name }"
          @click="toggleNoise(noise.name)"
        >
          <div class="noise-icon">{{ noise.icon }}</div>
          <span class="noise-name">{{ noise.label }}</span>
        </div>
      </div>
      <div class="volume-control" v-if="activeNoise">
        <el-icon><Headset /></el-icon>
        <el-slider v-model="volume" :min="0" :max="100" style="flex: 1; margin: 0 12px" />
        <span class="volume-value">{{ volume }}%</span>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { Headset } from '@element-plus/icons-vue'

const activeNoise = ref(null)
const volume = ref(50)

const noiseList = [
  { name: 'rain', label: '雨声', icon: '🌧️' },
  { name: 'forest', label: '森林', icon: '🌲' },
  { name: 'ocean', label: '海浪', icon: '🌊' },
  { name: 'fire', label: '篝火', icon: '🔥' },
  { name: 'wind', label: '微风', icon: '🍃' },
  { name: 'cafe', label: '咖啡厅', icon: '☕' },
  { name: 'thunder', label: '雷声', icon: '⛈️' },
  { name: 'birds', label: '鸟鸣', icon: '🐦' },
]

let audioContext = null
let oscillator = null
let gainNode = null

function toggleNoise(name) {
  if (activeNoise.value === name) {
    stopNoise()
    activeNoise.value = null
  } else {
    stopNoise()
    startNoise(name)
    activeNoise.value = name
  }
}

function startNoise(name) {
  try {
    audioContext = new (window.AudioContext || window.webkitAudioContext)()
    const bufferSize = 2 * audioContext.sampleRate
    const buffer = audioContext.createBuffer(1, bufferSize, audioContext.sampleRate)
    const data = buffer.getChannelData(0)

    if (name === 'rain' || name === 'wind') {
      for (let i = 0; i < bufferSize; i++) {
        data[i] = Math.random() * 2 - 1
      }
    } else if (name === 'ocean') {
      for (let i = 0; i < bufferSize; i++) {
        const t = i / audioContext.sampleRate
        data[i] = (Math.random() * 2 - 1) * (0.5 + 0.5 * Math.sin(2 * Math.PI * 0.1 * t))
      }
    } else if (name === 'fire') {
      for (let i = 0; i < bufferSize; i++) {
        data[i] = (Math.random() * 2 - 1) * (0.3 + 0.7 * Math.random())
      }
    } else {
      for (let i = 0; i < bufferSize; i++) {
        data[i] = Math.random() * 2 - 1
      }
    }

    const source = audioContext.createBufferSource()
    source.buffer = buffer
    source.loop = true

    gainNode = audioContext.createGain()
    gainNode.gain.value = volume.value / 100 * 0.3

    const filter = audioContext.createBiquadFilter()
    if (name === 'rain') {
      filter.type = 'lowpass'
      filter.frequency.value = 4000
    } else if (name === 'forest' || name === 'birds') {
      filter.type = 'bandpass'
      filter.frequency.value = 2000
      filter.Q.value = 0.5
    } else if (name === 'thunder') {
      filter.type = 'lowpass'
      filter.frequency.value = 500
    } else if (name === 'cafe') {
      filter.type = 'bandpass'
      filter.frequency.value = 1000
      filter.Q.value = 0.3
    } else {
      filter.type = 'lowpass'
      filter.frequency.value = 3000
    }

    source.connect(filter)
    filter.connect(gainNode)
    gainNode.connect(audioContext.destination)
    source.start()
    oscillator = source
  } catch (e) {
    console.error('白噪音播放失败:', e)
  }
}

function stopNoise() {
  if (oscillator) {
    try { oscillator.stop() } catch (e) { /* ignore */ }
    oscillator = null
  }
  if (audioContext) {
    audioContext.close()
    audioContext = null
  }
  gainNode = null
}

watch(volume, (val) => {
  if (gainNode) {
    gainNode.gain.value = val / 100 * 0.3
  }
})
</script>

<style scoped>
.noise-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}
.noise-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 16px 8px;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
  background: #f5f7fa;
}
.noise-item:hover {
  background: #ecf5ff;
}
.noise-item.active {
  background: #409eff;
  color: #fff;
}
.noise-icon {
  font-size: 28px;
  margin-bottom: 6px;
}
.noise-name {
  font-size: 12px;
}
.volume-control {
  display: flex;
  align-items: center;
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid #f0f0f0;
}
.volume-value {
  min-width: 36px;
  text-align: right;
  font-size: 13px;
  color: #909399;
}
</style>
