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
        <el-descriptions-item label="业务负责人ID">{{ project.business_user_id }}</el-descriptions-item>
        <el-descriptions-item label="项目负责人ID">{{ project.project_leader_id }}</el-descriptions-item>
        <el-descriptions-item label="状态">{{ project.status_display }}</el-descriptions-item>
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
