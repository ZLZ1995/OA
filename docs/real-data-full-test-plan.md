# OA系统真实数据全量测试方案

## 1. 目标与范围

本方案面向当前仓库 `D:\1\OA-main` 的本地完整验证，目标不是只验证“接口能通”，而是验证：

1. 功能是否按真实OA业务链路闭环运转。
2. 角色、权限、状态机、待办、通知、日志、文件、导出是否一致。
3. 前后端联调时，页面展示、按钮可见性、接口返回、数据库落库是否一致。
4. 正常流、回退流、拒绝流、并行流、异常流、重复提交流是否都可验证。
5. 本地仓库现有程序在“真实账号 + 真实流程数据 + 真实上传附件 + 真实待办切换”下是否存在死角。

范围覆盖：

1. 前端 `frontend/src/views` 全部业务入口。
2. 后端 `backend/app/api/v1` 全部业务路由。
3. 核心模型：`projects`、`work_orders`、`project_members`、`work_order_files`、`review_records`、`workflow_logs`、`invoices`、`archives`、`notifications`、`reminders` 等。
4. 内部主流程、国资外审扩展流程、签发流程、文印/邮寄/开票/归档流程。
5. 管理端流程：账号、冲突、删除申请、终止审批、问题反馈、导出、通知中心。

不覆盖：

1. 生产部署压测。
2. 云对象存储、真实短信/邮件第三方通道。
3. 安全渗透测试和大规模性能测试。

## 2. 系统实际功能与规则总览

结合代码、路由、模型、测试用例，当前系统实际功能如下。

### 2.1 功能模块

1. 认证与账号
   `auth`、`users`、`roles`、前端登录页、账号管理页。
2. 工作台与待办
   `dashboard`、`workbench`、`notifications`、`ws_notifications`。
3. 项目管理
   `projects`、`project_members`、`project_exports`、项目详情、项目流程页。
4. 工单与状态机
   `work_orders`、`workflow_logs`、`workflow_service`、`project_flow`。
5. 文件与版本
   `files`、`report_versions`、`work_order_files`。
6. 合同初稿与合同审核
   `contract_reviews`、合同上传面板、合同审核面板。
7. 一审/二审/三审/外部复核
   `reviews`、`review_records`。
8. 签发
   `signoff`、首席评估师审批。
9. 文印出具
   `print_room`。
10. 报告邮寄
   `report_mailing`。
11. 财务开票
   `finance`、`invoices`。
12. 归档
   `archives`、`archive_sync_service`。
13. 提醒与催办
   `reminders`、`reminder_policy`、`reminder_service`。
14. 通知中心
   `notifications`、实时通知服务。
15. 项目冲突与问题反馈
   `project_conflicts`、`issue_feedbacks`。
16. 删除申请与终止审批
   `project_delete_requests`、终止审批视图。
17. 帮助中心
   `help/overview`、`help/business-flow`、`help/role-flow`、`help/manual`。

### 2.2 角色矩阵

当前代码和文档中可识别的关键角色：

1. `ADMIN`
2. `PROJECT_LEADER`
3. `PROJECT_MEMBER`
4. `CONTRACT_REVIEWER`
5. `FIRST_REVIEWER`
6. `SECOND_REVIEWER`
7. `THIRD_REVIEWER`
8. `CHIEF_APPRAISER`
9. `PRINT_ROOM`
10. `FINANCE`
11. `ARCHIVE_MANAGER`

说明：

1. 一个账号可绑定多个角色，权限取并集。
2. 前端只做入口和按钮控制，最终以后端校验为准。
3. 管理端路由存在前端拦截，后端接口仍需再次验证越权。

### 2.3 主状态机

核心状态定义在 [states.py](D:/1/OA-main/backend/app/workflows/states.py)。

按业务可归并为以下阶段：

1. 项目创建
   `PROJECT_CREATED`、`WORK_ORDER_CREATED`
2. 合同阶段
   `WAIT_CONTRACT_UPLOAD`、`CONTRACT_UPLOADED`、`WAIT_CONTRACT_REVIEW_SUBMIT`、`CONTRACT_REVIEWING`、`CONTRACT_REJECTED`、`CONTRACT_APPROVED`
