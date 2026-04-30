<template>
  <el-row :gutter="12">
    <el-col :span="5">
      <el-card shadow="never">
        <template #header>项目流程导航</template>
        <el-menu :default-active="selectedStep" @select="onSelect">
          <el-menu-item v-for="(step, idx) in navigationSteps" :key="step" :index="step" :disabled="idx > activeStep + 1">
            <span :style="stepStyle(idx)">{{ step }}</span>
          </el-menu-item>
        </el-menu>
      </el-card>
    </el-col>
    <el-col :span="11">
      <el-card shadow="never">
        <template #header>{{ selectedStep }}</template>
        <el-descriptions :column="1" border v-if="flow">
          <el-descriptions-item label="项目编号">{{ flow.project.project_no }}</el-descriptions-item>
          <el-descriptions-item label="项目名称">{{ flow.project.project_name }}</el-descriptions-item>
          <el-descriptions-item label="客户名称">{{ flow.project.client_name }}</el-descriptions-item>
          <el-descriptions-item label="承接单位">{{ flow.project.undertaking_unit }}</el-descriptions-item>
          <el-descriptions-item label="当前步骤">{{ flow.project.current_step }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ flow.project.status_display }}</el-descriptions-item>
          <el-descriptions-item label="我的身份">{{ flow.user_role_in_project }}</el-descriptions-item>
          <el-descriptions-item label="可操作事项">{{ flow.available_action }}</el-descriptions-item>
        </el-descriptions>
        <p style="margin-top:12px">当前节点办理区域（占位）：{{ selectedStep }}。</p>
      </el-card>
    </el-col>
    <el-col :span="8">
      <el-card shadow="never">
        <template #header>办理流程图</template>
        <el-steps direction="vertical" :active="activeStep" finish-status="success">
          <el-step v-for="s in flow?.flow_steps || []" :key="s" :title="s" />
        </el-steps>
      </el-card>
    </el-col>
  </el-row>
</template>
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getProjectFlow, type ProjectFlowData } from '@/api/projectFlow'
const route = useRoute()
const flow = ref<ProjectFlowData | null>(null)
const selectedStep = ref('项目概况')
const navigationSteps = ['项目概况', '项目组成员', '合同上传', '报告送审', '一审', '二审', '三审', '报告出具', '开具发票', '报告归档']
const activeStep = computed(() => Math.max(0, (flow.value?.flow_steps || []).indexOf(flow.value?.project.current_step || '')))
function stepStyle(idx: number) {
  if (idx < activeStep.value) return { color: '#67c23a' }
  if (idx === activeStep.value) return { color: '#409eff', fontWeight: 700 }
  return { color: '#909399' }
}
function onSelect(step: string) { selectedStep.value = step }
async function load() {
  try {
    flow.value = await getProjectFlow(Number(route.params.id))
    selectedStep.value = flow.value.project.current_step
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '无权查看该项目')
  }
}
onMounted(load)
</script>
