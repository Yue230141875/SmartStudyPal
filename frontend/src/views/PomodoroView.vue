<template>
  <div class="pomodoro-view">
    <div class="timer-section">
      <el-progress
        type="circle"
        :percentage="percentage"
        :width="180"
        :stroke-width="12"
        :color="timerColor"
      >
        <template #default>
          <div class="timer-inner">
            <span class="timer-text">{{ displayTime }}</span>
            <span class="timer-sub">{{ isBreak ? '休息' : '专注' }}</span>
          </div>
        </template>
      </el-progress>
    </div>
    <div class="controls-section">
      <el-button type="primary" @click="toggleTimer" round size="small">
        {{ isRunning ? '暂停' : '开始' }}
      </el-button>
      <el-button @click="resetTimer" round size="small">重置</el-button>
      <el-tag :type="isBreak ? 'success' : 'primary'" size="small">
        {{ isBreak ? '休息中' : '学习中' }}
      </el-tag>
    </div>
    <div class="settings-section">
      <el-form inline size="small">
        <el-form-item label="学习">
          <el-input-number v-model="workMinutes" :min="1" :max="60" :disabled="isRunning" size="small" style="width: 80px" />
        </el-form-item>
        <el-form-item label="休息">
          <el-input-number v-model="breakMinutes" :min="1" :max="30" :disabled="isRunning" size="small" style="width: 80px" />
        </el-form-item>
      </el-form>
    </div>
    <div class="task-section">
      <el-input v-model="taskName" placeholder="输入当前任务..." :disabled="isRunning" clearable size="small">
        <template #prepend>任务</template>
      </el-input>
    </div>
    <div class="session-info">
      <span>已完成 {{ completedSessions }} 个番茄</span>
    </div>
    <el-divider />
    <WhiteNoisePlayer />
    <el-divider />
    <div class="history-section">
      <div class="history-title">今日记录</div>
      <div class="history-list">
        <div v-for="record in todayRecords" :key="record.id" class="history-item">
          <span class="history-task">{{ record.task_name }}</span>
          <span class="history-time">{{ formatDuration(record.actual_duration) }}</span>
          <el-tag :type="record.completed ? 'success' : 'info'" size="small">
            {{ record.completed ? '完成' : '进行中' }}
          </el-tag>
        </div>
        <el-empty v-if="todayRecords.length === 0" description="暂无记录" :image-size="40" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onUnmounted, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { startPomodoro, completePomodoro, listPomodoros } from '../api/pomodoro'
import WhiteNoisePlayer from '../components/WhiteNoisePlayer.vue'

const workMinutes = ref(25)
const breakMinutes = ref(5)
const taskName = ref('')
const totalSeconds = computed(() => (isBreak.value ? breakMinutes.value : workMinutes.value) * 60)
const remainingSeconds = ref(workMinutes.value * 60)
const isRunning = ref(false)
const isBreak = ref(false)
const completedSessions = ref(0)
const todayRecords = ref([])
const currentPomodoroId = ref(null)
let intervalId = null

const percentage = computed(() => {
  const total = totalSeconds.value
  if (total === 0) return 0
  return Math.round(((total - remainingSeconds.value) / total) * 100)
})

const displayTime = computed(() => {
  const mins = Math.floor(remainingSeconds.value / 60)
  const secs = remainingSeconds.value % 60
  return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
})

const timerColor = computed(() => {
  if (isBreak.value) return '#67c23a'
  if (percentage.value > 80) return '#e6a23c'
  return '#409eff'
})

async function toggleTimer() {
  if (isRunning.value) {
    clearInterval(intervalId)
    isRunning.value = false
  } else {
    if (!isBreak.value && !currentPomodoroId.value) {
      try {
        const res = await startPomodoro({
          task_name: taskName.value || '未命名任务',
          planned_duration: workMinutes.value * 60,
        })
        if (res.success) currentPomodoroId.value = res.data.id
      } catch (e) { /* ignore */ }
    }
    isRunning.value = true
    intervalId = setInterval(async () => {
      if (remainingSeconds.value > 0) {
        remainingSeconds.value--
      } else {
        clearInterval(intervalId)
        isRunning.value = false
        if (isBreak.value) {
          isBreak.value = false
          remainingSeconds.value = workMinutes.value * 60
          currentPomodoroId.value = null
          ElMessage.info('休息结束，继续学习吧！')
        } else {
          completedSessions.value++
          if (currentPomodoroId.value) {
            try { await completePomodoro(currentPomodoroId.value, workMinutes.value * 60) } catch (e) { /* ignore */ }
            currentPomodoroId.value = null
          }
          isBreak.value = true
          remainingSeconds.value = breakMinutes.value * 60
          ElMessage.success('休息一下吧！')
          loadTodayRecords()
        }
      }
    }, 1000)
  }
}

function resetTimer() {
  clearInterval(intervalId)
  isRunning.value = false
  isBreak.value = false
  remainingSeconds.value = workMinutes.value * 60
  currentPomodoroId.value = null
}

function formatDuration(seconds) {
  if (!seconds) return '-'
  return `${Math.floor(seconds / 60)}分钟`
}

async function loadTodayRecords() {
  try {
    const res = await listPomodoros(1, null, 10)
    if (res.success) todayRecords.value = res.data
  } catch (e) { /* ignore */ }
}

onMounted(loadTodayRecords)
onUnmounted(() => { if (intervalId) clearInterval(intervalId) })
</script>

<style scoped>
.pomodoro-view {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}
.timer-section {
  margin: 10px 0;
}
.timer-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
}
.timer-text {
  font-size: 36px;
  font-weight: bold;
  color: #303133;
}
.timer-sub {
  font-size: 13px;
  color: #909399;
}
.controls-section {
  display: flex;
  align-items: center;
  gap: 8px;
}
.settings-section {
  width: 100%;
}
.task-section {
  width: 100%;
  max-width: 360px;
}
.session-info {
  font-size: 13px;
  color: #909399;
}
.history-section {
  width: 100%;
}
.history-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 8px;
}
.history-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.history-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 0;
  border-bottom: 1px solid #f0f0f0;
}
.history-task {
  font-size: 13px;
  color: #303133;
  flex: 1;
}
.history-time {
  font-size: 12px;
  color: #909399;
  margin: 0 8px;
}
</style>