3. 内部评审阶段
   `WAIT_FIRST_REVIEW_SUBMIT`、`FIRST_REVIEWING`、`FIRST_REVIEW_REJECTED`
   `WAIT_SECOND_REVIEW_SUBMIT`、`SECOND_REVIEWING`、`SECOND_REVIEW_REJECTED`
   `WAIT_THIRD_REVIEW_SUBMIT`、`THIRD_REVIEWING`、`THIRD_REVIEW_REJECTED`
4. 国资外审扩展阶段
   `THIRD_APPROVED_WAIT_OWNER_CONFIRM_SEND`
   `WAIT_OWNER_EXTERNAL_AUDIT_CONFIRM`
   `WAIT_EXTERNAL_FIRST_REVIEW_SUBMIT` 到 `EXTERNAL_THIRD_REJECTED`
5. 签发与文印阶段
   `WAIT_OWNER_SIGNOFF_UPLOAD`、`SIGNOFF_REVIEWING`、`THIRD_APPROVED_WAIT_PRINTROOM`、`PRINTROOM_PROCESSING`
6. 后续交付阶段
   `PAPER_REPORT_ISSUED`、`REPORT_MAILING`、`REPORT_MAILING_COMPLETED`
   `WAIT_INVOICE_INFO`、`INVOICE_PROCESSING`、`INVOICE_INFO_REJECTED`、`INVOICE_ISSUED`
   `WAIT_ARCHIVE_SUBMIT`、`ARCHIVE_REVIEWING`、`ARCHIVE_REJECTED`、`ARCHIVED`

### 2.4 已确认的关键业务规则

从现有实现和测试中，至少要验证以下规则：

1. 项目创建会自动创建工单，工单默认指向项目负责人。
2. 项目组成员完成前，流程不能进入合同上传阶段。
3. 合同提交审核时，指定审核人必须具备 `CONTRACT_REVIEWER`。
4. 一审/二审/三审提交时，指定审核人必须具备对应轮次角色。
5. 项目金额、评估基准日是评审提交的必填前置条件。
6. 项目负责人和业务负责人不得兼任一审/二审/三审。
7. 一审/二审/三审人员必须互斥，不得重复。
8. 驳回后允许重新提交，也允许变更审核人，但同一轮驳回只允许变更一次。
9. 一审通过后并不一定直接给项目负责人，也存在“留在一审人处选择二审”的分支。
10. 二审、三审也存在同类“审核人选下一级”与“退回项目负责人”的分支。
11. 非国资项目三审通过后进入签发上传。
12. 国资项目三审通过后先走“外部审核确认”，之后进入外部一二三复核链。
13. 外部三审通过后才进入签发上传。
14. 项目方上传正式报告与合同扫描件后，才可进入首席签发。
15. 首席签发通过后进入文印。
16. 文印出具纸质报告后，主流程会推进到开票/邮寄相关阶段。
17. 邮寄和开票并非完全串行，待办可能并存，需要验证工作台展示逻辑。
18. 开票总金额不得超过项目金额，且已开票后允许新开一轮发票申请。
19. 发票被财务处理后，需要项目方确认；拒绝时主流程不一定改变，但待办必须改变。
20. 归档分为提交、审核、最终归档确认，项目 `archived_at` 与工单 `ARCHIVED` 需一致。
21. 所有流程动作应写入 `workflow_logs`。
22. 评审动作、合同审核动作等应写入对应记录表。
23. 通知中心的已读、未读、已处理状态来自通知表与业务动作联动。
24. 管理员可处理项目删除申请、终止审批、冲突处理、问题反馈。
25. 删除申请通过后项目实体删除，但申请记录摘要仍应保留。

## 3. 真实数据测试总原则

### 3.1 为什么要用真实数据

本系统的风险不在“字段增删改查”本身，而在：

1. 同一项目跨十几个状态的连续推进。
2. 同一账号在不同角色下看到的待办不同。
3. 同一阶段前端按钮显示与后端守卫可能不一致。
4. 同一业务动作会同时影响项目、工单、附件、记录、通知、工作台。

因此必须使用“真实业务场景数据”，而不是单接口空数据调试。

### 3.2 验证方法

每条用例都同时验证五层结果：

