<template>
  <el-card shadow="never">
    <template #header>项目流程页</template>
    <el-descriptions :column="2" border v-if="flow">
      <el-descriptions-item label="项目编号">{{ flow.project.project_no }}</el-descriptions-item>
      <el-descriptions-item label="项目名称">{{ flow.project.project_name }}</el-descriptions-item>
      <el-descriptions-item label="客户名称">{{ flow.project.client_name }}</el-descriptions-item>
      <el-descriptions-item label="承接单位">{{ flow.project.undertaking_unit }}</el-descriptions-item>
      <el-descriptions-item label="当前步骤">{{ flow.project.current_step }}</el-descriptions-item>
      <el-descriptions-item label="状态">{{ flow.project.status_display }}</el-descriptions-item>
      <el-descriptions-item label="我的身份">{{ flow.user_role_in_project }}</el-descriptions-item>
      <el-descriptions-item label="可操作事项">{{ flow.available_action }}</el-descriptions-item>
    </el-descriptions>
    <el-steps style="margin-top:16px" :active="activeStep" finish-status="success">
      <el-step v-for="s in flow?.flow_steps || []" :key="s" :title="s" />
    </el-steps>
  </el-card>
</template>
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getProjectFlow, type ProjectFlowData } from '@/api/projectFlow'
const route = useRoute()
const flow = ref<ProjectFlowData | null>(null)
const activeStep = computed(() => Math.max(0, (flow.value?.flow_steps || []).indexOf(flow.value?.project.current_step || '')))
async function load() {
  try { flow.value = await getProjectFlow(Number(route.params.id)) }
  catch (error: any) { ElMessage.error(error?.response?.data?.detail || '无权查看该项目') }
}
onMounted(load)
</script>
