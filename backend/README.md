# 后端基础工程（FastAPI）

## 目标：最简单、最平稳地上云
默认采用 **内置 SQLite**（单容器即可运行），不强依赖额外部 PostgreSQL。
这样部署时只要把容器跑起来就能工作，避免因为数据库服务编排导致反复重启。
## 技术栈
- FastAPI
- SQLAlchemy 2.x
- Pydantic 2.x
- SQLite（默认） / PostgreSQL（可选）
- JWT

## 目录说明
- `app/main.py`: FastAPI 入口
- `app/core/`: 配置与安全组件
- `app/db/`: 数据库会话和初始化
- `app/models/`: ORM 模型（users/roles/user_roles）
- `app/api/v1/`: v1 接口

## 环境变量（极简）
在 `backend` 目录下创建 `.env`（可选）：

```env
# 不填则默认使用 sqlite:////data/app.db
DATABASE_URL=sqlite:////data/app.db

# 默认 true：启动时创建表并初始化基础数据（推荐保留）
DB_INIT_REQUIRED=true

JWT_SECRET_KEY=change-this-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=480
INITIAL_ADMIN_USERNAME=admin
INITIAL_ADMIN_PASSWORD=zhongqin123
INITIAL_ADMIN_REAL_NAME=系统管理员
```

## 本地运行
> Zeabur 建议直接按 `backend/.env.zeabur.example` 配置平台环境变量，避免遗漏关键项。

## 云上部署（推荐）
### 方式 1：直接用仓库根目录 Dockerfile
- 镜像入口已配置为 `sh ./start`
- 默认监听 `PORT`（平台注入）或回退 `APP_PORT=8080`
- 默认数据库文件在 `/data/app.db`

建议给容器挂载持久化卷到 `/data`，避免重启后数据丢失。

### 方式 2：本地运行
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 从仓库根目录运行（程序名 `start`）
```bash
./start
```

> 云平台（如 Zeabur）通常会注入 `PORT` 环境变量，`start` 脚本已自动读取 `PORT`，避免因为固定端口导致网关 404。
> 若平台按“容器端口 8080”暴露（你截图就是这种），`start` 也会自动回退到 `APP_PORT`（默认 8080）。
> 若云环境数据库尚未就绪，可临时将 `DB_INIT_REQUIRED=false`，服务会先启动并在日志提示数据库初始化失败。
> 数据库就绪后建议设置 `DB_INIT_REQUIRED=true`，确保启动时强校验数据库连通性（Dockerfile 默认值即为 `true`）。
## 默认账号
- 用户名: `admin`
- 密码: `zhongqin123`

## 已提供基础 API
- `GET /` 登录页面（可直接输入账号密码）
- `GET /api/v1/health`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `GET/POST/PATCH /api/v1/users`，`PUT /api/v1/users/{id}/roles`
- `GET /api/v1/roles`
- `GET/POST/PATCH/DELETE /api/v1/projects`
- `GET/POST/PATCH/DELETE /api/v1/work-orders`
- `GET /api/v1/dashboard/mine`
## 阶段1固化文档
- `docs/architecture.md`
- `docs/db-schema.md`
- `docs/workflow-state-machine.md`
- `docs/permission-matrix.md`
