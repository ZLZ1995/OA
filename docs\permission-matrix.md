# 角色权限矩阵固化（阶段1）

## 固定角色
- ADMIN
- SALES
- PROJECT_LEADER
- PROJECT_MEMBER
- FIRST_REVIEWER
- SECOND_REVIEWER
- THIRD_REVIEWER
- PRINT_ROOM
- FINANCE
- ARCHIVE_MANAGER

## 原则
1. 一个账号可绑定多个角色，权限取并集。
2. 管理员只做账号与角色分配，不改角色模板。
3. 审核老师只审核，不负责指定下一位审核老师。
4. 只有项目负责人可发起二审/三审并选人。
5. 所有权限以后端校验为准。

## 最小能力划分
- ADMIN：账号、角色分配、全局查询。
- PROJECT_LEADER：工单推进、选审老师、提交流程。
- FIRST/SECOND/THIRD_REVIEWER：审核通过/退回。
- PRINT_ROOM：正式合同与纸质报告出具登记。
- FINANCE：发票登记。
- ARCHIVE_MANAGER：归档登记。
