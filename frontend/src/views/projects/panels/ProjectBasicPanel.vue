<template>
  <el-descriptions :column="2" border>
    <el-descriptions-item label="项目编号">{{ flowInfo.project.project_no }}</el-descriptions-item>
    <el-descriptions-item label="项目名称">{{ flowInfo.project.project_name }}</el-descriptions-item>
    <el-descriptions-item label="客户名称">{{ flowInfo.project.client_name }}</el-descriptions-item>
    <el-descriptions-item label="承接单位">{{ flowInfo.project.undertaking_unit || '-' }}</el-descriptions-item>
    <el-descriptions-item label="报告类型">{{ flowInfo.project.report_type || '-' }}</el-descriptions-item>
    <el-descriptions-item label="评估基准日">{{ flowInfo.project.valuation_base_date || '-' }}</el-descriptions-item>
    <el-descriptions-item label="项目承接业务员">{{ flowInfo.project.business_salesman || '-' }}</el-descriptions-item>
    <el-descriptions-item label="项目来源">{{ flowInfo.project.project_source_display }}</el-descriptions-item>
    <el-descriptions-item label="页面展示负责人">{{ flowInfo.project.project_leader_display_name || '-' }}</el-descriptions-item>
    <el-descriptions-item label="外部项目负责人">{{ flowInfo.project.external_project_leader_name || '-' }}</el-descriptions-item>
    <el-descriptions-item label="当前步骤">{{ flowInfo.project.current_step }}</el-descriptions-item>
    <el-descriptions-item label="项目状态">{{ flowInfo.project.status_display }}</el-descriptions-item>
    <el-descriptions-item label="合同审核状态">{{ flowInfo.contract_review_status_display || '-' }}</el-descriptions-item>
    <el-descriptions-item label="合同审核人">{{ flowInfo.contract_reviewer_name || '-' }}</el-descriptions-item>
  </el-descriptions>
</template>

<script setup lang="ts">
import type { ProjectFlowData } from '@/api/projectFlow'

defineProps<{ flowInfo: ProjectFlowData }>()
</script>
