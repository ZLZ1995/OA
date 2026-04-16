<template>
  <el-card class="page-card" shadow="never">
    <template #header>项目列表</template>
    <el-button type="primary">新建项目</el-button>
    <el-table :data="rows" style="margin-top: 12px">
      <el-table-column prop="code" label="项目编号" />
      <el-table-column prop="name" label="项目名称" />
      <el-table-column prop="leader" label="项目负责人" />
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
const rows = [
  { code: 'P2026001', name: '固定资产评估项目A', leader: 'zhangsan' }
]
</script>
