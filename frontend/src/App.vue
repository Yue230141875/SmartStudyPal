<template>
  <div class="desk-scene">
    <div class="desk-bg-wrapper">
      <img :src="deskBg" alt="desk" class="desk-img" />
    </div>

    <div class="desk-header">
      <span class="desk-title">SmartStudyPal</span>
      <span :class="apiStatus ? 'status-ok' : 'status-err'" class="api-dot">
        {{ apiStatus ? '●' : '○' }}
      </span>
    </div>

    <!-- 设置按钮 -->
    <button class="settings-btn" @click="showSettings = true" title="设置">
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="3"/>
        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
      </svg>
    </button>

    <!-- 设置面板 -->
    <div v-if="showSettings" class="settings-overlay" @click="showSettings = false">
      <div class="settings-panel" @click.stop>
        <div class="settings-header">
          <span>⚙️ 设置</span>
          <button class="settings-close" @click="showSettings = false">✕</button>
        </div>
        <div class="settings-body">
          <div class="settings-item">
            <label class="settings-label">🔊 语音音量</label>
            <div class="volume-control">
              <input
                type="range"
                min="0"
                max="100"
                :value="volumePercent"
                @input="onVolumeChange"
                class="volume-slider"
              />
              <span class="volume-value">{{ volumePercent }}%</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 实时时钟 -->
    <div class="clock-panel">
      <div class="clock-time">{{ currentTime }}</div>
      <div class="clock-date">{{ currentDate }}</div>
    </div>

    <!-- 阿米娅角色 -->
    <div
      class="desk-character"
      :class="{ 'character-active': characterClicked, 'character-listening': isListening }"
      @mousedown="onAmiyaPointerDown"
      @touchstart.prevent="onAmiyaPointerDown"
      @touchend="onAmiyaPointerUp"
      @touchcancel="onAmiyaPointerCancel"
      @contextmenu.prevent
    >
      <div class="desk-character-inner">
        <img :src="amiyaImg" alt="amiya" class="character-img" draggable="false" />
        <div class="character-shadow"></div>
        <div v-if="isListening || isProcessing" class="listening-indicator">
          <span class="listening-dot" v-if="isListening"></span>
          <span class="listening-text">{{ isProcessing ? '识别中...' : (listeningText || '聆听中...') }}</span>
        </div>
      </div>
    </div>

    <!-- 底部功能入口悬浮窗 -->
    <div class="widgets-float-window">
      <div class="widgets-container">
        <button
          v-for="w in widgets"
          :key="w.id"
          class="widget-btn"
          @click.stop="openWidget(w)"
        >
          <span class="widget-emoji">{{ w.emoji }}</span>
          <span class="widget-label">{{ w.label }}</span>
        </button>
      </div>
    </div>

    <!-- 功能弹窗 -->
    <div v-if="activeWidget" class="widget-overlay" @click="closeWidget">
      <div class="widget-modal" :style="{ width: activeWidget.width, height: activeWidget.height }" @click.stop>
        <div class="widget-header">
          <span class="widget-title">{{ activeWidget.emoji }} {{ activeWidget.label }}</span>
          <button class="widget-close" @click="closeWidget">✕</button>
        </div>
        <div class="widget-content">
          <component :is="activeWidget.component" ref="widgetRef" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, shallowRef, onMounted, onUnmounted } from 'vue'
import axios from 'axios'
import { amiyaSpeak, getAmiyaReadyAudio, speechToText } from './api/voice'
import StudySession from './components/StudySession.vue'
import DashboardView from './views/DashboardView.vue'
import deskBgImg from './assets/desk.png'
import amiyaImgSrc from './assets/amiya.png'

const apiStatus = ref(false)
const activeWidget = ref(null)
const characterClicked = ref(false)
const deskBg = ref(deskBgImg)
const amiyaImg = ref(amiyaImgSrc)
const showSettings = ref(false)
const volumePercent = ref(parseInt(localStorage.getItem('amiya_volume') || '80'))

const currentTime = ref('')
const currentDate = ref('')
let clockTimer = null

