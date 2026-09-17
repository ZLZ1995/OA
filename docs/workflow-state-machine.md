# 状态机固化（阶段1）

> 历史阶段文档，状态和迁移不完整。“审核通过必须回到负责人”等表述已过时。当前使用支持请阅读 [Agent 使用支持说明书](agent-support-manual.md)，完整实现见 `backend/app/workflows/`。

## 状态枚举（WorkOrderStatus）
- PROJECT_CREATED
- WORK_ORDER_CREATED
- CONTRACT_UPLOADED
- WAIT_PRINTROOM_OFFICIAL_CONTRACT
- WAIT_FIRST_REVIEW_SUBMIT
- FIRST_REVIEWING
- FIRST_REVIEW_REJECTED
- FIRST_APPROVED_WAIT_LEADER_SUBMIT_SECOND
- WAIT_SECOND_REVIEW_SUBMIT
- SECOND_REVIEWING
- SECOND_REVIEW_REJECTED
- SECOND_APPROVED_WAIT_LEADER_SUBMIT_THIRD
- WAIT_THIRD_REVIEW_SUBMIT
- THIRD_REVIEWING
- THIRD_REVIEW_REJECTED
- THIRD_APPROVED_WAIT_PRINTROOM
- PRINTROOM_PROCESSING
- PAPER_REPORT_ISSUED

## 关键迁移
- 一审通过后必须回到项目负责人发起二审。
- 二审通过后必须回到项目负责人发起三审。
- 三审通过由三审老师转交文印室。

## 守卫规则
- 当前状态必须允许当前动作。
- 当前操作者必须拥有动作对应角色。
- 审核规避规则必须通过。
