# Students Test Essay Backend

小学语文作文批改后端 MVP。当前版本先稳定接口合同：上传作文图片和作文要求，后端返回 OCR 文本、分项评分和结构化评语。OCR 和批改模型都通过 provider 抽象接入，默认使用可测试的 mock/deterministic provider，后续可替换为真实中文手写 OCR 和大模型。

仓库同时包含一个 Android 前端 MVP，位于 `android/`，使用 Kotlin + Jetpack Compose。APK 构建放在 GitHub Actions 执行，本地不需要安装 Android SDK。

## 功能

- `POST /api/v1/essay-templates`
  - 创建作文批改模板
  - 保存作文题目、作文要求、年级、作文类型
  - 返回 `tpl_...` 模板 ID
- `GET /api/v1/essay-templates`
  - 返回已创建模板列表
- `POST /api/v1/essay-corrections`
  - `multipart/form-data`
  - 推荐字段：`image`、`template_id`
  - 兼容字段：`image`、`title`、`requirements`、`grade_level`、`essay_type`
  - 返回：`ocrText`、总分、五项分数、总评、亮点、问题、修改建议、错别字问题、语句问题、修改示例、老师备注、鼓励性评语
  - 批改结果会写入本地 SQLite，后续可按 ID 查询
- `GET /api/v1/essay-corrections/{correction_id}`
  - 返回指定批改记录
- `GET /health`

## Android App

Android 工程目录：

```text
android/
```

当前 App 功能：

```text
1. 查看服务器上的作文模板列表
2. 新建作文模板
3. 进入模板详情
4. 从相册选图或调用相机拍照
5. 上传 template_id + image 到后端批改
6. 展示 OCR 文本、总分、分项分、评语、问题、建议、修改示例和老师备注
```

当前默认后端地址写在：

```text
android/app/src/main/java/com/studentstest/essay/MainActivity.kt
```

默认值：

```kotlin
private const val API_BASE_URL = "http://8.154.34.227:8000"
```

如果后面换域名或 HTTPS，改这里即可。

### GitHub 构建 APK

Android APK 构建工作流：

```text
.github/workflows/android.yml
```

触发方式：

```text
push 到 main/master
pull request 到 main/master
手动 workflow_dispatch
```

GitHub Actions 会构建 Debug APK，并上传 artifact：

```text
students-essay-debug-apk
```

下载路径：

```text
GitHub 仓库 -> Actions -> Android -> 最近一次成功运行 -> Artifacts -> students-essay-debug-apk
```

下载后解压，里面是：

```text
app-debug.apk
```

把 APK 发到手机上安装即可。首次安装需要允许“安装未知来源应用”。

### Android 构建命令

GitHub Actions 内部执行：

```bash
gradle -p android :app:assembleDebug
```

本地没有 Android SDK 时不需要运行这条命令。

## 本地运行

```bash
UV_CACHE_DIR=/tmp/uv-cache uv sync --extra dev
UV_CACHE_DIR=/tmp/uv-cache uv run uvicorn backend.app.main:app --reload
```

访问：

```text
http://127.0.0.1:8000/docs
```

## Docker 部署

服务器只需要安装 Docker 和 Docker Compose 插件，然后在项目根目录准备 `.env`：

```env
ESSAY_OCR_PROVIDER=xfyun_ocr
ESSAY_XFYUN_APP_ID=你的APPID
ESSAY_XFYUN_API_KEY=你的APIKey
ESSAY_XFYUN_API_SECRET=你的APISecret
ESSAY_XFYUN_ENDPOINT=https://cbm01.cn-huabei-1.xf-yun.com/v1/private/se75ocrbm

ESSAY_GRADER_PROVIDER=openai_compatible
ESSAY_LLM_BASE_URL=https://sub.kedaya.xyz
ESSAY_LLM_API_KEY=你的APIKey
ESSAY_LLM_MODEL=gpt-5.4-mini
```