1. 页面层
   页面能否进入、按钮是否可见、表单是否可填、错误提示是否正确。
2. 接口层
   接口返回码、返回字段、异常码是否符合预期。
3. 数据层
   关键表是否正确新增、更新、软删或保留。
4. 流程层
   `current_status`、`current_handler_user_id`、待办角色是否正确切换。
5. 留痕层
   `workflow_logs`、`review_records`、`contract_review_record`、`notifications` 等是否产生记录。

### 3.3 验收标准

达到“无死角”的最低标准：

1. 每个前端业务页至少执行 1 次正向流程。
2. 每个后端业务路由至少执行 1 次成功调用和 1 次失败调用。
3. 每个状态迁移至少验证 1 次合法转移。
4. 每个驳回类节点至少验证 1 次回退重提。
5. 每个角色至少验证 1 次“能做什么”和 1 次“不能做什么”。
6. 每个关键业务对象至少验证 1 次新增、查询、关联展示、留痕。
7. 工作台、通知中心、项目详情三处视图必须彼此对齐。

## 4. 本地测试环境设计

### 4.1 环境建议

建议分两套本地数据环境：

1. `环境A：回归基线库`
   用于重复跑主链路，数据库每轮重建。
2. `环境B：长链验证库`
   用于保留完整真实流程数据，做工作台、导出、通知、历史记录、重复开票、重复删除申请等验证。

### 4.2 启动方式

当前仓库可按以下方式启动：

1. 前端
   `cd D:\1\OA-main\frontend`
   `npm.cmd run dev`
2. 后端
   `cd D:\1\OA-main\backend`
   `uvicorn app.main:app --host 127.0.0.1 --port 8080`
3. 也可参考 [start-local.ps1](D:/1/OA-main/start-local.ps1)

建议使用独立测试库，例如：

```env
DATABASE_URL=sqlite:///D:/1/OA-main/tmp-test-data/real-test.db
LOCAL_STORAGE_DIR=D:/1/OA-main/tmp-test-data/uploads-real
DB_INIT_REQUIRED=true
INITIAL_ADMIN_USERNAME=admin
INITIAL_ADMIN_PASSWORD=zhongqin123
```

### 4.3 测试附件目录

建议准备真实测试附件目录：

1. `tmp-test-data/real-files/contracts`
2. `tmp-test-data/real-files/reports`
3. `tmp-test-data/real-files/formal`
4. `tmp-test-data/real-files/archive`
5. `tmp-test-data/real-files/imports`

建议至少准备以下文件：

1. 合同初稿 PDF 2 份
2. 合同扫描件 PDF 2 份
3. 报告压缩包 ZIP 3 份
4. 正式报告 PDF 2 份
5. 归档材料 ZIP 2 份
6. 一个错误格式文件用于校验失败提示
7. 一个超小文本文件用于上传异常兼容性

## 5. 测试账号与组织矩阵

建议在测试库中手工或脚本初始化以下真实账号。

### 5.1 核心账号

1. `admin`
   角色：`ADMIN`
2. `creator_a`
   角色：项目创建人，不兼审
3. `leader_a`
   角色：`PROJECT_LEADER`
4. `member_a`
   角色：`PROJECT_MEMBER`
5. `contract_a`
   角色：`CONTRACT_REVIEWER`
6. `first_a`
   角色：`FIRST_REVIEWER`
7. `second_a`
   角色：`SECOND_REVIEWER`
8. `third_a`
   角色：`THIRD_REVIEWER`
9. `chief_a`
   角色：`CHIEF_APPRAISER`
10. `print_a`
   角色：`PRINT_ROOM`
11. `finance_a`
   角色：`FINANCE`
12. `archive_a`
   角色：`ARCHIVE_MANAGER`

### 5.2 组合账号

用于验证多角色并集和路由切换：

1. `leader_member_a`
   角色：`PROJECT_LEADER` + `PROJECT_MEMBER`
2. `admin_finance_a`
   角色：`ADMIN` + `FINANCE`
3. `print_archive_a`
   角色：`PRINT_ROOM` + `ARCHIVE_MANAGER`

### 5.3 异常账号

1. `reviewer_without_role`
   无审核角色，用于验证禁止指定
