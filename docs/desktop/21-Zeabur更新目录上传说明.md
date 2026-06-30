# Zeabur 更新目录上传说明

## 1. 目标
将桌面端热更新文件发布到当前后端服务的持久盘目录：

`/data/desktop-updates/win/stable/`

并通过以下地址对外访问：

`https://zhongqinoa.zeabur.app/desktop-updates/win/stable/`

## 2. 后端已支持的能力
当前后端服务已在 FastAPI 中挂载静态目录：

- URL 前缀：`/desktop-updates`
- 物理目录：`/data/desktop-updates`

因此：

- `/data/desktop-updates/win/stable/latest.yml`
- `/data/desktop-updates/win/stable/release.json`

会分别对应：

- `https://zhongqinoa.zeabur.app/desktop-updates/win/stable/latest.yml`
- `https://zhongqinoa.zeabur.app/desktop-updates/win/stable/release.json`

## 3. 需要上传的文件
本地构建完成后，从以下目录取文件：

`desktop/out-update-publish/`

需要上传：

1. `latest.yml`
2. `release.json`
3. `zhongqin-oa-setup-x.y.z.exe`
4. `zhongqin-oa-setup-x.y.z.exe.blockmap`（可选）

## 4. 服务器目录结构
上传后服务器目录应为：

```text
/data/desktop-updates/
  win/
    stable/
      latest.yml
      release.json
      zhongqin-oa-setup-x.y.z.exe
      zhongqin-oa-setup-x.y.z.exe.blockmap
```

## 5. 推荐上传方式
根据当前 Zeabur 单服务结构，推荐以下方式之一：

1. 使用 Zeabur 提供的终端/文件管理能力进入容器
2. 将文件复制到 `/data/desktop-updates/win/stable/`
3. 若平台无文件管理入口，可在服务中临时增加一次性上传脚本或使用 `curl/wget` 从外部可访问位置拉取文件到 `/data`

### 5.1 当前推荐：本地分片上传脚本
对于 `0.2.1.exe` 这类大文件，若一次性上传持续被 Zeabur 连接重置，建议改用桌面仓库内置的分片上传脚本：

`desktop/scripts/upload-desktop-update-chunks.ps1`

该脚本会自动：

1. 普通上传 `latest.yml`
2. 普通上传 `release.json`
3. 为 `.exe` 与 `.blockmap` 创建分片上传会话
4. 按 `8MB` 分片上传
5. 服务端合并、校验 `sha256` 并落盘到 `/data/desktop-updates/win/stable/`

执行命令：

```powershell
powershell -ExecutionPolicy Bypass -File D:\1\OA-main-routing-pr2\desktop\scripts\upload-desktop-update-chunks.ps1 -AccessToken "管理员token"
```

如需显式指定后端地址：

```powershell
powershell -ExecutionPolicy Bypass -File D:\1\OA-main-routing-pr2\desktop\scripts\upload-desktop-update-chunks.ps1 -AccessToken "管理员token" -BackendBaseUrl "https://zhongqinoa.zeabur.app"
```

注意：

1. 使用前必须先把后端最新代码部署到 Zeabur
2. 该脚本依赖后端新增的分片接口：
   - `POST /api/v1/desktop-updates/upload-session`
   - `POST /api/v1/desktop-updates/upload-chunk`
   - `POST /api/v1/desktop-updates/upload-complete`

## 6. 上传前准备
先确保目录存在：

```sh
mkdir -p /data/desktop-updates/win/stable
```

再把 4 个文件复制进去。

## 7. 上传后验证
至少验证以下地址：

1. `https://zhongqinoa.zeabur.app/desktop-updates/win/stable/latest.yml`
2. `https://zhongqinoa.zeabur.app/desktop-updates/win/stable/release.json`
3. `https://zhongqinoa.zeabur.app/desktop-updates/win/stable/zhongqin-oa-setup-x.y.z.exe`

验证标准：

1. `latest.yml` 浏览器可直接打开
2. `release.json` 浏览器可直接打开
3. `.exe` 可直接下载
4. `.blockmap` 若返回 `404`，本次发布仍可视为“整包更新可上线”

## 8. 客户端验证
上传完成后，用已安装旧版桌面客户端执行：

1. 打开客户端
2. 点击“帮助 -> 检查更新”
3. 确认客户端发现更高版本号
4. 确认可下载并提示重启安装

## 9. 后续发版规则
下一个版本发布时：

1. 先递增 `desktop/package.json` 版本号
2. 重新执行 `npm.cmd run publish:official`
3. 用新版本文件覆盖 `stable/` 目录中的 `latest.yml`、`release.json`、`.exe`
4. `.blockmap` 若上传成功则一并覆盖；若上传失败，可记录为“差量更新未发布”
5. 若 `.exe` 普通上传失败，优先改用 `upload-desktop-update-chunks.ps1`
