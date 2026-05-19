import request from './request'

export function getOverview(userId = 1) {
  return request.get('/dashboard/overview', { params: { user_id: userId } })
}

export function getWeeklyFocus(userId = 1) {
  return request.get('/dashboard/weekly-focus', { params: { user_id: userId } })
}

export function getFocusDistribution(userId = 1, days = 7) {
  return request.get('/dashboard/focus-distribution', {
    params: { user_id: userId, days },
  })
}

export function getStudyHeatmap(userId = 1, days = 30) {
  return request.get('/dashboard/study-heatmap', {
    params: { user_id: userId, days },
  })
}
