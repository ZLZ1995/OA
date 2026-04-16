# 前端基础工程（阶段3）

## 技术栈
- Vue 3
- Vite
- Element Plus
- Pinia
- Vue Router

## 运行
```bash
cd frontend
npm install
npm run dev
```

## Zeabur 部署（前端服务）
- 根目录：`/frontend`
- 构建命令：`npm install && npm run build`
- 启动命令：`npm run preview -- --host 0.0.0.0 --port 8080`
- 环境变量（关键）：`VITE_API_BASE_URL=https://<你的后端域名>/api/v1`

## Zeabur Docker 部署（推荐）
- 根目录：`/frontend`
- Dockerfile：`frontend/Dockerfile`
- 容器启动后监听：`0.0.0.0:${PORT:-8080}`
- 环境变量（必须）：`VITE_API_BASE_URL=https://<你的后端域名>/api/v1`

## 已完成页面骨架
- 登录页
- 首页工作台
- 项目列表页
- 项目详情页
- 工单列表页
- 工单详情页（配合布局显示流程导览）
- 审核处理页
- 文印室处理页
- 账号管理页

## 响应式布局
- 桌面端：左侧导航 + 中间工作区 + 右侧流程导览
- 平板端：导航折叠 + 右侧流程抽屉
- 手机端：单栏 + 顶部菜单 + 流程抽屉
