# MiMo-V2.5-TTS-VoiceClone 集成开发文档

> 文档来源：基于 https://platform.xiaomimimo.com/docs/zh-CN/usage-guide/speech-synthesis-v2.5 官方文档整理
> 交付对象：Trae (AI IDE) 用于代码生成
> 目标：在项目中集成小米 MiMo 语音克隆模型，实现基于音频样本的音色复刻语音合成

---

## 1. 项目概述

### 1.1 功能目标
- 基于用户提供的音频样本，复刻任意音色
- 将目标文本合成为克隆后的语音
- 支持风格控制（情绪、语速、方言、角色扮演等）

### 1.2 技术栈
- Python 3.8+
- `openai` SDK（MiMo API 兼容 OpenAI 协议）
- 依赖包：`openai`, `numpy`, `soundfile`（流式调用时需要）

### 1.3 环境变量
```bash
export MIMO_API_KEY="your-mimo-api-key-here"
```

---

## 2. API 基础信息

| 项目 | 值 |
|------|-----|
| Base URL | `https://api.xiaomimimo.com/v1` |
| 模型 ID | `mimo-v2.5-tts-voiceclone` |
| 认证方式 | Header: `api-key: $MIMO_API_KEY` |
| 计费 | **限时免费**（不消耗 Token 额度） |

---

## 3. 核心调用规则（⚠️ 必须严格遵守）

### 3.1 消息角色规则
- **目标文本** 必须放在 `role: assistant` 的 `content` 中
- `role: user` 的 `content` 为**可选**，用于传入风格控制指令（自然语言）
- `user` 消息内容**不会**出现在合成语音中

### 3.2 音频样本要求
- 格式：仅支持 `mp3` 或 `wav`
- 大小：Base64 编码后**不能超过 10 MB**
- 传递方式：必须通过 `data URI` 格式传入

### 3.3 音频样本 Data URI 格式
```
data:{MIME_TYPE};base64,{BASE64_AUDIO}
```
- `{MIME_TYPE}`: `audio/mpeg`（或 `audio/mp3`）、`audio/wav`
- `{BASE64_AUDIO}`: 音频文件的纯 Base64 编码字符串（不含任何前缀）

---

## 4. 完整可运行代码

### 4.1 基础调用（非流式）

```python
import base64
import os
from openai import OpenAI

# 初始化客户端
client = OpenAI(
    api_key=os.environ.get("MIMO_API_KEY"),
    base_url="https://api.xiaomimimo.com/v1",
)


def clone_voice(
    audio_path: str,
    text: str,
    style_prompt: str = "",
    output_path: str = "output.wav",
    audio_format: str = "wav"
) -> str:
    """
    基于音频样本克隆音色并合成语音

    Args:
        audio_path: 参考音频文件路径（mp3 或 wav）
        text: 要合成的目标文本
        style_prompt: 风格控制指令（自然语言），可选
        output_path: 输出音频文件路径
        audio_format: 输出格式，可选 wav / mp3 / pcm16

    Returns:
        输出文件路径
    """
    # 1. 读取并编码参考音频
    with open(audio_path, "rb") as f:
        voice_bytes = f.read()

    voice_base64 = base64.b64encode(voice_bytes).decode("utf-8")

    # 2. 构造 Data URI（根据文件扩展名判断 MIME 类型）
    ext = os.path.splitext(audio_path)[1].lower()
    mime_type = "audio/wav" if ext == ".wav" else "audio/mpeg"
    voice_data_uri = f"data:{mime_type};base64,{voice_base64}"

    # 3. 调用 API
    completion = client.chat.completions.create(
        model="mimo-v2.5-tts-voiceclone",
        messages=[
            {
                "role": "user",
                "content": style_prompt  # 风格控制指令，可为空字符串
            },
            {
                "role": "assistant",
                "content": text  # 必须：目标合成文本
            }
        ],
        audio={
            "format": audio_format,
            "voice": voice_data_uri  # 必须：Base64 编码的参考音频
        }
    )

    # 4. 解码并保存音频
    message = completion.choices[0].message
    audio_bytes = base64.b64decode(message.audio.data)

    with open(output_path, "wb") as f:
        f.write(audio_bytes)

    return output_path


# 使用示例
if __name__ == "__main__":
    result = clone_voice(
        audio_path="./voice_sample.mp3",      # 参考音频样本
        text="你好，这是克隆后的声音在说话。",  # 要合成的文本
        style_prompt="用沉稳有力的语气播报",      # 风格控制（可选）
        output_path="./cloned_output.wav",
        audio_format="wav"
    )
    print(f"合成完成：{result}")
```

### 4.2 流式调用（兼容模式）

> ⚠️ 注意：当前流式接口为兼容模式，仅在所有推理完成后以流式格式返回**一次**结果。低延迟真流式尚未上线。