2. `inactive_user`
   停用账号，用于登录和可见性验证
3. `other_finance`
   另一财务账号，用于验证“指定财务才有待办”

## 6. 测试数据包设计

至少准备 8 个真实项目数据包，每个项目只承担一类重点场景，避免一个项目承载所有断言后难以追踪。

### 6.1 数据包清单

1. `P01-内部标准主链`
   内部项目，从创建到最终归档完整走通。
2. `P02-内部驳回重提链`
   合同驳回、一审驳回、二审换人、三审驳回后重提。
3. `P03-国资外审链`
   触发外部一二三复核，再进入签发与文印。
4. `P04-并行后处理链`
   重点验证邮寄与开票并行待办。
5. `P05-删除申请链`
   已进入后期状态后发起删除申请、拒绝后重提、通过后删除。
6. `P06-终止审批链`
   项目终止申请、管理员审批、工作台可见性变化。
7. `P07-冲突与反馈链`
   角色冲突、项目冲突、问题反馈、通知中心。
8. `P08-导出与历史链`
   用于验证导出、归档历史、通知时间线、工作流日志完整性。

### 6.2 项目字段建议

每个项目都应包含尽量真实的业务字段：

1. 项目编号
2. 项目名称
3. 客户名称
4. 评估业务性质
5. 报告类型
6. 评估基准日
7. 项目金额
8. 项目来源
9. 业务负责人
10. 项目负责人
11. 起止日期
12. 部门
13. 描述

至少准备两类 `evaluation_business_nature`：

1. 非国资类
2. 国资类

至少准备两类 `project_source`：

1. `INTERNAL`
2. `EXTERNAL`

## 7. 全量测试矩阵

以下矩阵是执行主干，建议按顺序跑。

### 7.1 认证与账号管理

正向验证：

1. 默认管理员首次登录成功。
2. 管理员可查看账号列表、修改角色、查看当前登录信息。
3. 多角色账号登录后可正常进入对应工作区。
4. 登出后再次访问业务页会回到登录页。

逆向验证：

1. 错误密码登录失败。
2. 停用账号不可登录。
3. 非管理员访问账号管理页被前端重定向，直接调接口返回 403。
4. 非管理员不可修改他人角色。

数据验证：

1. `users`
2. `roles`
3. `user_roles`

### 7.2 项目创建与工单初始化

正向验证：

1. 创建项目成功。
2. 自动生成 `project_code`。
3. 自动生成关联工单 `work_order_no`。
4. 工单状态为 `WORK_ORDER_CREATED`。
5. 当前处理人默认是项目负责人。

逆向验证：

1. 缺少项目名称、客户名称、项目负责人等必填字段时报错。
2. 业务负责人或项目负责人填写不存在账号时报错。
3. 重复项目编号或冲突项目是否有识别提示。

数据验证：

1. `projects`
2. `work_orders`
3. `workflow_logs`

### 7.3 项目成员管理

正向验证：

1. 项目负责人可批量添加成员。
2. 完成项目组设置后，状态推进到 `WAIT_CONTRACT_UPLOAD`。
3. 项目详情、流程页、工作台显示一致。

逆向验证：

1. 非项目负责人不可完成项目成员节点。
2. 未添加成员直接完成，验证是否允许；若允许需确认业务预期。
3. 重复添加同一成员的表现是否一致。

数据验证：

1. `project_members`
2. `work_orders.current_status`

### 7.4 合同上传与合同审核

正向验证：

1. 项目方上传合同初稿成功。
2. 当前版本文件在项目详情可见。
3. 提交合同审核时可指定合同审核人。
4. 审核通过后工单进入 `CONTRACT_APPROVED` 或后续报告送审阶段。
5. 审核驳回后退回项目方。

逆向验证：

1. 指定无 `CONTRACT_REVIEWER` 角色人员，提交失败。
2. 无合同初稿文件直接提交审核，验证后端是否拦截。
3. 非审核人处理审核记录，返回 403 或业务错误。

数据验证：

1. `work_order_files`
2. `contract_review_record`
3. `workflow_logs`

### 7.5 一审/二审/三审

正向验证：

