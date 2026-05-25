<template>
  <div class="study-session">
    <div class="ss-tabs">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        class="ss-tab"
        :class="{ active: activeTab === tab.id }"
        @click="switchTab(tab.id)"
        :disabled="isRunning"
      >
        <span class="ss-tab-icon">{{ tab.icon }}</span>
        <span class="ss-tab-name">{{ tab.name }}</span>
      </button>
    </div>

    <!-- 专注检测独立页 -->
    <div v-if="activeTab === 'focus'" class="ss-focus-page">
      <FocusDetector mode="full" @score-update="onFocusScoreUpdate" />
    </div>

    <!-- 计时模式 -->
    <template v-else>
      <div class="ss-timer-area">
        <div class="ss-ring-wrap">
          <svg viewBox="0 0 200 200" class="ss-ring-svg">
            <circle cx="100" cy="100" r="88" fill="none" stroke="#eee" stroke-width="10" />
            <circle cx="100" cy="100" r="88" fill="none" :stroke="ringColor" stroke-width="10"
              stroke-linecap="round" :stroke-dasharray="ringCircumference"
              :stroke-dashoffset="ringDashOffset" transform="rotate(-90 100 100)" />
          </svg>
          <div class="ss-ring-text">
            <span class="ss-time-display">{{ displayTime }}</span>
            <span class="ss-time-sub">{{ timerSubLabel }}</span>
          </div>
        </div>
      </div>

      <div class="ss-controls">
        <button class="ss-ctrl-btn primary" @click="toggleTimer">
          {{ isRunning ? '⏸ 暂停' : '▶ 开始' }}
        </button>
        <button class="ss-ctrl-btn stop" @click="stopTimer" :disabled="!hasStarted">⏹ 停止</button>
      </div>

      <div class="ss-settings">
        <template v-if="activeTab === 'pomodoro'">
          <div class="ss-setting-row">
            <label>学习时长</label>
            <div class="ss-num-ctrl">
              <button @click="workMinutes = Math.max(1, workMinutes - 5)" :disabled="isRunning">−</button>
              <span>{{ workMinutes }}分钟</span>
              <button @click="workMinutes = Math.min(60, workMinutes + 5)" :disabled="isRunning">+</button>
            </div>
          </div>
          <div class="ss-setting-row">
            <label>休息时长</label>
            <div class="ss-num-ctrl">
              <button @click="breakMinutes = Math.max(1, breakMinutes - 1)" :disabled="isRunning">−</button>
              <span>{{ breakMinutes }}分钟</span>
              <button @click="breakMinutes = Math.min(30, breakMinutes + 1)" :disabled="isRunning">+</button>
            </div>
          </div>
          <div class="ss-session-count">已完成 {{ completedSessions }} 个番茄</div>
        </template>

        <template v-if="activeTab === 'countdown'">
          <div class="ss-setting-row">
            <label>倒计时时长</label>
            <div class="ss-num-ctrl">
              <button @click="adjustCountdown(-5)" :disabled="isRunning">−</button>
              <span>{{ countdownMinutes }}分钟</span>
              <button @click="adjustCountdown(5)" :disabled="isRunning">+</button>
            </div>
          </div>
        </template>

        <template v-if="activeTab === 'stopwatch'">
          <div class="ss-stopwatch-hint">正计时模式：记录学习时长</div>
        </template>
      </div>

      <div class="ss-task">
        <input v-model="taskName" placeholder="输入当前任务..." :disabled="isRunning" class="ss-task-input" />
      </div>

      <div class="ss-focus-section">
        <FocusDetector
          ref="compactFocusDetector"
          mode="compact"
          :auto-start="focusAutoStart"
          @score-update="onFocusScoreUpdate"
          @detection-change="onDetectionChange"
        />
      </div>

      <div class="ss-noise-section">
        <WhiteNoisePlayer />
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, watch, onUnmounted, onMounted } from 'vue'
import { startPomodoro, completePomodoro, startSession, endSession } from '../api/pomodoro'
import { getAmiyaEncouragement, getAmiyaFocusReminder } from '../api/voice'
import FocusDetector from './FocusDetector.vue'
import WhiteNoisePlayer from './WhiteNoisePlayer.vue'

const tabs = [
  { id: 'pomodoro', name: '番茄钟', icon: '🍅' },
  { id: 'countdown', name: '倒计时', icon: '⏳' },
  { id: 'stopwatch', name: '正计时', icon: '⏱️' },
  { id: 'focus', name: '专注检测', icon: '📷' },
]

const activeTab = ref('pomodoro')
const isRunning = ref(false)
const taskName = ref('')
const focusAutoStart = ref(false)
const isFocusDetecting = ref(false)
const compactFocusDetector = ref(null)