```python
import base64
import os
import numpy as np
import soundfile as sf
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("MIMO_API_KEY"),
    base_url="https://api.xiaomimimo.com/v1",
)


def clone_voice_streaming(
    audio_path: str,
    text: str,
    style_prompt: str = "",
    output_path: str = "output.wav"
) -> str:
    """
    流式调用方式（当前为兼容模式）
    """
    # 编码参考音频
    with open(audio_path, "rb") as f:
        voice_bytes = f.read()

    voice_base64 = base64.b64encode(voice_bytes).decode("utf-8")
    ext = os.path.splitext(audio_path)[1].lower()
    mime_type = "audio/wav" if ext == ".wav" else "audio/mpeg"
    voice_data_uri = f"data:{mime_type};base64,{voice_base64}"

    # 流式调用（format 必须为 pcm16）
    completion = client.chat.completions.create(
        model="mimo-v2.5-tts-voiceclone",
        messages=[
            {"role": "user", "content": style_prompt},
            {"role": "assistant", "content": text}
        ],
        audio={
            "format": "pcm16",  # 流式调用必须指定 pcm16
            "voice": voice_data_uri
        },
        stream=True
    )

    # 收集音频数据（24kHz PCM16LE mono）
    collected_chunks = np.array([], dtype=np.float32)

    for chunk in completion:
        if not chunk.choices:
            continue

        delta = chunk.choices[0].delta
        audio = getattr(delta, "audio", None)

        if audio is not None:
            pcm_bytes = base64.b64decode(audio["data"])
            np_pcm = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            collected_chunks = np.concatenate((collected_chunks, np_pcm))
            print(f"Received audio chunk: {len(pcm_bytes)} bytes")

    # 保存为 wav 文件
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    sf.write(output_path, collected_chunks, samplerate=24000)

    return output_path


# 使用示例
if __name__ == "__main__":
    result = clone_voice_streaming(
        audio_path="./voice_sample.mp3",
        text="这是流式调用的测试文本。",
        style_prompt="",
        output_path="./streamed_output.wav"
    )
    print(f"流式合成完成：{result}")
```

---

## 5. 风格控制指南

### 5.1 自然语言控制（放在 user.content）

```python
style_prompt = "用轻快上扬的语调播报，语速稍快，带着查到成绩后压抑不住的激动与小骄傲，声音明亮有活力。"

style_prompt = """
角色：百年门阀岑家的现任大当家。自出生便被过继给祖庙的守门老人抚养，被塑造成一尊完美无瑕、绝情断欲的家族图腾。

场景：在祠堂的阴影里，看着那个不顾一切冲破保安防线来找她、企图带她私奔的男人。

指导：冰冷、慵懒却极具威压的低音御姐。语速极慢，每个字都像在舌尖滚过才吐出来，带着上位者漫不经心的傲慢。
"""
```

### 5.2 音频标签控制（放在 assistant.content 中）

```python
text = "(怅然)这么多年过去了，再走过那条街，心里一下子空了一块。"

text = "(东北话)哎呀妈呀，这天儿也忒冷了吧！你说这风，嗖嗖的，跟刀子似的，割脸啊！"

text = "(孙悟空)俺老孙来也！"

text = "(唱歌)原谅我这一生不羁放纵爱自由，也会怕有一天会跌倒。"
```

### 5.3 支持的标签类型

| 类型 | 示例 |
|------|------|
| 基础情绪 | 开心、悲伤、愤怒、恐惧、惊讶、兴奋、委屈、平静、冷漠 |
| 复合情绪 | 怅然、欣慰、无奈、愧疚、释然、嫉妒、厌倦、忐忑、动情 |
| 整体语调 | 温柔、高冷、活泼、严肃、慵懒、俏皮、深沉、干练、凌厉 |
| 音色定位 | 磁性、醇厚、清亮、空灵、稚嫩、苍老、甜美、沙哑、醇雅 |
| 人设腔调 | 夹子音、御姐音、正太音、大叔音、台湾腔 |
| 方言 | 东北话、四川话、河南话、粤语 |
| 角色扮演 | 孙悟空、林黛玉 |
| 唱歌 | 唱歌、sing、singing |

### 5.4 细粒度音频标签（可插入文本任意位置）

```python
text = "（紧张，深呼吸）呼……冷静，冷静。不就是一个面试吗……（语速加快，碎碎念）自我介绍已经背了五十遍了。"

text = "如果我当时……（沉默片刻）哪怕再坚持一秒钟，结果是不是就不一样了？（苦笑）呵，没如果了。"
```

| 风格类型 | 示例 |
|---------|------|
| 语速与节奏 | 吸气、深呼吸、叹气、长叹一口气、喘息、屏息 |
| 情绪状态 | 紧张、害怕、激动、疲惫、委屈、撒娇、心虚、震惊、不耐烦 |
| 语音特征 | 颤抖、声音颤抖、变调、破音、鼻音、气声、沙哑 |
| 哭笑表达 | 笑、轻笑、大笑、冷笑、抽泣、呜咽、哽咽、嚎啕大哭 |

---

## 6. 批量处理封装