1. 项目方上传报告送审材料成功。
2. 一审提交成功，状态到 `FIRST_REVIEWING`。
3. 一审通过后可选择“由一审人选二审”或“退回项目负责人发起二审”。
4. 二审、三审同理验证。
5. 驳回后项目方补充材料后可重新提交。
6. 驳回后变更审核人成功，重新提交后生效。

逆向验证：

1. 未指定对应轮次角色人员，提交失败。
2. 项目金额、评估基准日为空时提交失败。
3. 项目负责人或业务负责人兼任评审时提交失败。
4. 一审、二审、三审人员重复时提交失败。
5. 同一轮驳回后多次变更审核人，第二次失败。
6. 非当前审核人审批失败。

数据验证：

1. `review_records`
2. `work_order_files` 各轮次 `business_stage`
3. `workflow_logs`
4. `current_handler_user_id`

### 7.6 国资外部复核链

正向验证：

1. 国资项目三审通过后，状态进入 `THIRD_APPROVED_WAIT_OWNER_CONFIRM_SEND`。
2. 三审人触发外审确认流程成功。
3. 项目方确认“有外审”后进入 `WAIT_EXTERNAL_FIRST_REVIEW_SUBMIT`。
4. 外部一审、二审、三审逐级提交和通过成功。
5. 外部三审通过后进入签发上传。

逆向验证：

1. 非国资项目不应进入外审分支。
2. 项目方确认“无外审”时应走签发上传分支。
3. 外部审核文件缺失、角色不符、越权操作都应失败。

数据验证：

1. `review_records` 外部轮次记录
2. `work_order.current_status`
3. `workflow_logs`

### 7.7 签发流程

正向验证：

1. 项目方上传正式报告和合同扫描件成功。
2. 进入 `SIGNOFF_REVIEWING`。
3. 当前处理人切换为首席评估师。
4. 首席签发通过后进入 `THIRD_APPROVED_WAIT_PRINTROOM`。

逆向验证：

1. 缺少正式报告或合同扫描件时不得进入签发。
2. 非首席评估师不能审批签发。
3. 首席驳回后是否退回三审或项目方，需按实际行为核对。

数据验证：

1. `work_order.signoff_status`
2. `work_order_files`
3. `workflow_logs`

### 7.8 文印出具

正向验证：

1. 文印人员能看到待处理项目。
2. 录入纸质报告编号、份数成功。
3. 状态进入 `PAPER_REPORT_ISSUED` 或后续开票/邮寄阶段。
4. 项目详情、工作台同步刷新。

逆向验证：

1. 非文印角色不能出具。
2. 必填字段为空时报错。
3. 重复出具同一工单时，确认系统是否拦截。

数据验证：

1. `print_room_records`
2. `work_orders`
3. `workflow_logs`

### 7.9 报告邮寄

正向验证：

1. 项目方提交收件人、电话、地址成功。
2. 文印填写快递单号成功。
3. 项目方确认收件成功。
4. `mailing_status` 从提交到确认完整变化。

逆向验证：

1. 非项目方不能提交收件信息。
2. 非文印人员不能填快递单号。
3. 未填收件信息前文印提交快递单号失败。
4. 确认收件前工作台待办归属必须正确。

数据验证：

1. `report_mailing_record`
2. `work_orders.mailing_status`
3. `workflow_logs`

### 7.10 财务开票

正向验证：

1. 项目方可提交发票信息并指定财务处理人。
2. 指定财务能在工作台看到待办，其他财务看不到。
3. 财务处理完成后项目方可确认。
4. 一轮发票完成后可再次发起新一轮发票申请。

逆向验证：

1. 累计开票金额超过项目金额，提交失败。
2. 非指定财务处理失败。
3. 主流程在某些状态下提交发票不应错误改变主状态。
4. 发票被退回后，项目方应看到重新提交待办。

数据验证：

1. `invoices`
2. `work_orders.current_status`
3. `workbench` 待办显示
4. `workflow_logs`

### 7.11 归档

正向验证：

1. 项目方提交归档并指定归档审核人成功。
2. 归档管理员审核通过成功。
3. 项目方最终确认归档后，工单到 `ARCHIVED`，项目 `archived_at` 有值。
4. 归档后项目在导出、工作台、详情中显示一致。

逆向验证：