const preloadedAudio = ref(null)
const preloadedLongPressAudio = ref(null)
const preloadedOkAudio = ref(null)
let preloadPromise = null

const isListening = ref(false)
const listeningText = ref('')
const isProcessing = ref(false)
const widgetRef = ref(null)
let longPressTimer = null
let isLongPress = false
let mediaStream = null
let audioContext = null
let gainNode = null
let scriptNode = null
let recordedSamples = []
const LONG_PRESS_MS = 500

function updateClock() {
  const now = new Date()
  currentTime.value = now.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })
  currentDate.value = now.toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' })
}

updateClock()
clockTimer = setInterval(updateClock, 1000)

async function preloadAmiyaAudio() {
  try {
    const texts = [
      { text: '博士，我在', store: (a) => { preloadedAudio.value = a } },
      { text: '怎么了，博士', store: (a) => { preloadedLongPressAudio.value = a } },
      { text: '好的', store: (a) => { preloadedOkAudio.value = a } },
    ]
    for (const item of texts) {
      try {
        let audioUrl = null
        try {
          const readyRes = await getAmiyaReadyAudio(item.text)
          if (readyRes.success && readyRes.data?.audio_url) {
            audioUrl = readyRes.data.audio_url
          }
        } catch { /* ready未命中 */ }
        if (!audioUrl) {
          try {
            const res = await amiyaSpeak(item.text, true)
            if (res.success && res.data?.audio_url) {
              audioUrl = res.data.audio_url
            }
          } catch (e2) {
            console.warn(`合成失败: ${item.text}`, e2.message)
          }
        }
        if (audioUrl) {
          const audio = new Audio(audioUrl)
          audio.volume = volumePercent.value / 100
          audio.preload = 'auto'
          item.store(audio)
          console.log(`预加载成功: ${item.text}`)
        }
      } catch (e) {
        console.warn(`预加载失败: ${item.text}`, e.message)
      }
    }
  } catch (e) {
    console.warn('阿米娅语音预加载失败:', e.message)
  }
}

preloadPromise = preloadAmiyaAudio()

function playAudio(url) {
  return new Promise((resolve, reject) => {
    const audio = new Audio(url)
    audio.volume = volumePercent.value / 100
    audio.onended = () => resolve()
    audio.onerror = (e) => reject(e)
    audio.play().catch(reject)
  })
}

async function playPreloaded(preloadedRef) {
  if (preloadedRef.value) {
    try {
      const player = preloadedRef.value.cloneNode(true)
      player.volume = volumePercent.value / 100
      player.onended = () => {}
      player.onerror = () => {}
      await player.play()
      return true
    } catch (e) {
      console.warn('预加载音频播放失败:', e.message)
    }
  }
  return false
}

async function fetchAndPlay(text) {
  let audioUrl = null
  try {
    const readyRes = await getAmiyaReadyAudio(text)
    if (readyRes.success && readyRes.data?.audio_url) {
      audioUrl = readyRes.data.audio_url
    }
  } catch { /* ready未命中，继续尝试合成 */ }
  if (!audioUrl) {
    try {
      const res = await amiyaSpeak(text, true)
      if (res.success && res.data?.audio_url) {
        audioUrl = res.data.audio_url
      }
    } catch (e) {
      console.warn('合成语音失败:', e.message)
    }
  }
  if (audioUrl) {
    await playAudio(audioUrl)
  }
}

let docMouseUpHandler = null

function onAmiyaPointerDown() {
  isLongPress = false
  longPressTimer = setTimeout(() => {
    isLongPress = true
    onLongPressStart()
  }, LONG_PRESS_MS)

  docMouseUpHandler = () => {
    onAmiyaPointerUp()
    document.removeEventListener('mouseup', docMouseUpHandler)
    docMouseUpHandler = null
  }
  document.addEventListener('mouseup', docMouseUpHandler)
}

function onAmiyaPointerUp() {
  clearTimeout(longPressTimer)
  if (isLongPress) {
    onLongPressEnd()
  } else {
    onShortPress()
  }
}

