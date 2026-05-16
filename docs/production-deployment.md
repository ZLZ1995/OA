# 生产部署手册

本文档用于 `OA-main` 的生产部署。当前云端约束必须保留：后端使用仓库根目录 `Dockerfile` 和 `./start`，前端服务根目录使用 `/frontend` 与 `frontend/Dockerfile`。

## 服务拓扑

| 服务 | 部署根目录 | Dockerfile | 入口 | 说明 |
| --- | --- | --- | --- | --- |
| 后端 API | 仓库根目录 | `Dockerfile` | `./start` | FastAPI，默认监听 `PORT` 或 8080 |
| 前端 Web | `/frontend` | `frontend/Dockerfile` | 镜像默认命令 | Vite 构建后静态托管 `dist` |
| 数据库 | 云平台持久化卷或外部数据库 | 不适用 | 不适用 | 当前默认 SQLite，可迁移到 PostgreSQL |
| 上传文件 | 后端持久化卷 | 不适用 | 不适用 | 必须挂载持久化目录，避免重部署丢文件 |

## 环境变量清单

| 变量 | 默认值 | 必填 | 用途 |
| --- | --- | --- | --- |
| `PORT` | `8080` | 否 | 容器监听端口，云平台通常自动注入 |
| `PYTHONUNBUFFERED` | `1` | 否 | 后端日志实时输出 |
| `PYTHONDONTWRITEBYTECODE` | `1` | 否 | 避免容器内生成 `.pyc` |
| `DATABASE_URL` | `sqlite:////data/app.db` | 是 | 生产数据库连接，SQLite 必须放在持久化卷 |
| `DB_INIT_REQUIRED` | `true` | 否 | 首次部署或迁移时初始化数据库结构 |
| `LOCAL_STORAGE_DIR` | `/data/uploads` | 建议 | 上传文件持久化目录 |
| `INITIAL_ADMIN_USERNAME` | 配置默认值 | 首次部署必填 | 初始超级管理员账号 |
| `INITIAL_ADMIN_PASSWORD` | 配置默认值 | 首次部署必填 | 初始超级管理员密码，上线后应立即修改 |
| `INITIAL_ADMIN_REAL_NAME` | 配置默认值 | 否 | 初始超级管理员显示名 |

## 首次部署步骤

1. 后端服务绑定 `OA-main` 仓库根目录，保留根目录 `Dockerfile` 和启动命令 `./start`。
2. 给后端挂载持久化卷，例如 `/data`，确保 `DATABASE_URL=sqlite:////data/app.db`。
3. 前端服务绑定同一仓库但根目录选择 `/frontend`，使用 `frontend/Dockerfile`。
4. 配置初始管理员变量，部署后立即登录并修改默认密码。
5. 后端启动后检查 `/api/health`，前端打开登录页并确认静态资源 hash 已更新。
6. 创建一个测试项目，走到合同初审或报告送审前停止，确认数据库和上传目录均写入持久化卷。

## 发布前检查

| 检查项 | 命令或方式 | 通过标准 |
| --- | --- | --- |
| 后端测试 | `python -m pytest -q` | 全部通过 |
| 前端类型检查 | `npm run typecheck` | 无类型错误 |
| 前端构建 | `npm run build` | 构建成功 |
| 生成物清理 | `D:\1\cleanup-generated-artifacts.ps1` | dry-run 无残留 |
| 部署文件 | 人工检查 | `Dockerfile`、`start`、`frontend/Dockerfile` 均未移动 |

## 数据备份方案

### SQLite

1. 每次发布前停止后端写入或进入维护窗口。
2. 备份 `/data/app.db` 到带时间戳的位置，例如 `/data/backups/app-YYYYMMDD-HHMM.db`。
3. 同步备份 `/data/uploads`，保持数据库记录和文件对象一致。
4. 恢复时先停止服务，再替换 `app.db` 和 `uploads`，最后启动后端检查 `/api/health`。

### PostgreSQL

1. 使用云厂商自动快照作为基础备份。
2. 发布前执行逻辑备份：`pg_dump "$DATABASE_URL" > backup.sql`。
3. 上传文件仍需单独备份，不能只备份数据库。
4. 恢复演练至少每月一次，确认账号、项目、流程记录、附件下载都可用。

## 回滚方案

1. 保留上一版镜像或上一版 Git commit。
2. 数据库迁移前必须先备份；涉及结构变更时只做前向兼容迁移。
3. 若新版本启动失败，先回滚镜像，再恢复数据库备份。
4. 若只是前端异常，可单独回滚前端服务，不影响后端数据。
