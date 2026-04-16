<template>
  <el-card class="page-card" shadow="never">
    <template #header>工单列表</template>
    <el-button type="primary">创建工单</el-button>
    <el-table :data="rows" style="margin-top: 12px">
      <el-table-column prop="no" label="工单号" />
      <el-table-column prop="title" label="标题" />
      <el-table-column prop="status" label="状态" />
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
const rows = [
  { no: 'WO2026001', title: '一期评估报告', status: 'FIRST_REVIEWING' }
]
</script>
