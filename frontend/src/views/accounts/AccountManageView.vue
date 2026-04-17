<template>
  <el-card class="page-card" shadow="never">
    <template #header>账号管理页</template>
    <el-button type="primary">新增账号</el-button>
    <el-table :data="rows" style="margin-top: 12px">
      <el-table-column prop="username" label="账号" />
      <el-table-column prop="real_name" label="姓名" />
      <el-table-column prop="roles" label="角色" />
      <el-table-column prop="is_active" label="状态">
        <template #default="scope">
          <el-tag :type="scope.row.is_active ? 'success' : 'danger'">{{ scope.row.is_active ? '启用' : '禁用' }}</el-tag>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getUsers } from '@/api/users'

interface UserRow {
  id: number
  username: string
  real_name: string
  roles: string
  is_active: boolean
}

const rows = ref<UserRow[]>([])

onMounted(async () => {
  try {
    const data = await getUsers()
    rows.value = data.map((item) => ({ ...item, roles: item.roles.join(', ') }))
  } catch {
    ElMessage.error('账号列表加载失败')
  }
})
</script>