```python
import base64
import os
from pathlib import Path
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("MIMO_API_KEY"),
    base_url="https://api.xiaomimimo.com/v1",
)


class MiMoVoiceCloner:
    """MiMo V2.5 TTS VoiceClone 封装类"""

    def __init__(self, api_key: str = None):
        self.client = OpenAI(
            api_key=api_key or os.environ.get("MIMO_API_KEY"),
            base_url="https://api.xiaomimimo.com/v1",
        )

    def _encode_audio(self, audio_path: str) -> str:
        """将音频文件编码为 Data URI"""
        with open(audio_path, "rb") as f:
            voice_bytes = f.read()

        voice_base64 = base64.b64encode(voice_bytes).decode("utf-8")
        ext = Path(audio_path).suffix.lower()
        mime_type = "audio/wav" if ext == ".wav" else "audio/mpeg"

        return f"data:{mime_type};base64,{voice_base64}"

    def synthesize(
        self,
        audio_path: str,
        text: str,
        style_prompt: str = "",
        output_path: str = "output.wav",
        audio_format: str = "wav"
    ) -> str:
        """单次语音合成"""
        voice_data_uri = self._encode_audio(audio_path)

        completion = self.client.chat.completions.create(
            model="mimo-v2.5-tts-voiceclone",
            messages=[
                {"role": "user", "content": style_prompt},
                {"role": "assistant", "content": text}
            ],
            audio={
                "format": audio_format,
                "voice": voice_data_uri
            }
        )

        audio_bytes = base64.b64decode(completion.choices[0].message.audio.data)

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(audio_bytes)

        return output_path

    def batch_synthesize(
        self,
        audio_path: str,
        texts: list[str],
        style_prompt: str = "",
        output_dir: str = "./outputs",
        audio_format: str = "wav"
    ) -> list[str]:
        """批量语音合成"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        results = []
        voice_data_uri = self._encode_audio(audio_path)

        for i, text in enumerate(texts):
            completion = self.client.chat.completions.create(
                model="mimo-v2.5-tts-voiceclone",
                messages=[
                    {"role": "user", "content": style_prompt},
                    {"role": "assistant", "content": text}
                ],
                audio={
                    "format": audio_format,
                    "voice": voice_data_uri
                }
            )

            audio_bytes = base64.b64decode(completion.choices[0].message.audio.data)
            output_path = output_dir / f"output_{i:03d}.{audio_format}"

            with open(output_path, "wb") as f:
                f.write(audio_bytes)

            results.append(str(output_path))
            print(f"[{i+1}/{len(texts)}] 已保存: {output_path}")

        return results


# 使用示例
if __name__ == "__main__":
    cloner = MiMoVoiceCloner()

    # 单次合成
    cloner.synthesize(
        audio_path="./sample.mp3",
        text="你好，这是克隆音色的测试。",
        style_prompt="用温柔亲切的语气",
        output_path="./output_single.wav"
    )

    # 批量合成
    texts = [
        "第一条语音内容。",
        "第二条语音内容。",
        "第三条语音内容。"
    ]
    cloner.batch_synthesize(
        audio_path="./sample.mp3",
        texts=texts,
        style_prompt="用专业沉稳的播报语气",
        output_dir="./batch_outputs"
    )
```

---

## 7. 常见问题与注意事项

### 7.1 模型限制
- ❌ 不支持唱歌模式
- ❌ 不支持预置音色
- ❌ 不支持音色设计（那是 VoiceDesign 模型的功能）
- ✅ 支持风格控制（自然语言 + 音频标签）

### 7.2 音频样本建议
- 样本质量直接影响克隆效果，建议使用清晰、无噪音的音频
- 样本时长：几秒即可，但更长更清晰的声音样本效果更好
- 样本内容：最好是目标人物的自然说话声，而非唱歌或喊叫

### 7.3 错误排查
- **400 错误**：检查 `assistant.content` 是否为空，或 `voice` 的 Data URI 格式是否正确
- **音频无法播放**：检查 `audio.format` 是否与输出文件扩展名匹配
- **Base64 过大**：确保编码后的字符串不超过 10 MB

### 7.4 流式调用注意
- 流式调用时 `audio.format` 必须设为 `pcm16`
- 当前流式接口为兼容模式，推理完成后一次性返回结果
- 输出音频采样率为 **24kHz**，单声道，PCM16LE

---

## 8. 项目文件结构建议

```
project/
├── .env                    # 环境变量（MIMO_API_KEY）
├── requirements.txt        # 依赖
│   openai>=1.0.0
│   numpy
│   soundfile
├── samples/
│   └── voice_sample.mp3    # 参考音频样本
├── outputs/                # 输出目录
├── mimo_tts/
│   ├── __init__.py
│   ├── voice_cloner.py     # 核心封装类
│   └── utils.py            # 工具函数
└── main.py                 # 入口文件
```

---

## 9. 快速验证清单

- [ ] 已获取 MiMo API Key 并设置环境变量
- [ ] 已安装 `openai` SDK: `pip install openai`
- [ ] 准备了参考音频样本（mp3 或 wav，< 10MB）
- [ ] 目标文本放在 `assistant` 角色的消息中
- [ ] 音频样本已正确编码为 Data URI 格式
- [ ] 已测试基础调用能正常返回音频数据

---

*文档生成时间：2026-05-19*
*基于 MiMo 官方文档 v2.5 版本*
