# 手动构建 OA 容器镜像（不部署）

## 边界

工作流：`.github/workflows/manual-container-images.yml`。
只有 `workflow_dispatch` 入口，没有 push、PR、定时或部署触发器。
提交或合并此文件不会自动构建镜像，更不会连接 ECS。
不读取生产数据库、附件、Zeabur 环境变量或服务器密钥。

## 审查和操作

1. 人工审查并合并 PR 后，工作流才会显示标准的 Run workflow 入口。
2. GitHub 仓库 → Actions → Manual OA container images → Run workflow。
3. 首次保留 `publish=false`：只在临时 runner 构建前后端镜像，不上传。
4. 核对日志后，需要另行批准发布时，选择默认分支并勾选 `publish=true`。
5. 查看运行摘要中的镜像标签与 registry digest。不要用构建成功代替业务验收。

发布使用本次任务的 `GITHUB_TOKEN`，无需录入个人 PAT；权限为 contents:read、
packages:write（仅镜像任务）。workflow 未执行前不产生该运行令牌。
构建任务使用 GitHub 托管 runner，可能占用账号 Actions 和 Packages 配额，
运行前应查看账号当前用量。工作流不购买任何云产品。

镜像名：`ghcr.io/zlz1995/oa-backend`、`ghcr.io/zlz1995/oa-frontend`。
标签：`sha-<完整提交SHA>-<运行ID>-<重跑次数>`；不发布 `latest`。
两份镜像都构建成功后才开始推送，但两次推送不是事务：第二份失败时第一份可能已发布。
只有两份都成功且摘要有 digest，才可以将它们作为一套候选版本。

新 GHCR package 默认私有；发布前拒绝已经可见且不是 private 的同名 package，
不自动改变 package 可见性。首次发布后仍需人工核对两份 package 为 Private，
不要将其改成 Public。API 返回 404 也可能表示无权访问现有包，推送可能因此失败；
此时先检查包的仓库关联与权限，不要扩大账号权限来绕过。

## 构建隔离与旧系统兼容

`scripts/ci/prepare_image_contexts.py` 在 runner 临时目录准备白名单构建上下文。
保留原有 Dockerfile 和应用入口；不修改旧 Zeabur 部署文件。
后端只包含运行代码、迁移定义、依赖、启动脚本和智能客服使用说明书。
前端包含源码、锁文件和 public 资源；环境文件、数据库、私钥等不从源码复制。
public 中原有培训手册仍包含在镜像中，因此必须保持镜像私有。

新前端上下文单独生成 `VITE_API_BASE_URL=/api/v1`，不继承旧 Zeabur 地址。
上线前必须配置同源反向代理，将 `/api/v1` 转发到后端；当前流程不配置代理。
镜像使用现有 Dockerfile 的 Python 3.11 和 Node 20 基础镜像，不在本 PR 中升级运行时。
基础镜像及部分前端依赖是浮动版本；相同源码重新构建不保证字节一致。
发布后应使用运行摘要中的 digest 固定部署版本，并在上线前做依赖安全检查。

## 验证与后续

本地检查：`python -m unittest discover -s scripts/ci -p 'test_*.py' -v`。
首次手动构建用于验证 Dockerfile、依赖下载及真实镜像构建，目前不能宣称已通过。
首次发布后需另行配置服务器只读拉取凭证，并实际验证镜像下载；接口可达并不等于
完整镜像层能下载。不得把凭证写入仓库、聊天、命令参数或截图。
本 PR 不执行发布、不生成服务器凭证、不迁移业务、不启动应用、不修改 DNS。
ICP备案完成和迁移验收仍是独立流程。

参考：
- https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry
- https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow
