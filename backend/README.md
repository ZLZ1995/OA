# 后端基础工程（FastAPI）

## 技术栈
- FastAPI
- SQLAlchemy 2.x
- Pydantic 2.x
- PostgreSQL
- JWT

## 目录说明
- `app/main.py`: FastAPI 入口
- `app/core/`: 配置与安全组件
- `app/db/`: 数据库会话和初始化
- `app/models/`: ORM 模型（users/roles/user_roles）
- `app/api/v1/`: v1 接口

## 环境变量
在 `backend` 目录下创建 `.env`：

```env
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/asset_flow
JWT_SECRET_KEY=change-this-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=480
INITIAL_ADMIN_USERNAME=admin
INITIAL_ADMIN_PASSWORD=zhongqin123
INITIAL_ADMIN_REAL_NAME=系统管理员
```

## 本地运行
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

## 默认账号
- 用户名: `admin`
- 密码: `zhongqin123`

## 已提供基础 API
- `GET /` 根接口
- `GET /api/v1/health`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
