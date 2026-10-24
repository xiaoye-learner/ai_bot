# AI Voice Chat WebUI (for GPT-SoVITS)

一个基于 GPT-SoVITS TTS 引擎的对话式 WebUI，实现直接的语音、文本交互式对话。  
本项目在原始 GPT-SoVITS 项目基础上新增 `webui.py`、`client_bot`、`Dockerfile.webui`、`requirements_webui.txt`，修改了`docker-compose.yaml`，使用docker容器部署方式。

---

## 项目参考来源

- GPT-SoVITS 官方项目: https://github.com/RVC-Boss/GPT-SoVITS  
- DeepSeek API (对话大模型): https://platform.deepseek.com/  
- Gradio (WebUI 框架): https://www.gradio.app/
- TTS音频训练集来源：https://www.gamekee.com/ba/tj/674785.html

---

## 快速开始

### 关键配置说明

- `webui.py` 内置关键配置:
  - `DEEPSEEK_API_KEY`: 对话模型 API Key（默认需要输入Deepseek API Key）
  - `TTS_API_URL`: TTS 推理服务地址，默认是 `http://gpt-sovits-bot:9880`
- 参考音频与参考文本:
  - `REF_AUDIO_PATH` / `REF_TEXT` / `REF_LANG` 可按需替换

---

## Docker 部署

> 适合一键部署 GPT-SoVITS + WebUI 的组合环境

本项目基于原项目的 `cu128` 版本镜像进行适配与部署。

### 1) 直接使用 docker compose

```bash
docker compose up -d
```

默认会启动两个服务:

- **gpt-sovits-bot**: GPT-SoVITS 推理 API（端口 9880）
- **webui**: Gradio WebUI（端口 7860）

### 2) 访问地址

- WebUI: `http://localhost:7860`

### 3) WebUI 镜像构建

WebUI 容器使用 `Dockerfile.webui` 构建，基础镜像来自 `xxxxrt666/gpt-sovits`。

如需单独构建:

```bash
docker build -f Dockerfile.webui -t ai-waifu-webui .
```

---

## WebUI 界面介绍

WebUI 由 3 个主要页面组成:

![WebUI Screenshot](image.png)

### 1) 聊天模式

- 支持文字输入与麦克风语音输入  
- 对话内容实时显示在聊天窗口  
- AI 回复会自动进行语音合成  
- 可调节语音参数:
  - 语速 (Speed)
  - 情感波动 (Temperature)
  - 句间停顿 (Pause Delay)
  - Top-K / Top-P

### 2) 历史记录

目前为占位页面，后续可扩展数据库存储与检索功能。

### 3) 系统设置

用于快速查看或修改 DeepSeek Key、参考音频路径等配置（当前为模拟保存）。

---

## 项目结构（核心文件）

```
.
├─ webui.py               # WebUI 主入口
├─ Dockerfile.webui       # WebUI 镜像构建
├─ docker-compose.yaml    # GPT-SoVITS + WebUI 组合部署
├─ requirements_webui.txt # WebUI 依赖
├─ asset/                 # 参考音频
└─ avatar.png             # 聊天头像
```

---

## 说明

本项目是我学习docker和TTS过程的一个产物（很简陋而且没有整理）。最好只作为参考学习用。  
音频训练使用了GPT-SoVITS项目完成，训练后模型为`BlueArchive_meidai_e15_s660.pth`与`BlueArchive_meidai-e25.ckpt`，放置在`GPT_SoVITS/pretrained_models`目录下。

### 模型下载与运行准备

两个训练模型已上传至 [GitHub Release v1.0-models](https://github.com/xiaoye-learner/ai_bot/releases/tag/v1.0-models)，附带 `SHA256SUMS.txt` 校验文件。模型目录由 `.gitignore` 忽略，克隆仓库或下载源码压缩包不会包含模型，需要另外准备。

首次部署前，请在项目根目录运行（需要 Python 3.9 或更高版本）：

```bash
python tools/prepare_models.py --with-base
```

脚本会下载两个训练模型和所需的 HuBERT、RoBERTa、v2Pro 说话人编码器，校验大小及 SHA-256，并从 `GPT_SoVITS/configs/tts_infer.example.yaml` 生成本地推理配置 `tts_infer.yaml`。已有配置保留，已有模型校验通过后跳过。若已有完整底模，可省略 `--with-base`；无需下载所有版本的底模。

复制 `.env.example` 为 `.env`，填写 `DEEPSEEK_API_KEY`，Docker Compose 会将它传给 WebUI。本地直接运行 Python 客户端时，需要设置同名环境变量，程序不会自动读取 `.env`。

启动前可检查文件：

```bash
python tools/prepare_models.py --check
```

完成以上准备后，再按前面的 Docker 部署步骤启动。手动下载、镜像地址和配置说明见 [模型说明](docs/models.md)，文件清单见 [models.json](docs/models.json)。

如需完整训练与底模能力，请参考 GPT-SoVITS 原项目文档。

测试环境显卡: RTX 5060。

---

## License

本项目遵循原 GPT-SoVITS 协议与依赖项授权协议，请在使用前自行确认。  
