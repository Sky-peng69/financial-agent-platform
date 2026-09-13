# 弈金免费部署方案

目标：让外部用户可以像本地 `http://127.0.0.1:3001/dashboard` 一样访问产品。

## 推荐方案

先按公开 Demo 部署，不按正式生产系统部署：

- 前端：Netlify Free，部署 `frontend`。
- 后端：Render Free Web Service，使用 `backend/Dockerfile`。
- 数据库：首选 Render Free Postgres 快速跑通；如需长期保留数据，改用 Supabase/Neon 等免费 Postgres。
- Redis/Worker：当前代码没有真正使用 Redis 队列，第一版可以不部署。
- 文件存储：当前使用 Render 本地文件系统，免费实例重启或重新部署后上传原文件和导出文件可能丢失；数据库里的解析文本、任务和报告记录仍保留。正式公开使用前应接 S3/R2/Supabase Storage。

## 需要准备

1. 一个 GitHub 仓库。
2. Render 账号。
3. Netlify 账号。
4. DeepSeek API Key，否则登录和界面可用，但 AI 分析会失败。

## 后端部署到 Render

### 方式 A：使用仓库里的 `render.yaml`

1. 把仓库推到 GitHub。
2. Render Dashboard 选择 New -> Blueprint。
3. 连接 GitHub 仓库。
4. 选择本仓库根目录的 `render.yaml`。
5. 设置环境变量：
   - `DEEPSEEK_API_KEY`：你的 DeepSeek Key。
   - `ENVIRONMENT`：保持 `demo`，这样开发体验入口可用。
   - `DEBUG`：`false`。
   - `SECRET_KEY`：让 Render 自动生成或手动设置长随机字符串。
   - `FRONTEND_URL`：先临时填 Netlify 预计域名，前端部署后再改成真实 URL。
6. 部署完成后打开：
   - `https://<你的后端服务名>.onrender.com/health`
   - 正常应返回 `{"status":"ok","service":"金融 Agent 平台"}`。

### 方式 B：手动创建 Render Web Service

1. Render Dashboard 选择 New -> Web Service。
2. 连接 GitHub 仓库。
3. Runtime 选择 Docker。
4. Dockerfile Path 设置为：
   - `./backend/Dockerfile`
5. Docker Context 设置为：
   - `./backend`
6. 添加 Postgres 数据库，把数据库连接串填入：
   - `DATABASE_URL`
7. 添加同方式 A 的其他环境变量。

## 前端部署到 Netlify

1. Netlify 选择 Add new site -> Import an existing project。
2. 连接 GitHub 仓库。
3. Base directory 设置为：
   - `frontend`
4. Build command 设置为：
   - `npm run build`
5. Publish directory 设置为：
   - `.next`
6. 添加环境变量：
   - `NEXT_PUBLIC_API_URL=https://<你的后端服务名>.onrender.com`
   - 这个变量必须在 Netlify 构建前设置；否则前端会默认请求本地 `http://localhost:8001`。
7. 部署后得到前端 URL，例如：
   - `https://<你的站点名>.netlify.app`
8. 回到 Render 后端，把 `FRONTEND_URL` 改成这个 Netlify URL，然后重新部署后端。

## 上线后验证

1. 打开 `https://<你的站点名>.netlify.app/login`。
2. 使用开发体验入口或注册新用户。
3. 进入 `/dashboard`。
4. 上传一个小 PDF。
5. 发起一次 AI 分析。
6. 确认页面能显示流式进度和最终报告。
7. 打开 Render 后端 `/health`，确认仍可访问。

## 免费方案限制

- Render Free Web Service 空闲 15 分钟后会休眠，首次访问可能要等约 1 分钟。
- Render Free Postgres 只有 1GB，且 30 天后过期；不适合长期用户数据。
- Render Free Web Service 没有持久磁盘，上传原文件和导出文件可能在重启、重新部署或休眠后丢失。
- Netlify Free 有免费额度，适合小流量 Demo。
- DeepSeek API 调用不是免费的，实际 AI 分析成本取决于你的 Key 用量。

## 最小可用结论

如果只是让评委、朋友或少量试用用户体验：

```text
Netlify 前端 + Render 后端 + Render Postgres
```

如果希望用户数据至少能较长期保留：

```text
Netlify 前端 + Render 后端 + Supabase/Neon Postgres + S3/R2/Supabase Storage
```

第二套方案需要改造当前 `LocalStorage`，不建议在第一次上线前临时硬改。