function onAmiyaPointerCancel() {
  clearTimeout(longPressTimer)
  if (docMouseUpHandler) {
    document.removeEventListener('mouseup', docMouseUpHandler)
    docMouseUpHandler = null
  }
  if (isLongPress) {
    onLongPressEnd()
  }
  isLongPress = false
}

async function onShortPress() {
  characterClicked.value = true
  setTimeout(() => { characterClicked.value = false }, 600)

  try {
    if (await playPreloaded(preloadedAudio)) return
    await preloadPromise
    if (await playPreloaded(preloadedAudio)) return
    await fetchAndPlay('博士，我在')
  } catch (error) {
    console.error('阿米娅语音播放失败:', error)
  }
}

async function onLongPressStart() {
  characterClicked.value = true
  setTimeout(() => { characterClicked.value = false }, 600)

  isListening.value = true
  isProcessing.value = false
  listeningText.value = '启动麦克风...'

  playPreloaded(preloadedLongPressAudio).catch(() => {
    fetchAndPlay('怎么了，博士').catch(() => {})
  })

  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
        channelCount: 1,
        sampleRate: 16000,
      }
    })

    audioContext = new AudioContext({ sampleRate: 16000 })
    const source = audioContext.createMediaStreamSource(mediaStream)

    gainNode = audioContext.createGain()
    gainNode.gain.value = 3.0

    const compressor = audioContext.createDynamicsCompressor()
    compressor.threshold.value = -30
    compressor.knee.value = 20
    compressor.ratio.value = 8
    compressor.attack.value = 0.003
    compressor.release.value = 0.1

    scriptNode = audioContext.createScriptProcessor(4096, 1, 1)
    recordedSamples = []

    scriptNode.onaudioprocess = (e) => {
      const inputData = e.inputBuffer.getChannelData(0)
      recordedSamples.push(new Float32Array(inputData))
    }

    source.connect(gainNode)
    gainNode.connect(compressor)
    compressor.connect(scriptNode)
    scriptNode.connect(audioContext.destination)

    listeningText.value = '聆听中...'
  } catch (e) {
    console.warn('麦克风启动失败:', e)
    if (e.name === 'NotAllowedError') {
      listeningText.value = '请允许麦克风权限'
    } else if (e.name === 'NotFoundError') {
      listeningText.value = '未检测到麦克风'
    } else {
      listeningText.value = '麦克风启动失败'
    }
    setTimeout(() => {
      isListening.value = false
      listeningText.value = ''
    }, 2000)
  }
}

function onLongPressEnd() {
  isLongPress = false

  if (scriptNode) {
    scriptNode.disconnect()
    scriptNode = null
  }

  if (!mediaStream || recordedSamples.length === 0) {
    isListening.value = false
    isProcessing.value = false
    listeningText.value = ''
    cleanupAudioResources()
    return
  }

  isListening.value = false
  isProcessing.value = true
  listeningText.value = '识别中...'

  const allSamples = concatFloat32Arrays(recordedSamples)
  recordedSamples = []

  cleanupAudioResources()

  const wavBlob = encodeWAV(allSamples, 16000)

  processWithBackendASR(wavBlob)
}

function concatFloat32Arrays(arrays) {
  let totalLength = 0
  for (const arr of arrays) totalLength += arr.length
  const result = new Float32Array(totalLength)
  let offset = 0
  for (const arr of arrays) {
    result.set(arr, offset)
    offset += arr.length
  }
  return result
}

function encodeWAV(samples, sampleRate) {
  const buffer = new ArrayBuffer(44 + samples.length * 2)
  const view = new DataView(buffer)

  function writeString(offset, string) {
    for (let i = 0; i < string.length; i++) {
      view.setUint8(offset + i, string.charCodeAt(i))
    }
  }

  writeString(0, 'RIFF')
  view.setUint32(4, 36 + samples.length * 2, true)
  writeString(8, 'WAVE')
  writeString(12, 'fmt ')
  view.setUint32(16, 16, true)
  view.setUint16(20, 1, true)
  view.setUint16(22, 1, true)
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * 2, true)
  view.setUint16(32, 2, true)
  view.setUint16(34, 16, true)
  writeString(36, 'data')
  view.setUint32(40, samples.length * 2, true)

  let offset = 44
  for (let i = 0; i < samples.length; i++) {
    let s = Math.max(-1, Math.min(1, samples[i]))
    s = s < 0 ? s * 0x8000 : s * 0x7FFF
    view.setInt16(offset, s, true)
    offset += 2
  }

  return new Blob([buffer], { type: 'audio/wav' })
}