const workMinutes = ref(25)
const breakMinutes = ref(5)
const countdownMinutes = ref(30)
const completedSessions = ref(0)

const pomodoroRemaining = ref(25 * 60)
const countdownRemaining = ref(30 * 60)
const stopwatchElapsed = ref(0)
const isBreak = ref(false)
const currentPomodoroId = ref(null)
const currentSessionId = ref(null)
const studyStartTime = ref(null)

const hasStarted = computed(() => {
  if (activeTab.value === 'pomodoro') return pomodoroRemaining.value < workMinutes.value * 60
  if (activeTab.value === 'countdown') return countdownRemaining.value < countdownMinutes.value * 60
  return stopwatchElapsed.value > 0
})

let intervalId = null
let focusScoreSum = 0
let focusScoreCount = 0
let lastFocusReminderTime = 0
const FOCUS_REMINDER_COOLDOWN = 10000
const focusReminderAudios = ref([])

onMounted(async () => {
  try {
    const res = await getAmiyaFocusReminder()
    if (res.success && res.data?.audio_url) {
      focusReminderAudios.value.push(res.data.audio_url)
    }
  } catch { /* ignore */ }
  try {
    const res2 = await getAmiyaFocusReminder()
    if (res2.success && res2.data?.audio_url && !focusReminderAudios.value.includes(res2.data.audio_url)) {
      focusReminderAudios.value.push(res2.data.audio_url)
    }
  } catch { /* ignore */ }
  try {
    const res3 = await getAmiyaFocusReminder()
    if (res3.success && res3.data?.audio_url && !focusReminderAudios.value.includes(res3.data.audio_url)) {
      focusReminderAudios.value.push(res3.data.audio_url)
    }
  } catch { /* ignore */ }
  if (focusReminderAudios.value.length > 0) {
    console.log('[专注提醒] 预加载完成，缓存', focusReminderAudios.value.length, '条提醒语音')
  }
})

async function playEncouragement() {
  try {
    const res = await getAmiyaEncouragement()
    if (res.success && res.data?.audio_url) {
      const audio = new Audio(res.data.audio_url)
      const vol = parseInt(localStorage.getItem('amiya_volume') || '80')
      audio.volume = vol / 100
      audio.play().catch(() => {})
    }
  } catch { /* ignore */ }
}

const ringCircumference = 2 * Math.PI * 88

const ringDashOffset = computed(() => {
  let progress = 0
  if (activeTab.value === 'pomodoro') {
    const total = (isBreak.value ? breakMinutes.value : workMinutes.value) * 60
    progress = total > 0 ? (total - pomodoroRemaining.value) / total : 0
  } else if (activeTab.value === 'countdown') {
    const total = countdownMinutes.value * 60
    progress = total > 0 ? (total - countdownRemaining.value) / total : 0
  } else {
    const maxDisplay = 3600
    progress = Math.min(stopwatchElapsed.value / maxDisplay, 1)
  }
  return ringCircumference * (1 - progress)
})

const ringColor = computed(() => {
  if (activeTab.value === 'pomodoro' && isBreak.value) return '#67c23a'
  if (activeTab.value === 'countdown') {
    const total = countdownMinutes.value * 60
    if (total > 0 && countdownRemaining.value / total < 0.1) return '#f56c6c'
  }
  return '#8b6914'
})

const displayTime = computed(() => {
  let seconds = 0
  if (activeTab.value === 'pomodoro') {
    seconds = pomodoroRemaining.value
  } else if (activeTab.value === 'countdown') {
    seconds = countdownRemaining.value
  } else {
    seconds = stopwatchElapsed.value
  }
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = seconds % 60
  if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
})

const timerSubLabel = computed(() => {
  if (activeTab.value === 'pomodoro') return isBreak.value ? '休息中' : '专注中'
  if (activeTab.value === 'countdown') return '倒计时'
  return '正计时'
})

function switchTab(tabId) {
  if (isRunning.value) return
  activeTab.value = tabId
  if (tabId !== 'focus') {
    pomodoroRemaining.value = workMinutes.value * 60
    countdownRemaining.value = countdownMinutes.value * 60
    stopwatchElapsed.value = 0
    focusScoreSum = 0
    focusScoreCount = 0
  }
}

function adjustCountdown(delta) {
  countdownMinutes.value = Math.max(1, Math.min(180, countdownMinutes.value + delta))
  countdownRemaining.value = countdownMinutes.value * 60
}

function toggleTimer() {
  if (isRunning.value) {
    pauseTimer()
  } else {
    startTimer()
  }
}

