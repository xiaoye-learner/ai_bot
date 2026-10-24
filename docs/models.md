# 模型与推理配置

## 为什么 GitHub 目录里只有 .gitignore

`GPT_SoVITS/pretrained_models/.gitignore` 忽略整个模型目录，仅保留它自身。底模来自安装包或另外下载，角色权重来自训练；这些本地文件没有进入 Git 提交历史。

角色权重现在通过 [v1.0-models Release](https://github.com/xiaoye-learner/ai_bot/releases/tag/v1.0-models) 分发。普通 Git 提交不保存大模型文件。

## 自动准备

在项目根目录运行：

```bash
python tools/prepare_models.py --with-base
python tools/prepare_models.py --check
```

脚本不安装 Python 包，不加载权重执行推理，也不修改已有推理配置。`--check` 只检查文件，不创建目录或下载文件。SHA-256 和大小来自 [models.json](models.json)。

## 手动准备

1. 从 Release 下载两个 `BlueArchive_*` 模型和 `SHA256SUMS.txt`，核对 SHA-256 后将模型放入 `GPT_SoVITS/pretrained_models/`。
2. 从 [固定版本的上游模型仓库](https://huggingface.co/lj1995/GPT-SoVITS/tree/8f8857563c040d542de108a2c18b0425abd6c9c5) 下载下表文件，保留相同子目录结构。
3. 复制 `GPT_SoVITS/configs/tts_infer.example.yaml` 为同目录的 `tts_infer.yaml`。样例指向美代模型，版本为 `v2Pro`、设备为 `cuda`。
4. 运行 `python tools/prepare_models.py --check`。

| 上游文件（相对 pretrained_models） | 用途 |
| --- | --- |
| `chinese-hubert-base/config.json` | HuBERT 配置 |
| `chinese-hubert-base/preprocessor_config.json` | 音频预处理配置 |
| `chinese-hubert-base/pytorch_model.bin` | HuBERT 权重 |
| `chinese-roberta-wwm-ext-large/config.json` | RoBERTa 配置 |
| `chinese-roberta-wwm-ext-large/tokenizer.json` | 分词器 |
| `chinese-roberta-wwm-ext-large/pytorch_model.bin` | RoBERTa 权重 |
| `sv/pretrained_eres2netv2w24s4ep4.ckpt` | v2Pro 说话人编码器 |

本套模型无需安装目录中的 v1、v2、v3 等全部底模，也无需 BigVGAN。训练或切换其他版本时，按 GPT-SoVITS 官方说明另外准备相应资源。Whisper、语言处理字典等运行时资源不在本清单内。

## 校验与配置注意事项

Linux 可在下载目录运行 `sha256sum -c SHA256SUMS.txt`；PowerShell 可使用 `Get-FileHash 文件路径 -Algorithm SHA256` 与清单对照。

`tts_infer.yaml` 是运行时可修改的本地配置，继续由 Git 忽略；提交的是 `tts_infer.example.yaml`。修改样例后，已有配置不会自动更新，需要手动同步。文件存在和模型校验通过不代表配置路径或 GPU 环境一定正确，实际加载以 TTS 日志为准。

Compose 使用当前目录挂载，并直接启动 `api_v2.py`，不会执行基础镜像的默认模型目录初始化命令，也不会自动运行安装脚本。不要仅依赖镜像内的文件代替宿主机准备。

替换角色时应同时准备匹配的 GPT/SoVITS 模型，并修改 `tts_infer.yaml` 中的 `t2s_weights_path`、`vits_weights_path`、`version`，以及 `webui.py` 中的参考音频和文本。