function cleanupAudioResources() {
  if (mediaStream) {
    mediaStream.getTracks().forEach(t => t.stop())
    mediaStream = null
  }
  if (audioContext) {
    try { audioContext.close() } catch { /* ignore */ }
    audioContext = null
    gainNode = null
  }
  scriptNode = null
  recordedSamples = []
}

async function processWithBackendASR(wavBlob) {
  try {
    const result = await speechToText(wavBlob, 'zh')
    if (result.success && result.data?.text) {
      const text = result.data.text.trim()
      const pinyin = (result.data.pinyin || '').toLowerCase()
      console.log('后端ASR识别结果:', text, '拼音:', pinyin)
      if (text && tryMatchText(text, pinyin)) {
        isProcessing.value = false
        listeningText.value = ''
        return
      }
    }
    console.log('ASR未匹配到命令')
  } catch (e) {
    console.warn('后端ASR失败:', e.message)
  }
  isProcessing.value = false
  listeningText.value = ''
}

const PINYIN_MAP = {
  '正计时': 'zhengjishi',
  '番茄钟': 'fanqiezhong',
  '倒计时': 'daojishi',
}

function tryMatchText(text, pinyin) {
  for (const [keyword, tabId] of Object.entries(VOICE_COMMANDS)) {
    if (text.includes(keyword)) {
      console.log('精确匹配语音命令:', keyword, '->', tabId)
      executeVoiceCommand(tabId)
      return true
    }
  }
  if (pinyin) {
    for (const [keyword, tabId] of Object.entries(VOICE_COMMANDS)) {
      const kwPinyin = PINYIN_MAP[keyword]
      if (kwPinyin && pinyin.includes(kwPinyin)) {
        console.log('拼音匹配语音命令:', keyword, '->', tabId, '(识别拼音:', pinyin, ')')
        executeVoiceCommand(tabId)
        return true
      }
    }
    for (const [keyword, tabId] of Object.entries(VOICE_COMMANDS)) {
      const kwPinyin = PINYIN_MAP[keyword]
      if (kwPinyin && fuzzyPinyinMatch(pinyin, kwPinyin)) {
        console.log('模糊拼音匹配语音命令:', keyword, '->', tabId, '(识别拼音:', pinyin, ')')
        executeVoiceCommand(tabId)
        return true
      }
    }
  }
  return false
}

function fuzzyPinyinMatch(recognized, target) {
  const r = recognized.replace(/[^a-z]/g, '')
  const t = target.replace(/[^a-z]/g, '')
  if (r.length < 2 || t.length < 2) return false
  if (r.includes(t.substring(0, Math.ceil(t.length * 0.6)))) return true
  let matchCount = 0
  let j = 0
  for (let i = 0; i < t.length && j < r.length; i++) {
    if (r[j] === t[i]) {
      matchCount++
      j++
    }
  }
  return matchCount / t.length >= 0.7
}

async function executeVoiceCommand(tabId) {
  const studyWidget = widgets.find(w => w.id === 'study')
  if (studyWidget) {
    activeWidget.value = studyWidget
    await new Promise(r => setTimeout(r, 100))
    if (widgetRef.value && widgetRef.value.switchToTab) {
      widgetRef.value.switchToTab(tabId)
    }
  }
  try {
    if (!(await playPreloaded(preloadedOkAudio))) {
      await preloadPromise
      if (!(await playPreloaded(preloadedOkAudio))) {
        await fetchAndPlay('好的')
      }
    }
  } catch (e) {
    console.warn('播放"好的"失败:', e)
  }
}

const VOICE_COMMANDS = {
  '正计时': 'stopwatch',
  '番茄钟': 'pomodoro',
  '倒计时': 'countdown',
}

