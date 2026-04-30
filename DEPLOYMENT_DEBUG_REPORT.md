# GitHub main vs Zeabur 前端不一致排查报告

日期：2026-04-30（UTC）

## 1) Git 状态
- 当前分支：`work`（不是 `main`）。
- 最近提交：`4e4e151`（Merge PR #63）。
- 本地存在未跟踪目录：`frontend/node_modules/`。
- 当前仓库未配置任何 remote（`git remote -v` 为空），因此无法在本地直接验证 `origin/main` 的远程状态。

## 2) 关键功能在代码中的真实状态

### 已存在
- 路由包含 `/projects/:id/flow`，并存在 `ProjectFlowView.vue` 页面。
- 登录后有管理员去 `/accounts`、非管理员去 `/dashboard` 的逻辑。
- 后端 `/api/v1/workbench` 返回 `my_projects` 与 `todo_projects`。

### 不满足预期（关键）
- `MainMenu` 仍然引用 `APP_MENUS`，普通业务用户仍能看到：项目管理/工单管理/项目成员/报告审核/报告版本/文印室管理/财务管理/归档管理。
- `HomeView.vue` 的“进入项目”仍跳转 `/projects/:id`，并未统一跳转 `/projects/:id/flow`。
- `HomeView.vue` 的项目创建区没有“项目编号：系统自动生成”的只读占位提示。
- `ProjectFlowView.vue` 当前为单卡片 + 步骤条，不是“左侧流程导航 + 右侧办理流程图”的布局。

结论：你描述的“最新项目工作台改造”并未完整体现在当前代码中。

## 3) 旧菜单是否仍被引用
- `frontend/src/constants/menus.ts` 中仍定义旧菜单项。
- `frontend/src/components/common/MainMenu.vue` 直接消费 `APP_MENUS`。
- 路由仍保留旧业务页路由（projects/workorders/reviews/...）。

因此线上出现旧菜单，不一定是 Zeabur 缓存；更可能是当前代码本身仍保留旧菜单并被主布局继续使用。

## 4) 构建验证
在 `frontend` 执行：
- `npm install`
- `npm run build`

结果：构建通过，且产物中存在：
- `HomeView-*.js`
- `ProjectFlowView-*.js`

同时产物中仍可检索到旧菜单字符串，印证当前代码行为确实会渲染旧菜单。

## 5) 部署链路配置检查
- 根目录 `Dockerfile` 仅用于后端（Python + backend requirements + start）。
- `frontend/Dockerfile` 为前端构建与静态托管（Node build + serve dist）。

若 Zeabur 前端服务误用根目录 `Dockerfile`，将不会构建前端；
若前端服务使用 `frontend/Dockerfile`，其 `COPY . .` 会复制 frontend 目录全部源码，不存在“只复制旧文件”的路径错误。

## 6) 结论与建议
1. 不能仅依据 GitHub compare 文案断定“你期待的 UI 改造全部已在 main”。当前本地 HEAD 代码仍保留旧菜单逻辑。 
2. Zeabur 线上旧菜单很可能与当前代码一致（并非单纯缓存导致）。
3. 先确认 Zeabur 前端服务绑定分支是 `main`，且构建上下文是 `frontend/`，Dockerfile 是 `frontend/Dockerfile`。
4. 触发一次 **Rebuild without cache**，并在浏览器 Network 验证 `index-*.js` / `HomeView-*.js` / `ProjectFlowView-*.js` hash 是否更新。
5. 若 hash 已更新但页面仍旧，说明部署成功但代码本身未实现你预期的菜单/跳转/布局，需要补齐对应改造提交。