1. 非归档管理员不能审核归档。
2. 审核驳回后项目方可重新提交。
3. 已归档项目不得继续推进其他流程。

数据验证：

1. `archives`
2. `projects.archived_at`
3. `work_orders.current_status`
4. `workflow_logs`

### 7.12 通知中心与催办

正向验证：

1. 流程推进后相关人员收到通知。
2. 通知列表支持分页、已读未读、消息类型、优先级筛选。
3. 通知详情能显示项目、工单、当前状态、时间线。
4. 批量已读成功。
5. 提醒消息在业务已处理后状态变成 `PROCESSED`。

逆向验证：

1. 非当前用户不可读取他人通知详情。
2. 无关联业务对象的消息详情展示不应报错。
3. 回滚事务后不应产生假通知。

数据验证：

1. `user_notifications`
2. `reminder_events`
3. `reminder_receipts`
4. `workflow_logs`

### 7.13 工作台与待办准确性

这是必须单独测的一层。

正向验证：

1. 每个角色登录后只看到属于自己的项目待办。
2. 管理员能看到审批类待办。
3. 审核驳回、发票退回、邮寄确认、归档确认等非主状态动作，也能正确改变待办。
4. 已终止、已删除、已归档项目在工作台展示符合预期。

逆向验证：

1. 审批已完成后旧待办必须消失。
2. 非指定财务、非指定归档审核人、非当前审核人不应出现待办。
3. 管理端项目在业务工作台和管理工作台间不能串台。

### 7.14 项目导出

正向验证：

1. 导出列表可包含进行中、归档、终止、删除申请状态。
2. 项目进度字段与实际状态一致。
3. 删除申请状态、是否可管理员删除等辅助列正确。

逆向验证：

1. 过滤条件边界值下结果正确。
2. 已删除项目是否保留摘要，需和导出逻辑核对。

### 7.15 删除申请

正向验证：

1. 项目进入允许删除阶段后，项目方可发起删除申请。
2. 管理员可审批通过或拒绝。
3. 被拒绝后可再次发起，且覆盖旧申请。
4. 审批通过后项目实体删除，但申请摘要仍可查。

逆向验证：

1. 已有待审批删除申请时不可重复申请。
2. 不允许删除阶段发起删除申请应失败。
3. 非管理员不能审批删除申请。

数据验证：

1. `project_delete_requests`
2. `projects`
3. `workbench`

### 7.16 终止审批

正向验证：

1. 项目方发起终止申请成功。
2. 管理员看到终止待办并可审批。
3. 已批准终止项目从普通待办移除。

逆向验证：

1. 已终止项目不可继续正常推进流程。
2. 非管理员不能审批终止。

数据验证：

1. `projects.termination_status`
2. `termination_*` 字段
3. `workbench`

### 7.17 冲突与问题反馈

正向验证：

1. 项目冲突列表可查看和处理。
2. 问题反馈可提交、查看、管理。
3. 管理员端可见性正确。

逆向验证：

1. 普通业务账号不能进入管理员冲突/反馈页。
2. 非管理员不能处理他人冲突记录。

### 7.18 帮助中心与静态业务说明

正向验证：

1. 四个帮助页均可正常打开。
2. 路由刷新不白屏。
3. 登录后访问与直接访问行为正确。

## 8. 关键横切验证

这些检查要嵌入每条主用例中，不可漏。

### 8.1 权限横切

每一个核心动作都至少验证：

1. 正确角色成功。
2. 错误角色失败。
3. 非当前处理人失败。
4. 管理员越权是否被允许，需按接口实际约束确认。

### 8.2 状态横切

每个关键动作都要记录：

1. 执行前状态
2. 执行后状态
3. 当前处理人变化
4. 是否命中 `ALLOWED_TRANSITIONS`

### 8.3 附件横切

每个有文件上传的节点都验证：

1. 文件能上传
2. 文件能回显
3. 版本号和 `is_current` 正确
4. 业务阶段 `business_stage` 正确
5. 错误格式或空文件表现可控

### 8.4 留痕横切

每个关键动作都要核对至少一条：

1. `workflow_logs`
2. 业务记录表
3. 通知记录
4. 工作台待办变化

## 9. 建议执行顺序