const widgets = [
  {
    id: 'study',
    label: '开始自习',
    emoji: '📖',
    width: '560px',
    height: '680px',
    component: shallowRef(StudySession),
  },
  {
    id: 'dashboard',
    label: '数据看板',
    emoji: '📊',
    width: '760px',
    height: '560px',
    component: shallowRef(DashboardView),
  },
]

function openWidget(w) {
  activeWidget.value = w
}

function closeWidget() {
  activeWidget.value = null
}

function onVolumeChange(e) {
  volumePercent.value = parseInt(e.target.value)
  localStorage.setItem('amiya_volume', String(volumePercent.value))
}

onMounted(async () => {
  try {
    await axios.get('/api/health', { timeout: 3000 })
    apiStatus.value = true
  } catch {
    apiStatus.value = false
  }
})

onUnmounted(() => {
  if (clockTimer) clearInterval(clockTimer)
  cleanupAudioResources()
})
</script>

<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;700&display=swap');

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body, #app {
  height: 100%;
  overflow: hidden;
}

body {
  font-family: 'Noto Sans SC', sans-serif;
}

.desk-scene {
  position: relative;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
}

.desk-bg-wrapper {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  background: linear-gradient(135deg, #f5f3ef 0%, #e8e4dc 100%);
}

.desk-img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.desk-header {
  position: absolute;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 24px;
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(10px);
  border-radius: 20px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
}

.desk-title {
  font-size: 18px;
  font-weight: 700;
  color: #5c4033;
}

.api-dot {
  font-size: 14px;
}

.status-ok {
  color: #67c23a;
}

.status-err {
  color: #f56c6c;
}

.desk-character {
  position: absolute;
  left: 50%;
  bottom: 15%;
  cursor: pointer;
  z-index: 10;
}

.clock-panel {
  position: absolute;
  left: 50%;
  top: 35%;
  transform: translate(-50%, -50%);
  z-index: 9;
  text-align: center;
  padding: 16px 40px;
  background: rgba(255, 255, 255, 0.45);
  backdrop-filter: blur(16px);
  border-radius: 24px;
  border: 1px solid rgba(255, 255, 255, 0.3);
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.1);
  user-select: none;
}

.clock-time {
  font-size: 52px;
  font-weight: 700;
  color: #3d2b1f;
  letter-spacing: 4px;
  line-height: 1.2;
  font-variant-numeric: tabular-nums;
}

.clock-date {
  font-size: 16px;
  font-weight: 500;
  color: #7a6555;
  margin-top: 4px;
  letter-spacing: 1px;
}

.desk-character-inner {
  transition: transform 0.3s ease;
  transform: translateX(-50%);
}

.desk-character:hover .desk-character-inner {
  transform: translateX(-50%) translateY(-10px);
}

.desk-character.character-active .desk-character-inner {
  animation: characterBounce 0.6s ease;
}

.desk-character.character-listening .desk-character-inner {
  animation: listeningPulse 1.2s ease-in-out infinite;
}

@keyframes listeningPulse {
  0%, 100% { transform: translateX(-50%) scale(1); }
  50% { transform: translateX(-50%) scale(1.03); }
}

.listening-indicator {
  position: absolute;
  top: -40px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 6px;
  background: rgba(74, 108, 247, 0.92);
  color: #fff;
  padding: 6px 14px;
  border-radius: 18px;
  font-size: 13px;
  white-space: nowrap;
  pointer-events: none;
  box-shadow: 0 2px 12px rgba(74, 108, 247, 0.4);
}

.listening-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #fff;
  animation: dotBlink 0.8s ease-in-out infinite;
}

@keyframes dotBlink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

.listening-text {
  font-size: 12px;
  line-height: 1;
}

@keyframes characterBounce {
  0%, 100% { transform: translateX(-50%) translateY(0); }
  30% { transform: translateX(-50%) translateY(-15px); }
  60% { transform: translateX(-50%) translateY(-8px); }
}

