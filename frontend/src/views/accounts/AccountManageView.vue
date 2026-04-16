<template>
  <el-card class="page-card" shadow="never">
    <template #header>账号管理页</template>
    <el-button type="primary">新增账号</el-button>
    <el-table :data="rows" style="margin-top: 12px">
      <el-table-column prop="username" label="账号" />
      <el-table-column prop="realName" label="姓名" />
      <el-table-column prop="roles" label="角色" />
      <el-table-column prop="status" label="状态" />
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
const rows = [{ username: 'admin', realName: '系统管理员', roles: 'ADMIN', status: '启用' }]
</script>
