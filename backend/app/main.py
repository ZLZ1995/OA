import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.api.router import api_router
from app.core.config import settings
from app.db.init_db import init_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialize database objects and seed basic data on startup."""
    try:
        init_db()
        logger.info("Database initialized successfully.")
    except Exception as exc:
        logger.exception("Database initialization failed during startup: %s", exc)
        if settings.db_init_required:
            raise
        logger.warning(
            "Continue startup without database initialization because DB_INIT_REQUIRED is false."
        )
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/", response_class=HTMLResponse)
def root() -> str:
    return """
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>登录 - 资产评估项目流程管理系统</title>
    <style>
      body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f1220; color: #fff; display: grid; place-items: center; min-height: 100vh; margin: 0; }
      .card { width: min(420px, 92vw); background: #1b1f36; border-radius: 14px; padding: 24px; box-shadow: 0 10px 30px rgba(0,0,0,.35); }
      h1 { margin-top: 0; font-size: 22px; }
      label { display: block; margin: 12px 0 6px; font-size: 14px; color: #c9ccea; }
      input { width: 100%; box-sizing: border-box; padding: 10px 12px; border-radius: 10px; border: 1px solid #3b426f; background: #13172a; color: #fff; }
      button { margin-top: 16px; width: 100%; padding: 10px; border: 0; border-radius: 10px; background: #6f4bff; color: #fff; font-size: 15px; cursor: pointer; }
      .msg { margin-top: 12px; font-size: 14px; color: #c9ccea; white-space: pre-wrap; }
    </style>
  </head>
  <body>
    <div class="card">
      <h1>登录系统</h1>
      <label>用户名</label>
      <input id="username" placeholder="admin" value="admin" />
      <label>密码</label>
      <input id="password" type="password" placeholder="请输入密码" />
      <button onclick="login()">登录</button>
      <div class="msg" id="msg">请输入账号密码后点击登录。</div>
    </div>

    <script>
      async function login() {
        const username = document.getElementById('username').value.trim();
        const password = document.getElementById('password').value;
        const msg = document.getElementById('msg');
        msg.textContent = '正在登录...';

        try {
          const resp = await fetch('/api/v1/auth/login', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ username, password })
          });

          const data = await resp.json();
          if (!resp.ok) {
            msg.textContent = '登录失败：' + (data.detail || JSON.stringify(data));
            return;
          }

          localStorage.setItem('access_token', data.access_token || '');
          msg.textContent = '登录成功，正在跳转...';
          window.location.href = '/dashboard';
        } catch (e) {
          msg.textContent = '登录失败：' + e;
        }
      }
    </script>
  </body>
</html>
"""


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard() -> str:
    return """
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>主界面 - 资产评估项目流程管理系统</title>
    <style>
      body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f1220; color: #fff; margin: 0; padding: 24px; }
      .card { width: min(720px, 96vw); margin: 0 auto; background: #1b1f36; border-radius: 14px; padding: 24px; box-shadow: 0 10px 30px rgba(0,0,0,.35); }
      h1 { margin-top: 0; font-size: 24px; }
      button { margin-right: 8px; padding: 8px 14px; border: 0; border-radius: 8px; background: #6f4bff; color: #fff; cursor: pointer; }
      pre { background: #13172a; border: 1px solid #3b426f; border-radius: 10px; padding: 12px; white-space: pre-wrap; word-break: break-word; }
      .muted { color: #c9ccea; }
    </style>
  </head>
  <body>
    <div class="card">
      <h1>主界面</h1>
      <p class="muted">已从登录页跳转。当前页面会使用 localStorage 中的 Token 调用 <code>/api/v1/auth/me</code> 进行验证。</p>
      <div>
        <button onclick="loadMe()">刷新当前用户</button>
        <button onclick="logout()">退出登录</button>
      </div>
      <pre id="output">正在加载...</pre>
    </div>
    <script>
      async function loadMe() {
        const output = document.getElementById('output');
        const token = localStorage.getItem('access_token') || '';
        if (!token) {
          output.textContent = '未检测到 access_token，请先登录。';
          return;
        }
        try {
          const resp = await fetch('/api/v1/auth/me', {
            headers: { Authorization: 'Bearer ' + token }
          });
          const data = await resp.json();
          if (!resp.ok) {
            output.textContent = '获取用户信息失败：' + (data.detail || JSON.stringify(data));
            return;
          }
          output.textContent = '当前登录用户信息：\\n' + JSON.stringify(data, null, 2);
        } catch (e) {
          output.textContent = '请求失败：' + e;
        }
      }

      function logout() {
        localStorage.removeItem('access_token');
        window.location.href = '/';
      }

      loadMe();
    </script>
  </body>
</html>
"""
