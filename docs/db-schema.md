# 数据库表设计固化（阶段1）

本文档对应模型目录 `backend/app/models`。

## 核心表
- users
- roles
- user_roles
- departments
- projects
- project_members
- work_orders
- work_order_files
- contracts
- report_versions
- review_records
- workflow_logs
- print_room_records
- invoices
- archives

## 关键约束
1. 账号可绑定多个角色（`user_roles` 唯一索引：`user_id + role_id`）。
2. 角色模板固定，业务不允许新增/删除/改模板。
3. 工单流转状态由 `work_orders.current_status` 持有。
4. 全流程动作留痕到 `workflow_logs`。
5. 审核过程记录到 `review_records`。
6. 文件按版本管理：`work_order_files` + `report_versions`。

## 审核规避规则（服务层强校验）
- 项目负责人/业务负责人不得担任同项目一审/二审/三审。
- 一审、二审、三审人员两两互斥。
- 候选人列表需要前置过滤，提交动作需要后置硬校验。
