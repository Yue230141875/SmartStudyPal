import request from './request'

export function startSession(userId = 1) {
  return request.post('/pomodoro/session/start', { user_id: userId })
}

export function endSession(sessionId, focusScoreAvg = null) {
  return request.post(`/pomodoro/session/${sessionId}/end`, null, {
    params: focusScoreAvg !== null ? { focus_score_avg: focusScoreAvg } : {},
  })
}

export function listSessions(userId = 1, limit = 20) {
  return request.get('/pomodoro/session/list', { params: { user_id: userId, limit } })
}

export function addSnapshot(data) {
  return request.post('/pomodoro/snapshot', data)
}

export function getSnapshots(sessionId) {
  return request.get(`/pomodoro/snapshot/${sessionId}`)
}

export function startPomodoro(data) {
  return request.post('/pomodoro/pomodoro/start', data)
}

export function completePomodoro(pomodoroId, actualDuration, focusScoreAvg = null) {
  return request.post(`/pomodoro/pomodoro/${pomodoroId}/complete`, {
    actual_duration: actualDuration,
    focus_score_avg: focusScoreAvg,
  })
}

export function listPomodoros(userId = 1, dateStr = null, limit = 20) {
  return request.get('/pomodoro/pomodoro/list', {
    params: { user_id: userId, date_str: dateStr, limit },
  })
}

export function getTodayStats(userId = 1) {
  return request.get('/pomodoro/pomodoro/today-stats', { params: { user_id: userId } })
}

export function fuseFocusScore(visionScore, voiceEmotion) {
  return request.post('/pomodoro/fuse', null, {
    params: { vision_score: visionScore, voice_emotion: voiceEmotion },
  })
}

export function getFocusTrend(n = 10) {
  return request.get('/pomodoro/trend', { params: { n } })
}
