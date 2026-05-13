# Students Test Essay Backend

小学语文作文批改后端和 Android 前端 MVP。

后端使用 FastAPI，支持创建作文模板、上传作文图片、调用 OCR 和大模型批改，并把模板和批改记录保存到 SQLite。

Android 前端位于 `android/`，使用 Kotlin + Jetpack Compose。APK 构建放在 GitHub Actions 执行，本地不需要安装 Android SDK。

## 后端接口

- `GET /health`
- `POST /api/v1/essay-templates`
- `GET /api/v1/essay-templates`
- `POST /api/v1/essay-corrections`
- `GET /api/v1/essay-corrections/{correction_id}`

推荐前端流程：

```text
1. 创建模板：POST /api/v1/essay-templates
2. 进入模板详情
3. 在模板内拍照或选图
4. 批改时提交 template_id + image
5. 保存 correction id，用于查看批改详情或历史记录
```

## Docker 部署后端

服务器项目根目录准备 `.env`：

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

SQLite 数据保存在宿主机：

```text
./data/essay_backend.sqlite3
```

## Android App

当前功能：

```text
1. 查看模板列表
2. 新建模板
3. 进入模板详情
4. 从相册选图或调用相机拍照
5. 上传 template_id + image 到后端批改
6. 展示 OCR 文本、总分、分项分、评语、问题、建议、修改示例和老师备注
```

默认后端地址写在：

```text
android/app/src/main/java/com/studentstest/essay/MainActivity.kt
```

## GitHub 构建 APK

工作流：

```text
.github/workflows/android.yml
```

触发方式：push、pull request 或手动 `workflow_dispatch`。

下载路径：

```text
GitHub 仓库 -> Actions -> Android -> 最近一次成功运行 -> Artifacts -> students-essay-debug-apk
```

下载后解压，安装 `app-debug.apk`。

## 本地测试后端

```bash
UV_CACHE_DIR=/tmp/uv-cache uv sync --extra dev
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -v
```

## 安全说明

`.env`、本地数据库和真实学生图片都被 `.gitignore` 排除。不要把真实讯飞密钥或大模型 API Key 提交到仓库。