async function startTimer() {
  isRunning.value = true
  studyStartTime.value = Date.now()

  playEncouragement()

  if (compactFocusDetector.value && !isFocusDetecting.value) {
    compactFocusDetector.value.startDetection()
  }

  if (!currentSessionId.value) {
    try {
      const res = await startSession(1)
      if (res.success) currentSessionId.value = res.data.session_id
    } catch { /* ignore */ }
  }

  if (activeTab.value === 'pomodoro' && !isBreak.value && !currentPomodoroId.value) {
    try {
      const res = await startPomodoro({
        task_name: taskName.value || '未命名任务',
        planned_duration: workMinutes.value * 60,
      })
      if (res.success) currentPomodoroId.value = res.data.id
    } catch (e) { /* ignore */ }
  }

  intervalId = setInterval(() => {
    if (activeTab.value === 'pomodoro') {
      tickPomodoro()
    } else if (activeTab.value === 'countdown') {
      tickCountdown()
    } else {
      tickStopwatch()
    }
  }, 1000)
}

function pauseTimer() {
  clearInterval(intervalId)
  intervalId = null
  isRunning.value = false
}

function stopTimer() {
  clearInterval(intervalId)
  intervalId = null
  isRunning.value = false

  const avgFocus = focusScoreCount > 0 ? Math.round(focusScoreSum / focusScoreCount) : null

  if (currentSessionId.value) {
    endSession(currentSessionId.value, avgFocus).catch(() => {})
    currentSessionId.value = null
  }

  if (currentPomodoroId.value) {
    const elapsed = workMinutes.value * 60 - pomodoroRemaining.value
    completePomodoro(currentPomodoroId.value, elapsed, avgFocus).catch(() => {})
    currentPomodoroId.value = null
  }

  if (compactFocusDetector.value && isFocusDetecting.value) {
    compactFocusDetector.value.stopDetection()
  }

  isBreak.value = false
  pomodoroRemaining.value = workMinutes.value * 60
  countdownRemaining.value = countdownMinutes.value * 60
  stopwatchElapsed.value = 0
  focusScoreSum = 0
  focusScoreCount = 0
  studyStartTime.value = null
}

function tickPomodoro() {
  if (pomodoroRemaining.value > 0) {
    pomodoroRemaining.value--
  } else {
    clearInterval(intervalId)
    intervalId = null
    isRunning.value = false
    if (isBreak.value) {
      isBreak.value = false
      pomodoroRemaining.value = workMinutes.value * 60
      currentPomodoroId.value = null
    } else {
      completedSessions.value++
      const avgFocus = focusScoreCount > 0 ? Math.round(focusScoreSum / focusScoreCount) : null
      if (currentPomodoroId.value) {
        completePomodoro(currentPomodoroId.value, workMinutes.value * 60, avgFocus).catch(() => {})
        currentPomodoroId.value = null
      }
      isBreak.value = true
      pomodoroRemaining.value = breakMinutes.value * 60
      focusScoreSum = 0
      focusScoreCount = 0
    }
  }
}

function tickCountdown() {
  if (countdownRemaining.value > 0) {
    countdownRemaining.value--
  } else {
    clearInterval(intervalId)
    intervalId = null
    isRunning.value = false
  }
}

function tickStopwatch() {
  stopwatchElapsed.value++
}

function onFocusScoreUpdate(data) {
  focusScoreSum += data.focusScore
  focusScoreCount++

  if (data.focusScore < 60) {
    const now = Date.now()
    if (now - lastFocusReminderTime > FOCUS_REMINDER_COOLDOWN) {
      lastFocusReminderTime = now
      console.log('[专注提醒] 分数低于60，触发提醒, score=', data.focusScore)
      playFocusReminder()
    }
  }
}

async function playFocusReminder() {
  try {
    if (focusReminderAudios.value.length > 0) {
      const idx = Math.floor(Math.random() * focusReminderAudios.value.length)
      const audio = new Audio(focusReminderAudios.value[idx])
      const vol = parseInt(localStorage.getItem('amiya_volume') || '80')
      audio.volume = vol / 100
      audio.play().catch(() => {})
      console.log('[专注提醒] 播放预缓存语音:', focusReminderAudios.value[idx])
      return
    }
    const res = await getAmiyaFocusReminder()
    console.log('[专注提醒] API返回:', res)
    if (res.success && res.data?.audio_url) {
      const audio = new Audio(res.data.audio_url)
      const vol = parseInt(localStorage.getItem('amiya_volume') || '80')
      audio.volume = vol / 100
      audio.play().catch(() => {})
    }
  } catch (e) {
    console.warn('[专注提醒] 播放失败:', e.message)
  }
}

function onDetectionChange(active) {
  isFocusDetecting.value = active
}

watch(workMinutes, (val) => {
  if (!isRunning.value && !isBreak.value) pomodoroRemaining.value = val * 60
})

watch(breakMinutes, (val) => {
  if (!isRunning.value && isBreak.value) pomodoroRemaining.value = val * 60
})

watch(countdownMinutes, (val) => {
  if (!isRunning.value) countdownRemaining.value = val * 60
})

