# SmartStudyPal - 智能陪伴自习系统

> 基于视觉-语音多模态融合的沉浸式智能学习伴侣，搭载明日方舟阿米娅声线克隆

![Vue3](https://img.shields.io/badge/Vue-3.4-4FC08D?logo=vue.js)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?logo=fastapi)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python)
![License](https://img.shields.io/badge/License-MIT-green)

## 项目简介

SmartStudyPal 是一款面向自习场景的智能陪伴系统，通过 **摄像头视觉检测** + **阿米娅语音交互** 双模态融合，为用户提供专注度实时监测、番茄钟计时、白噪音播放、数据统计等全套自习辅助功能。

**核心亮点**：
- 阿米娅声线克隆（MiMo VoiceClone）—— 真正的罗德岛领袖音色
- 多因子专注度评分算法 v2 —— 眼部/头部/身体三维加权 + 方向无关转头检测
- 沉浸式桌面场景 UI —— 毛玻璃面板、悬浮交互、零 Element Plus 依赖

## 功能概览

| 功能模块 | 描述 | 完成度 |
|---------|------|--------|
| 视觉专注检测 | Dlib 人脸 68 点 + MediaPipe 姿态估计，0-100 分实时评分 | 98% |
| 阿米娅语音交互 | MiMo V2.5 声线克隆，点击/长按/鼓励语音/番茄钟提醒 | 100% |
| 自习模式 | 番茄钟 / 倒计时 / 正计时 / 专注检测 四种模式 | 90% |
| 白噪音播放器 | 多种环境音切换，沉浸式学习氛围 | 80% |
| 数据看板 | 学习时长统计与可视化展示 | 80% |
| 多模态融合引擎 | 视觉 0.7 + 语音 0.3 加权融合 + 冲突检测 + 自动降级 | 100% |

## 技术架构

```
SmartStudyPal/
├── frontend/                  # Vue3 + Vite 前端
│   ├── src/
│   │   ├── components/       # FocusDetector, StudySession, WhiteNoisePlayer
│   │   ├── views/            # Home, Focus, Dashboard, Pomodoro
│   │   ├── api/              # Axios 封装层
│   │   └── App.vue           # 主场景（桌面 + 时钟 + 阿米娅）
│   └── vite.config.js        # API 代理配置
│
├── backend/                   # FastAPI 后端
│   ├── main.py               # 应用入口
│   ├── database.py           # SQLite 数据库管理
│   ├── api/                  # RESTful 接口层
│   │   ├── vision.py         # /api/vision/detect
│   │   ├── voice.py          # /api/voice/amiya/*
│   │   ├── pomodoro.py       # /api/pomodoro/*
│   │   └── dashboard.py      # /api/dashboard/stats
│   └── modules/
│       ├── vision/           # 视觉算法引擎
│       │   ├── face_detector.py    # Dlib HOG+SVM + 68点 + EAR
│       │   ├── focus_scorer.py     # 多因子加权评分 v2
│       │   ├── pose_estimator.py   # MediaPipe Pose/FaceMesh
│       │   └── image_preprocessor.py
│       ├── voice/            # 语音处理引擎
│       │   ├── amiya_tts.py        # MiMo VoiceClone 声线克隆
│       │   ├── asr_whisper.py      # Whisper 语音识别
│       │   ├── wake_word.py        # 唤醒词检测
│       │   └── emotion_classifier.py
│       ├── fusion_engine.py         # 多模态融合
│       └── degradation_manager.py   # 服务降级管理
│
├── .github/workflows/        # CI/CD
└── README.md
```

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- 摄像头（用于专注检测）
- dlib 模型文件 `shape_predictor_68_face_landmarks.dat`（需单独下载）

### 1. 克隆仓库

```bash
git clone https://github.com/Yue230141875/SmartStudyPal.git
cd SmartStudyPal
```

### 2. 后端启动

```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# 下载 dlib 模型（~100MB）
# 放到 backend/models/shape_predictor_68_face_landmarks.dat
# 下载地址: http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2

# 启动服务（默认端口 8000）
python main.py
```

> 后端 API 文档：http://localhost:8000/docs (Swagger UI)

### 3. 前端启动

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器（默认端口 5173）
npm run dev
```

打开浏览器访问 http://localhost:5173

### 4. 配置 MiMo VoiceClone（可选）

编辑 [amiya_tts.py](backend/modules/voice/amiya_tts.py) 中的 API 配置：

```python
MIMO_API_KEY = "your-api-key"
MIMO_BASE_URL = "https://api.mimo.im/v1"
REFERENCE_AUDIO_PATH = "path/to/Reference.wav"  # 阿米娅参考音频
```

详细配置指南参见 [mimo_voiceclone_trae_guide.md](mimo_voiceclone_trae_guide.md)

## 核心算法

### 专注度评分模型 v2

多因子加权评分 + EAR 可靠性校正：

```
total_score = eye_score × 0.4 + head_score × 0.3 + body_score × 0.3
```

**眼部评分**（EAR = Eye Aspect Ratio）：
- EAR ≥ 0.25 → 100 分（睁眼正常）
- EAR ≥ 0.20 → 80 分
- EAR ≥ 0.18 → 50 分（可能疲劳）
- EAR < 0.18 → 15 分（闭眼）

**头部评分**（纯 yaw/pitch 角度驱动，方向无关）：

| yaw 范围 | yaw_score | 说明 |
|---------|-----------|------|
| \|yaw\| < 20° | 100 | 正视/微调 |
| 20° ~ 35° | 75 | 轻度偏头 |
| 35° ~ 50° | 45 | 大幅转头 |
| \|yaw\| ≥ 50° | 20 | 极端侧脸 |

**EAR 可靠性校正**（解决 dlib 侧脸方向性不对称）：

| yaw 幅度 | eye_score 上限 |
|---------|---------------|
| < 25° | 不限制(100) |
| 25° ~ 35° | 75 |
| 35° ~ 50° | 55 |
| ≥ 50° | 30 |

**状态标签映射**：
- ≥ 65 分 → 🟢 专注
- ≥ 45 分 → 🟡 轻度分心
- ≥ 25 分 → 🟠 明显走神
- < 25 分 → 🔴 疲劳

### 阿米娅声线克隆

基于小米 **MiMo-V2.5-TTS-VoiceClone** API 实现：

1. 参考音频编码为 Data URI 发送至 MiMo
2. 自然语言风格指令控制音色/语速/情感
3. MD5 哈希缓存避免重复合成
4. 后台线程预合成常用语音（<100ms 响应）

风格指令（最终版）：
> 角色=明日方舟阿米娅罗德岛领袖；风格=温柔亲切带责任感，清亮干净，音调自然偏高，语速适中偏快，干脆利落；基调=温暖关怀偶尔成熟担当；禁止=颤抖/沙哑/拖音/过度撒娇

## API 接口

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| POST | `/api/vision/detect` | 视觉专注度检测 |
| POST | `/api/voice/amiya/speak` | 阿米娅语音合成 |
| GET | `/api/voice/amiya/ready` | 获取预合成音频 URL |
| GET | `/api/voice/amiya/encouragement` | 随机鼓励学习语音 |
| GET | `/api/voice/amiya/audio/{filename}` | 音频文件服务 |
| POST | `/api/pomodoro/start` | 启动番茄钟 |
| POST | `/api/pomodoro/pause` | 暂停番茄钟 |
| GET | `/api/pomodoro/status` | 番茄钟状态查询 |
| GET | `/api/dashboard/stats` | 学习统计数据 |

## 项目状态

| 指标 | 状态 |
|------|------|
| 总体完成度 | **87%** |
| 核心功能（专注检测+语音交互） | ✅ 已完成并深度优化 |
| 前后端联调 | ✅ 基本完成 |
| AC-1 视觉准确率实测 | 待实测验证（目标≥85%） |
| 房间/座位预约 | 🔴 未实现（Out of Scope 低优先级） |
| 连续30分钟稳定性压力测试 | 待执行 |

详细进度参见 [功能完成度报告.md](功能完成度报告.md)

## 开发日志

完整的开发提示词记录和决策过程参见 [开发提示词日志.md](开发提示词日志.md)，包含：
- 项目初始化与技术选型变更
- 阿米娅声线克隆调优过程（8轮迭代）
- 专注检测模块深度优化 v2（4轮迭代修复转头不对称问题）
- Git 版本管理与 GitHub 推送记录

## 技术选型变更

| 计划方案 | 实际方案 | 变更原因 |
|---------|---------|---------|
| pyTTS 离线语音合成 | **MiMo V2.5 VoiceClone API** | 声线克隆能力 + 音质 |
| Element Plus UI 库 | **自研桌面场景 CSS** | 沉浸式体验 |
| edge-tts + 音频迁移 | **直接 MiMo VoiceClone** | 效果不理想 |
| 同步预合成 | **异步后台线程(daemon)** | 启动超时 |
| sounddevice 服务端播放 | **Audio 前端浏览器播放** | 浏览器端输出 |

## 许可证

MIT License

---

> 开发者：陈岳 230141875 · 基于 Trae IDE (Vibe Coding) 开发
