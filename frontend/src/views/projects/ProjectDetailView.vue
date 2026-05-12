<template>
  <el-card class="page-card" shadow="never" v-loading="loading">
    <template #header>项目详情</template>

    <el-empty v-if="!project" description="暂无项目数据" />
    <template v-else>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="项目编号">{{ project.project_code }}</el-descriptions-item>
        <el-descriptions-item label="承接单位">{{ project.undertaking_unit }}</el-descriptions-item>
        <el-descriptions-item label="项目名称">{{ project.project_name }}</el-descriptions-item>
        <el-descriptions-item label="客户名称">{{ project.client_name }}</el-descriptions-item>
        <el-descriptions-item label="报告类型">{{ project.report_type }}</el-descriptions-item>
        <el-descriptions-item label="评估基准日">{{ project.valuation_base_date || '-' }}</el-descriptions-item>
        <el-descriptions-item label="项目承接业务员">{{ project.business_salesman || '-' }}</el-descriptions-item>
        <el-descriptions-item label="项目来源">{{ project.project_source_display }}</el-descriptions-item>
        <el-descriptions-item label="项目负责人">{{ project.project_leader_display_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="外部项目负责人">{{ project.external_project_leader_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="合同审核状态">{{ project.contract_review_status_display || '-' }}</el-descriptions-item>
        <el-descriptions-item label="项目状态">{{ project.status_display }}</el-descriptions-item>
        <el-descriptions-item label="归档时间">{{ project.archived_at || '-' }}</el-descriptions-item>
      </el-descriptions>

      <div class="actions">
        <el-button type="primary" @click="goFlow">进入流程办理</el-button>
        <el-button @click="router.back()">返回</el-button>
      </div>
    </template>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getProject, type ProjectItem } from '@/api/projects'

const route = useRoute()
const router = useRouter()
const project = ref<ProjectItem | null>(null)
const loading = ref(false)

async function loadProject() {
  loading.value = true
  try {
    project.value = await getProject(route.params.id as string)
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '项目详情加载失败')
  } finally {
    loading.value = false
  }
}

function goFlow() {
  router.push(`/projects/${route.params.id}/flow`)
}

onMounted(loadProject)
</script>

<style scoped>
.actions {
  margin-top: 16px;
  display: flex;
  gap: 8px;
}
</style>
