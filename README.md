# SmartStudyPal - 智能陪伴自习系统

> 基于视觉-语音多模态融合的沉浸式智能学习伴侣，搭载明日方舟阿米娅声线克隆

![Vue3](https://img.shields.io/badge/Vue-3.4-4FC08D?logo=vue.js)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?logo=fastapi)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python)
![License](https://img.shields.io/badge/License-MIT-green)

## 项目简介

### 解决什么问题？

在数字化学习时代，**自习效率低下**是学生群体的普遍痛点：

- **缺乏实时反馈**：独自自习时不知道自己是否真的在专注，走神了也无人提醒
- **传统番茄钟太机械**：固定 25 分钟倒计时无法感知学习状态，"人在心不在"时仍继续计时
- **学习氛围缺失**：居家/宿舍环境缺少图书馆式的沉浸感，容易分心刷手机
- **学习数据黑箱**：每天学了多久、专注了多少时间、效率如何变化——全凭感觉，没有量化依据

SmartStudyPal 从 **AI + 教育** 的交叉视角出发，用计算机视觉和语音合成技术构建一个**能看、能说、能陪伴的智能学习伙伴**。

### 核心理念

> **"让 AI 成为你的自习伙伴，而不是冷冰冰的监控工具。"**

SmartStudyPal 的设计围绕一个核心矛盾：**学习需要自律，但人天生容易分心**。

传统方案（番茄钟 App、Forest 种树、自习室打卡）都只解决了"时间管理"问题，却忽略了**学习状态本身是否在线**。我们换了一个思路——与其强制你坐满 25 分钟，不如让你**知道自己此刻是否真的在专注**，并在走神时温柔地拉回来。

| 维度 | 传统自习的困境 | SmartStudyPal 的解法 |
|:-----|:--------------|:---------------------|
| **专注感知** | 不知道自己是否在走神，回过神来半小时已过 | 摄像头实时检测面部状态 → 0-100 分可视化评分 + 四级标签（专注/轻度分心/明显分心/严重分心） |
| **反馈机制** | 走神了没人提醒，全靠意志力硬撑 | 阿米娅语音实时提醒"博士，集中注意力哦"，用角色陪伴替代冰冷的系统通知 |
| **计时方式** | 机械倒计时不管你在不在状态 | 四种模式自由切换：番茄钟 / 倒计时 / 正计时 / 纯专注检测，适配不同学习场景 |
| **情感陪伴** | 一个人面对屏幕，孤独感强易放弃 | 自习开始随机播放鼓励语音 + 番茄钟结束语音总结 + 学习数据看板正向反馈 |
| **效果量化** | 学了多久、效率如何全凭感觉 | 每次自习记录时长与专注分布，统计每日/每周趋势，让进步看得见 |

这套方案的底层逻辑是 **"感知 → 反馈 → 激励"闭环**：AI 先通过视觉判断你的状态，再用语音给出即时反馈，最终通过数据积累形成长期激励。

### 技术特色

| 特色 | 技术实现 | 教育价值 |
|------|---------|---------|
| **非侵入式专注检测** | Dlib 68点人脸关键点 + MediaPipe 姿态估计，无需佩戴任何设备 | 学生无需额外硬件，打开摄像头即可使用 |
| **方向无关转头检测** | 纯 yaw 角度驱动的 v2 评分算法 + EAR 可靠性校正 | 无论坐姿偏左偏右，左右转头判定完全对称公平 |
| **情感化语音交互** | MiMo V2.5 声线克隆 API 复刻明日方舟阿米娅音色 | 用熟悉的角色声音降低工具使用的冰冷感，提升持续使用意愿 |
| **多模态融合决策** | 视觉 70% + 语音 30% 加权融合 + 冲突检测自动降级 | 单一信号不可靠时自动调整策略，保证判断鲁棒性 |
| **自适应学习辅助** | 自习开始随机播放鼓励语音 + 番茄钟结束语音提醒 | 在关键节点提供正向激励，形成"检测→反馈→激励"闭环 |

**核心亮点**：
- 🎯 **解决"不知道自己专不专注"的问题** —— 实时 0-100 分可视化评分 + 四级状态标签
- 🗣️ **解决"学习过程孤独无反馈"的问题** —— 阿米娅声线克隆提供情感化陪伴与鼓励
- ⏱️ **解决"机械计时不管状态"的问题** —— 四种自习模式适配不同场景（番茄钟/倒计时/正计时/纯检测）
- 📊 **解决"学习效果无法量化"的问题** —— 数据看板记录每次自习时长与专注分布

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

### 4. 配置 MiMo VoiceClone（语音合成功能必需）

项目使用环境变量管理敏感配置，**不要将密钥硬编码到代码中**：

```bash
# 复制模板文件
cp .env.example .env

# 编辑 .env 文件，填入你的 MiMo API Key
MIMO_API_KEY=your-mimo-api-key-here
```

> **获取 API Key**: 访问 [MiMo 官网](https://api.xiaomimimo.com) 注册并获取密钥

详细配置指南参见 [mimo_voiceclone_trae_guide.md](mimo_voiceclone_trae_guide.md)

> ⚠️ **注意**: `.env` 文件已被 `.gitignore` 忽略，不会被提交到仓库。请妥善保管你的密钥。

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
