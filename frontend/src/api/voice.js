import request from './request'

/**
 * 阿米娅语音合成API
 */
export function amiyaSpeak(text = null, forceSynthesize = false) {
  const params = text ? { text, force_synthesize: forceSynthesize } : { force_synthesize: forceSynthesize }
  return request.post('/voice/amiya/speak', null, {
    params
  })
}

export function getAmiyaReadyAudio(text = '博士，我在') {
  return request.get('/voice/amiya/ready', {
    params: { text }
  })
}

/**
 * 获取阿米娅可用语音列表
 */
export function getAmiyaVoices() {
  return request.get('/voice/amiya/voices')
}

/**
 * 文字转语音（通用TTS）
 */
export function textToSpeech(text, rate = 180, volume = 0.9) {
  return request.post('/voice/tts', {
    text,
    rate,
    volume
  })
}

/**
 * 获取可用语音列表
 */
export function getVoiceList() {
  return request.get('/voice/tts/voices')
}

/**
 * 语音识别
 */
export function speechToText(audioFile, language = 'zh') {
  const formData = new FormData()
  formData.append('audio', audioFile)
  return request.post('/voice/asr', formData, {
    params: { language },
    headers: { 'Content-Type': undefined }
  })
}

/**
 * 唤醒词检测
 */
export function wakeupDetect(audioFile) {
  const formData = new FormData()
  formData.append('audio', audioFile)
  return request.post('/voice/wakeup', formData, {
    headers: { 'Content-Type': undefined }
  })
}

/**
 * 语音情绪分析
 */
export function emotionAnalyze(audioFile) {
  const formData = new FormData()
  formData.append('audio', audioFile)
  return request.post('/voice/emotion', formData, {
    headers: { 'Content-Type': undefined }
  })
}
