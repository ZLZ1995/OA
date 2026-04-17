<template>
  <el-card class="page-card" shadow="never">
    <template #header>工单列表</template>
    <el-button type="primary">创建工单</el-button>
    <el-table :data="rows" style="margin-top: 12px">
      <el-table-column prop="work_order_no" label="工单号" />
      <el-table-column prop="title" label="标题" />
      <el-table-column prop="current_status" label="状态" />
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getWorkOrders } from '@/api/workorders'

const rows = ref<Array<{ id: number; work_order_no: string; title: string; current_status: string }>>([])

onMounted(async () => {
  try {
    rows.value = await getWorkOrders()
  } catch {
    ElMessage.error('工单列表加载失败')
  }
})
</script>
