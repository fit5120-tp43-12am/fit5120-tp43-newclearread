# Piper 朗读服务使用说明（piper_code2）

本目录提供一层 **业务 API**（`tts_api.py`）和 **简单网页**（`static/index.html`），在后台把文本转发给 **Piper 官方 HTTP 服务**，返回 WAV 供播放或下载。

---

## 1. 你需要准备什么

| 项目 | 说明 |
|------|------|
| Python | 建议使用项目根目录下的虚拟环境 `venv3.10`（或你自建的 3.10+ 环境） |
| Piper | 已 `pip install piper-tts`（或等价安装），能运行 `python -m piper.http_server` |
| **eSpeak NG** | **Windows 上强烈建议安装**；Piper 做英文等语言的音素化时常依赖系统里的 eSpeak NG。可用本仓库提供的安装包或官网 MSI。 |
| 语音模型 | 例如 `en_US-lessac-medium.onnx` 及同目录下的 `.onnx.json`，放在 **`piper_code2\models\`**（与启动命令里的相对路径一致即可） |

### 启动 Piper HTTP（复制即用）

该命令与下文 **§5.1** 中一致。请在已激活虚拟环境后，**先 `cd` 到本目录 `piper_code2`**（保证 `.\models\...` 能找到），再执行：

```powershell
python -m piper.http_server --host 127.0.0.1 --port 5000 --model ".\models\en_US-lessac-medium.onnx"
```

---

## 2. 安装 eSpeak NG（Windows，MSI）

Piper 在合成前会把文字转成音素；在 Windows 上若未正确安装 **eSpeak NG**，可能出现无法合成、异常或行为异常。

### 方式 A：使用仓库里的安装包

若 **`piper_code2`** 目录下已有 **`espeak-ng.msi`**（或你备份的同名文件）：

1. 双击运行 **`espeak-ng.msi`**，按向导完成安装（默认路径一般为 `C:\Program Files\eSpeak NG\`）。
2. 安装结束后**新开**一个终端/PowerShell，再启动 Piper，避免读不到更新后的 PATH。

### 方式 B：从官网下载

若本地没有 MSI，可到 [eSpeak NG Releases](https://github.com/espeak-ng/espeak-ng/releases) 下载 Windows 安装包（`.msi`），安装步骤同上。

### 验证（可选）

在 **新的** PowerShell 中执行：

```powershell
espeak-ng --version
```

能输出版本信息即表示命令已在 PATH 中（若提示找不到命令，可检查安装是否勾选「加入 PATH」，或重启终端/系统）。

---

## 3. Python 依赖

在已激活的虚拟环境中安装（按你实际是否已装可省略）：

```powershell
cd "<你的项目根目录>"
.\venv3.10\Scripts\Activate.ps1
pip install piper-tts flask requests
```

若使用 GPU 加速 Piper，还需按 Piper / ONNX Runtime 文档安装 **`onnxruntime-gpu`** 等（与 `piper.http_server --cuda` 配合）。

---

## 4. 目录与文件说明

| 文件/目录 | 作用 |
|-----------|------|
| `tts_api.py` | Flask 服务：对外提供 `/tts/*`、健康检查、以及首页 `/` 网页 |
| `static/index.html` | 浏览器里粘贴文字、合成并播放 |
| `piper_online.py` | 命令行：把文字发给本机 Piper（5000），写 `output.wav`（见下文用法） |

**`piper_online.py` 用法（需 Piper 已在 5000 运行）：**

```powershell
cd "<你的项目根目录>\piper_code2"
python piper_online.py "Hello world"
# 或从管道读入：
echo 你好 | python piper_online.py
```

---

## 5. 启动服务（必须两步）

需要 **两个终端**，且都建议先 **激活同一虚拟环境**。

### 5.1 终端一：Piper HTTP（默认端口 5000）

在 **`piper_code2`** 目录执行（与 `models` 文件夹同级），**把模型路径改成你的实际路径**：

```powershell
cd "<你的项目根目录>\piper_code2"
..\venv3.10\Scripts\Activate.ps1
python -m piper.http_server --host 127.0.0.1 --port 5000 --model ".\models\en_US-lessac-medium.onnx"
```

- 有 NVIDIA 显卡且已配置好 GPU 版 ONNX Runtime 时，可加 **`--cuda`** 以加快合成。
- 看到 `Running on http://127.0.0.1:5000` 表示成功。**此窗口不要关。**

### 5.2 终端二：业务 API + 网页（默认端口 8080）

```powershell
cd "<你的项目根目录>\piper_code2"
..\venv3.10\Scripts\Activate.ps1
python tts_api.py
```

可选环境变量：

| 变量 | 含义 | 默认 |
|------|------|------|
| `PIPER_SYNTH_URL` | Piper 合成地址（根路径会 POST `/`） | `http://127.0.0.1:5000` |
| `TTS_API_HOST` / `TTS_API_PORT` | 本服务监听地址与端口 | `0.0.0.0` / `8080` |
| `PIPER_TIMEOUT_SEC` | 转发 Piper 的超时（秒） | `300` |

启动成功后，终端会提示在浏览器打开 **`http://127.0.0.1:8080/`**。

---

## 6. 使用网页

1. 浏览器访问：**http://127.0.0.1:8080/**
2. 在文本框中**粘贴或输入**要朗读的内容。
3. 按需填写 **voice**（须与 Piper 已加载或可找到的模型名一致，如 `en_US-lessac-medium`）。
4. **接口路径**（`/tts/full-text`、`/tts/summary`、`/tts/section`）当前实现为**同一套合成逻辑**，仅 URL 不同，便于以后按类型扩展。
5. 点击 **「合成并播放」**，下方播放器可播放返回的 WAV。

**说明：** 页面会等待**整段音频生成完毕**再播放，等待时间主要取决于 Piper 推理（CPU/GPU、模型大小、文本长度），与「网页慢」关系不大。页内「如何加快合成？」有可展开说明。

---

## 7. 使用 HTTP API（脚本 / 后端）

向以下任一地址发送 **`POST`**，**`Content-Type: application/json`**，Body 示例：

```json
{
  "text": "Hello world",
  "voice": "en_US-lessac-medium",
  "length_scale": 1.0
}
```

- **`text`**：必填。
- **`voice`**、**`length_scale`**、**`noise_scale`**、**`noise_w_scale`**、**`speaker`**、**`speaker_id`**：按 Piper 官方 HTTP API 约定选填（多说话人模型才需要 speaker 相关字段）。

### PowerShell 示例（推荐，避免 curl 引号问题）

```powershell
$body = '{"text":"Hello","voice":"en_US-lessac-medium"}'
Invoke-WebRequest -Uri "http://127.0.0.1:8080/tts/full-text" -Method POST -ContentType "application/json; charset=utf-8" -Body $body -OutFile test.wav
```

### 健康检查

```powershell
Invoke-WebRequest -Uri "http://127.0.0.1:8080/health" -UseBasicParsing
```

---

## 8. Piper 官方 HTTP 约定（供对照）

Piper 自带服务的合成接口为 **`POST /`**（不是 `/speak`），请求体为 JSON，核心字段包括 **`text`**、**`voice`** 等。本项目的 `tts_api.py` 将浏览器/脚本的请求**转发**到该地址，并把返回的 **WAV 字节**原样返回给客户端。

---

## 9. 常见问题

| 现象 | 可能原因与处理 |
|------|----------------|
| 合成极慢 | 默认 CPU 推理较慢；Piper 加 `--cuda`，或换更小/更低音质模型；缩短文本。 |
| 浏览器 400 | 请求体缺 `text` 或 JSON 无效；用网页或上面 PowerShell 示例对照。 |
| `test.wav`「损坏」 | 实际保存的是错误 JSON（如 400 响应），应用播放器前确认 HTTP 状态码为 200。 |
| 无法连接 Piper | 确认 5000 上 Piper 已启动；`PIPER_SYNTH_URL` 是否与 Piper 监听地址一致。 |
| 仅 `curl.exe` 异常 | Windows PowerShell 下对 `-d` 的引号处理易错，优先用 **`Invoke-WebRequest`** 或 **`--data-binary "@body.json"`**。 |

---

## 10. 版本与课程说明

本文档随课程项目 `piper_code2` 目录维护；若 Piper / eSpeak NG 升级，安装与命令以官方文档为准。

如有新的路径（例如模型统一放在别的文件夹），只需相应修改 **`python -m piper.http_server --model "<模型.onnx路径>"`** 即可。