.character-img {
  width: 182px;
  height: auto;
  filter: drop-shadow(0 8px 20px rgba(0, 0, 0, 0.2));
}

.character-shadow {
  position: absolute;
  bottom: -10px;
  left: 50%;
  transform: translateX(-50%);
  width: 130px;
  height: 20px;
  background: radial-gradient(ellipse, rgba(0, 0, 0, 0.3) 0%, transparent 70%);
  border-radius: 50%;
}

.widgets-float-window {
  position: absolute;
  left: 8%;
  top: 50%;
  transform: translateY(-50%);
  z-index: 8;
  padding: 20px 14px;
  background: rgba(240, 240, 240, 0.35);
  backdrop-filter: blur(20px);
  border-radius: 40px;
  border: 1px solid rgba(255, 255, 255, 0.15);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.25);
}

.widgets-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
}

.widget-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 12px 20px;
  background: rgba(255, 255, 255, 0.6);
  border: none;
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.3s ease;
  min-width: 80px;
}

.widget-btn:hover {
  background: rgba(255, 255, 255, 0.9);
  transform: scale(1.1);
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.15);
}

.widget-btn:active {
  transform: scale(0.95);
}

.widget-emoji {
  font-size: 28px;
}

.widget-label {
  font-size: 13px;
  color: #5c4033;
  font-weight: 500;
}

.widget-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(5px);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 100;
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.widget-modal {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  border-radius: 24px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  overflow: hidden;
  animation: slideUp 0.3s ease;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.widget-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background: linear-gradient(135deg, #8b6914 0%, #a07a23 100%);
  color: white;
}

.widget-title {
  font-size: 16px;
  font-weight: 600;
}

.widget-close {
  width: 28px;
  height: 28px;
  border: none;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 50%;
  color: white;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.widget-close:hover {
  background: rgba(255, 255, 255, 0.3);
  transform: scale(1.1);
}

.widget-content {
  padding: 20px;
  height: calc(100% - 60px);
  overflow: auto;
}

.settings-btn {
  position: absolute;
  top: 24px;
  left: 24px;
  z-index: 20;
  width: 42px;
  height: 42px;
  border: none;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.75);
  backdrop-filter: blur(10px);
  color: #5c4033;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
}

.settings-btn:hover {
  background: rgba(255, 255, 255, 0.95);
  transform: rotate(30deg) scale(1.1);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15);
}

.settings-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(4px);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 200;
  animation: fadeIn 0.2s ease;
}

.settings-panel {
  width: 380px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  border-radius: 20px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.25);
  overflow: hidden;
  animation: slideUp 0.3s ease;
}

.settings-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background: linear-gradient(135deg, #8b6914 0%, #a07a23 100%);
  color: white;
  font-size: 16px;
  font-weight: 600;
}

.settings-close {
  width: 28px;
  height: 28px;
  border: none;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 50%;
  color: white;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.settings-close:hover {
  background: rgba(255, 255, 255, 0.3);
  transform: scale(1.1);
}

.settings-body {
  padding: 24px;
}

.settings-item {
  margin-bottom: 20px;
}

.settings-item:last-child {
  margin-bottom: 0;
}

.settings-label {
  display: block;
  font-size: 15px;
  font-weight: 500;
  color: #5c4033;
  margin-bottom: 12px;
}

.volume-control {
  display: flex;
  align-items: center;
  gap: 16px;
}

.volume-slider {
  flex: 1;
  -webkit-appearance: none;
  appearance: none;
  height: 6px;
  border-radius: 3px;
  background: linear-gradient(to right, #8b6914, #a07a23);
  outline: none;
  cursor: pointer;
}

.volume-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #8b6914;
  border: 3px solid white;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
  cursor: pointer;
  transition: transform 0.2s ease;
}

.volume-slider::-webkit-slider-thumb:hover {
  transform: scale(1.2);
}

.volume-slider::-moz-range-thumb {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #8b6914;
  border: 3px solid white;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
  cursor: pointer;
}

.volume-value {
  min-width: 45px;
  text-align: right;
  font-size: 14px;
  font-weight: 600;
  color: #8b6914;
}
</style>
