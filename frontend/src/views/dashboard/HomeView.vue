<template>
  <el-card class="page-card" shadow="never">
    <template #header>首页工作台</template>
    <el-row :gutter="12" v-loading="loading">
      <el-col :span="12"><el-statistic title="待我办理" :value="todoCount" /></el-col>
      <el-col :span="12"><el-statistic title="我创建的工单" :value="createdCount" /></el-col>
    </el-row>
    <el-button style="margin-top: 12px" @click="loadDashboard">刷新</el-button>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getMyDashboard } from '@/api/dashboard'

const loading = ref(false)
const todoCount = ref(0)
const createdCount = ref(0)

async function loadDashboard() {
  loading.value = true
  try {
    const data = await getMyDashboard()
    todoCount.value = data.todo_items.length
    createdCount.value = data.created_items.length
  } finally {
    loading.value = false
  }
}

onMounted(loadDashboard)
</script>
