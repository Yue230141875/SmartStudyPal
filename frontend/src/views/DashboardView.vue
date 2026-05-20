<template>
  <div class="dashboard-view">
    <div class="stat-row">
      <div v-for="card in statCards" :key="card.label" class="stat-card">
        <div class="stat-icon" :style="{ background: card.color }">
          <el-icon :size="22"><component :is="card.icon" /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ card.value }}</div>
          <div class="stat-label">{{ card.label }}</div>
        </div>
      </div>
    </div>

    <div class="chart-row">
      <div class="chart-section">
        <div class="section-title">近7天专注度趋势</div>
        <div class="bar-chart">
          <div v-for="item in weeklyData" :key="item.date" class="bar-item">
            <div class="bar-wrapper">
              <div class="bar" :style="{ height: item.avg_focus_score + '%', background: barColor(item.avg_focus_score) }"></div>
            </div>
            <span class="bar-label">{{ item.date.slice(5) }}</span>
            <span class="bar-value">{{ item.avg_focus_score }}</span>
          </div>
        </div>
      </div>
      <div class="dist-section">
        <div class="section-title">专注度分布</div>
        <div class="distribution">
          <div v-for="(count, label) in distribution" :key="label" class="dist-item">
            <span class="dist-label">{{ label }}</span>
            <el-progress :percentage="distPercentage(count)" :stroke-width="12" :color="distColor(label)" />
            <span class="dist-count">{{ count }}次</span>
          </div>
        </div>
      </div>
    </div>

    <div class="bottom-row">
      <div class="pomo-section">
        <div class="section-title">今日番茄钟</div>
        <div class="pomo-summary">
          <div class="pomo-stat">
            <span class="pomo-number">{{ todayStats.completed || 0 }}</span>
            <span class="pomo-desc">已完成</span>
          </div>
          <div class="pomo-stat">
            <span class="pomo-number">{{ todayStats.total_focus_hours || 0 }}</span>
            <span class="pomo-desc">专注(h)</span>
          </div>
          <div class="pomo-stat">
            <span class="pomo-number">{{ todayStats.avg_focus_score || 0 }}</span>
            <span class="pomo-desc">平均专注</span>
          </div>
        </div>
      </div>
      <div class="heatmap-section">
        <div class="section-title">学习热力图</div>
        <div class="heatmap-grid">
          <div
            v-for="item in heatmapData"
            :key="item.date"
            class="heatmap-cell"
            :style="{ background: heatmapColor(item.minutes) }"
            :title="`${item.date}: ${item.minutes}分钟`"
          ></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Timer, Clock, TrendCharts, Star } from '@element-plus/icons-vue'
import { getOverview, getWeeklyFocus, getFocusDistribution, getStudyHeatmap } from '../api/dashboard'

const todayStats = ref({})
const weeklyData = ref([])
const distribution = ref({})
const heatmapData = ref([])

const statCards = computed(() => [
  { label: '今日番茄', value: todayStats.value.pomodoro_completed || 0, icon: Timer, color: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' },
  { label: '专注时长', value: (todayStats.value.focus_hours || 0) + 'h', icon: Clock, color: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)' },
  { label: '学习会话', value: todayStats.value.session_count || 0, icon: TrendCharts, color: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)' },
  { label: '平均专注度', value: todayStats.value.avg_focus_score || 0, icon: Star, color: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)' },
])

function barColor(score) {
  if (score >= 75) return '#67c23a'
  if (score >= 50) return '#e6a23c'
  return '#f56c6c'
}

function distPercentage(count) {
  const total = Object.values(distribution.value).reduce((a, b) => a + b, 0)
  return total > 0 ? Math.round((count / total) * 100) : 0
}

function distColor(label) {
  const map = { '专注': '#67c23a', '轻度分心': '#e6a23c', '明显走神': '#f56c6c', '疲劳': '#909399' }
  return map[label] || '#409eff'
}

function heatmapColor(minutes) {
  if (minutes === 0) return '#ebedf0'
  if (minutes < 30) return '#9be9a8'
  if (minutes < 60) return '#40c463'
  if (minutes < 120) return '#30a14e'
  return '#216e39'
}

async function loadData() {
  try {
    const [overviewRes, weeklyRes, distRes, heatmapRes] = await Promise.all([
      getOverview(), getWeeklyFocus(), getFocusDistribution(), getStudyHeatmap(),
    ])
    if (overviewRes.success) todayStats.value = overviewRes.data.today
    if (weeklyRes.success) weeklyData.value = weeklyRes.data
    if (distRes.success) distribution.value = distRes.data
    if (heatmapRes.success) heatmapData.value = heatmapRes.data
  } catch (e) {
    console.error('加载仪表盘数据失败:', e)
  }
}

onMounted(loadData)
</script>

<style scoped>
.dashboard-view {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.stat-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}
.stat-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  background: #fafafa;
  border-radius: 10px;
  border: 1px solid #f0f0f0;
}
.stat-icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
}
.stat-value {
  font-size: 20px;
  font-weight: bold;
  color: #303133;
}
.stat-label {
  font-size: 12px;
  color: #909399;
}
.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 10px;
}
.chart-row {
  display: flex;
  gap: 16px;
}
.chart-section {
  flex: 2;
}
.dist-section {
  flex: 1;
}
.bar-chart {
  display: flex;
  align-items: flex-end;
  justify-content: space-around;
  height: 160px;
  padding: 8px 0;
}
.bar-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
}
.bar-wrapper {
  width: 28px;
  height: 120px;
  display: flex;
  align-items: flex-end;
}
.bar {
  width: 100%;
  border-radius: 3px 3px 0 0;
  transition: height 0.3s;
  min-height: 2px;
}
.bar-label {
  font-size: 10px;
  color: #909399;
  margin-top: 4px;
}
.bar-value {
  font-size: 10px;
  color: #606266;
}
.distribution {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.dist-item {
  display: flex;
  align-items: center;
  gap: 6px;
}
.dist-label {
  min-width: 55px;
  font-size: 12px;
  color: #606266;
}
.dist-item .el-progress {
  flex: 1;
}
.dist-count {
  min-width: 36px;
  text-align: right;
  font-size: 11px;
  color: #909399;
}
.bottom-row {
  display: flex;
  gap: 16px;
}
.pomo-section {
  flex: 1;
}
.heatmap-section {
  flex: 1;
}
.pomo-summary {
  display: flex;
  justify-content: space-around;
  padding: 12px 0;
}
.pomo-stat {
  text-align: center;
}
.pomo-number {
  display: block;
  font-size: 26px;
  font-weight: bold;
  color: #409eff;
}
.pomo-desc {
  font-size: 12px;
  color: #909399;
}
.heatmap-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 2px;
}
.heatmap-cell {
  width: 12px;
  height: 12px;
  border-radius: 2px;
}
</style>