onUnmounted(() => {
  if (intervalId) clearInterval(intervalId)
})

function switchToTab(tabId) {
  if (isRunning.value) return
  activeTab.value = tabId
  if (tabId !== 'focus') {
    pomodoroRemaining.value = workMinutes.value * 60
    countdownRemaining.value = countdownMinutes.value * 60
    stopwatchElapsed.value = 0
    focusScoreSum = 0
    focusScoreCount = 0
  }
}

defineExpose({ switchToTab })
</script>

<style scoped>
.study-session {
  display: flex;
  flex-direction: column;
  gap: 14px;
  height: 100%;
  overflow-y: auto;
  padding-right: 4px;
}
.ss-tabs {
  display: flex;
  gap: 4px;
  background: rgba(139,105,20,0.06);
  border-radius: 12px;
  padding: 4px;
}
.ss-tab {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 7px 2px;
  border: none;
  border-radius: 10px;
  background: transparent;
  cursor: pointer;
  transition: all 0.2s;
}
.ss-tab:hover:not(:disabled) {
  background: rgba(139,105,20,0.1);
}
.ss-tab.active {
  background: #8b6914;
  color: #fff;
  box-shadow: 0 2px 8px rgba(139,105,20,0.3);
}
.ss-tab:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.ss-tab-icon {
  font-size: 18px;
}
.ss-tab-name {
  font-size: 10px;
  font-weight: 600;
}
.ss-focus-page {
  flex: 1;
}
.ss-timer-area {
  display: flex;
  justify-content: center;
}
.ss-ring-wrap {
  position: relative;
  width: 160px;
  height: 160px;
}
.ss-ring-svg {
  width: 100%;
  height: 100%;
}
.ss-ring-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
}
.ss-time-display {
  font-size: 32px;
  font-weight: 700;
  color: #3d2b1f;
  font-variant-numeric: tabular-nums;
  line-height: 1;
}
.ss-time-sub {
  font-size: 12px;
  color: #7a6555;
  margin-top: 4px;
}
.ss-controls {
  display: flex;
  justify-content: center;
  gap: 12px;
}
.ss-ctrl-btn {
  padding: 8px 28px;
  border: 1px solid #8b6914;
  border-radius: 20px;
  background: transparent;
  color: #8b6914;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}
.ss-ctrl-btn.primary {
  background: #8b6914;
  color: #fff;
}
.ss-ctrl-btn.stop {
  border-color: #e74c3c;
  color: #e74c3c;
}
.ss-ctrl-btn.stop:hover:not(:disabled) {
  background: #e74c3c;
  color: #fff;
}
.ss-ctrl-btn.stop:disabled {
  border-color: #ccc;
  color: #ccc;
  cursor: not-allowed;
  opacity: 0.5;
}
.ss-ctrl-btn:hover {
  opacity: 0.85;
  transform: scale(1.03);
}
.ss-settings {
  padding: 10px 14px;
  background: rgba(139,105,20,0.04);
  border-radius: 10px;
}
.ss-setting-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
}
.ss-setting-row label {
  font-size: 13px;
  color: #5c4033;
  font-weight: 500;
}
.ss-num-ctrl {
  display: flex;
  align-items: center;
  gap: 8px;
}
.ss-num-ctrl button {
  width: 26px;
  height: 26px;
  border: 1px solid #ccc;
  border-radius: 50%;
  background: #fff;
  cursor: pointer;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}
.ss-num-ctrl button:hover:not(:disabled) {
  border-color: #8b6914;
  color: #8b6914;
}
.ss-num-ctrl button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.ss-num-ctrl span {
  font-size: 14px;
  font-weight: 600;
  color: #3d2b1f;
  min-width: 60px;
  text-align: center;
}
.ss-session-count {
  text-align: center;
  font-size: 12px;
  color: #7a6555;
  margin-top: 6px;
}
.ss-stopwatch-hint {
  text-align: center;
  font-size: 13px;
  color: #7a6555;
  padding: 4px 0;
}
.ss-task {
  width: 100%;
}
.ss-task-input {
  width: 100%;
  padding: 8px 14px;
  border: 1px solid #e8e4dc;
  border-radius: 10px;
  font-size: 13px;
  color: #3d2b1f;
  background: rgba(255,255,255,0.7);
  outline: none;
  transition: border-color 0.2s;
}
.ss-task-input:focus {
  border-color: #8b6914;
}
.ss-task-input:disabled {
  opacity: 0.6;
}
.ss-focus-section {
  margin-top: 2px;
}
.ss-noise-section :deep(.white-noise-player) {
  margin-top: 0;
}
.ss-noise-section :deep(.el-card) {
  border: 1px solid #e8e4dc;
  border-radius: 12px;
}
</style>