### 第一轮：烟雾与环境确认

1. 登录
2. 创建项目
3. 自动创建工单
4. 工作台可见
5. 上传一份测试文件
6. 通知列表可打开

### 第二轮：内部标准主链

1. `P01-内部标准主链`
2. 从项目创建走到最终归档
3. 每节点核对状态、处理人、日志、通知

### 第三轮：驳回与回退链

1. `P02-内部驳回重提链`
2. 合同驳回
3. 一审驳回
4. 二审换人
5. 三审驳回重提

### 第四轮：国资外审链

1. `P03-国资外审链`
2. 覆盖外部一二三复核

### 第五轮：后处理并行链

1. `P04-并行后处理链`
2. 邮寄、开票、待办准确性

### 第六轮：管理链

1. `P05-删除申请链`
2. `P06-终止审批链`
3. `P07-冲突与反馈链`

### 第七轮：历史与导出

1. `P08-导出与历史链`
2. 导出
3. 通知时间线
4. 工作流日志核账

## 10. 数据核对清单

每完成一个项目数据包，至少执行一次数据库核对。

建议核对表：

1. `projects`
2. `work_orders`
3. `project_members`
4. `work_order_files`
5. `review_records`
6. `contract_review_records`
7. `print_room_records`
8. `report_mailing_records`
9. `invoices`
10. `archives`
11. `workflow_logs`
12. `user_notifications`
13. `reminder_events`
14. `reminder_receipts`
15. `project_delete_requests`
16. `issue_feedbacks`
17. `project_conflicts`

核对维度：

1. 数量是否正确
2. 最新记录是否正确
3. 关联外键是否正确
4. 状态值是否正确
5. 操作人是否正确
6. 时间顺序是否正确

## 11. 与现有自动化的对应关系

仓库已有测试已经覆盖了部分规则，但还不足以替代真实数据全量验证。

已覆盖较多的领域：

1. [test_product_smoke_flow.py](D:/1/OA-main/backend/tests/test_product_smoke_flow.py)
   主链路烟雾流程。
2. [test_reviews_submit_rules.py](D:/1/OA-main/backend/tests/test_reviews_submit_rules.py)
   审核提交规则、驳回重提、换人规则。
3. [test_signoff_flow_scenarios.py](D:/1/OA-main/backend/tests/test_signoff_flow_scenarios.py)
   国资外审与签发场景。
4. [test_project_progress_and_termination.py](D:/1/OA-main/backend/tests/test_project_progress_and_termination.py)
   项目进度、终止、发票并行待办。
5. [test_notifications_center_v2.py](D:/1/OA-main/backend/tests/test_notifications_center_v2.py)
   通知中心。
6. [test_project_delete_requests.py](D:/1/OA-main/backend/tests/test_project_delete_requests.py)
   删除申请。
7. [test_contract_reviews.py](D:/1/OA-main/backend/tests/test_contract_reviews.py)
   合同审核。

仍必须通过真实数据手工或半自动补足的部分：

1. 前端页面交互与按钮权限
2. 路由跳转与刷新
3. 文件上传和版本回显
4. 工作台与项目详情的前端映射
5. 实时通知展示
6. 多账号串行登录后的真实待办切换
7. 帮助中心、导出页、管理员页联动

## 12. 最终验收输出物

完成本方案时，建议形成以下产物：

1. `测试执行记录.xlsx`
   记录项目包、步骤、执行人、结果、问题编号。
2. `真实数据测试库`
   保留一份完整链路数据库快照。
3. `截图包`
   每个关键节点保留页面截图。
4. `SQL核对脚本`
   针对关键表做快速核账。
5. `缺陷清单`
   按严重度区分：阻断、主要、次要、体验。

## 13. 结论

如果按本方案执行，基本可以无死角覆盖本仓库当前OA系统的：

1. 角色权限
2. 业务主流程
3. 扩展外审流程
4. 后处理流程
5. 管理审批流程
6. 前后端联动
7. 数据落库与历史留痕

这套方案的重点不是“多写几条测试”，而是把“项目、工单、附件、审核、通知、待办、归档、导出”作为一个整体去验。对于这个仓库来说，这才是真正能发现问题的验证方式。
