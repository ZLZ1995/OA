<template>
  <el-card class="page-card" shadow="never">
    <template #header>项目列表</template>
    <el-button type="primary">新建项目</el-button>
    <el-table :data="rows" style="margin-top: 12px">
      <el-table-column prop="project_code" label="项目编号" />
      <el-table-column prop="project_name" label="项目名称" />
      <el-table-column prop="client_name" label="客户名称" />
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getProjects } from '@/api/projects'

const rows = ref<Array<{ id: number; project_code: string; project_name: string; client_name: string }>>([])

onMounted(async () => {
  try {
    rows.value = await getProjects()
  } catch {
    ElMessage.error('项目列表加载失败')
  }
})
</script>
