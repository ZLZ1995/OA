<template>
  <el-descriptions :column="2" border>
    <el-descriptions-item label="项目编号">{{ flowInfo.project.project_no }}</el-descriptions-item>
    <el-descriptions-item label="项目名称">{{ flowInfo.project.project_name }}</el-descriptions-item>
    <el-descriptions-item label="客户名称">{{ flowInfo.project.client_name }}</el-descriptions-item>
    <el-descriptions-item label="承接单位">{{ flowInfo.project.undertaking_unit || '-' }}</el-descriptions-item>
    <el-descriptions-item label="当前步骤">{{ flowInfo.project.current_step }}</el-descriptions-item>
    <el-descriptions-item label="项目状态">{{ flowInfo.project.status_display }}</el-descriptions-item>
  </el-descriptions>
</template>

<script setup lang="ts">
import type { ProjectFlowData } from '@/api/projectFlow'

defineProps<{ flowInfo: ProjectFlowData }>()
</script>