启动：

```bash
docker compose up -d --build
```

查看日志：

```bash
docker compose logs -f
```

访问：

```text
http://服务器IP:8000/docs
```

停止：

```bash
docker compose down
```

后续更新代码：

```bash
git pull
docker compose up -d --build
```

Docker 容器内仍使用 SQLite，数据库挂载在宿主机：

```text
./data/essay_backend.sqlite3
```

只要不删除宿主机的 `data` 目录，重建容器不会丢模板和批改历史。

## 推荐前端流程

```text
1. 创建模板：POST /api/v1/essay-templates
2. 模板列表/详情页保存返回的 template id
3. 用户进入模板后拍照
4. 批改时只提交 template_id + image
5. 批改完成后保存 correction id，用于进入批改详情或历史记录
```

## 本地数据

模板和批改记录默认保存在本地 SQLite：

```text
data/essay_backend.sqlite3
```

该数据库文件已被 `.gitignore` 忽略，不会提交到 GitHub。删除这个文件会清空本地模板和批改历史。

## 示例请求

创建模板：

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/essay-templates" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "一次难忘的春游",
    "requirements": "围绕春游经历写清楚事情经过，语句通顺，有真情实感。",
    "grade_level": "小学三年级",
    "essay_type": "命题作文"
  }'
```

在模板内拍照后批改：

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/essay-corrections" \
  -F "template_id=tpl_xxx" \
  -F "image=@/path/to/essay.jpg"
```

查询批改详情：

```bash
curl "http://127.0.0.1:8000/api/v1/essay-corrections/corr_xxx"
```

## 测试

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -v
```

## Provider 配置

默认配置：

```text
ESSAY_OCR_PROVIDER=mock
ESSAY_GRADER_PROVIDER=deterministic
```

可选 OCR provider：

```text
mock       默认模拟 OCR，适合前端联调和 CI
imgocr     本地 imgocr，需安装 OCR 可选依赖
xfyun_ocr  讯飞通用文档识别 OCR 大模型
```

讯飞 OCR 配置：

```bash
ESSAY_OCR_PROVIDER=xfyun_ocr
ESSAY_XFYUN_APP_ID=你的APPID
ESSAY_XFYUN_API_KEY=你的APIKey
ESSAY_XFYUN_API_SECRET=你的APISecret
```

讯飞接口默认地址：

```text
https://cbm01.cn-huabei-1.xf-yun.com/v1/private/se75ocrbm
```

如需覆盖：

```bash
ESSAY_XFYUN_ENDPOINT=https://cbm01.cn-huabei-1.xf-yun.com/v1/private/se75ocrbm
```

本地 imgocr 可选依赖：

```bash
UV_CACHE_DIR=/tmp/uv-cache uv sync --extra dev --extra ocr
```

当前批改 provider 仍为：

```text
deterministic
```

可选批改 provider：

```text
deterministic       默认模拟批改，适合前端联调和 CI
openai_compatible  OpenAI 兼容 Chat Completions 接口
```

OpenAI 兼容批改配置：

```bash
ESSAY_GRADER_PROVIDER=openai_compatible
ESSAY_LLM_BASE_URL=https://your-openai-compatible-host
ESSAY_LLM_API_KEY=你的APIKey
ESSAY_LLM_MODEL=gpt-5.4-mini
```

后端会调用：

```text
{ESSAY_LLM_BASE_URL}/v1/chat/completions
```

并要求模型返回结构化 JSON：

```json
{
  "score": {
    "total": 0,
    "content": 0,
    "structure": 0,
    "language": 0,
    "mechanics": 0,
    "presentation": 0
  },
  "comments": {
    "summary": "",
    "strengths": [],
    "issues": [],
    "suggestions": [],
    "encouragement": "",
    "spellingIssues": [],
    "sentenceIssues": [],
    "revisionExample": "",
    "teacherNotes": ""
  }
}
```
