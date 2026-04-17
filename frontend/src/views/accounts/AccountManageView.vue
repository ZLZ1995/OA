<template>
  <el-card class="page-card" shadow="never">
    <template #header>账号管理页</template>
    <el-form inline @submit.prevent>
      <el-form-item label="账号">
        <el-input v-model="form.username" placeholder="例如 user01" />
      </el-form-item>
      <el-form-item label="姓名">
        <el-input v-model="form.real_name" placeholder="姓名" />
      </el-form-item>
      <el-form-item label="密码">
        <el-input v-model="form.password" type="password" show-password placeholder="至少6位" />
      </el-form-item>
      <el-form-item>
        <el-select v-model="form.role_codes" multiple placeholder="角色">
          <el-option v-for="role in roleOptions" :key="role.code" :label="role.name" :value="role.code" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="onCreate">新增账号</el-button>
      </el-form-item>
    </el-form>

    <el-table :data="rows" style="margin-top: 12px" v-loading="loading">
      <el-table-column prop="username" label="账号" />
      <el-table-column prop="real_name" label="姓名" />
      <el-table-column label="角色">
        <template #default="scope">
          {{ scope.row.roles.join(', ') }}
        </template>
      </el-table-column>
      <el-table-column label="状态">
        <template #default="scope">{{ scope.row.is_active ? '启用' : '禁用' }}</template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { listRoles, type RoleItem } from '@/api/roles'
import { createUser, listUsers, type UserItem } from '@/api/users'

const loading = ref(false)
const rows = ref<UserItem[]>([])
const roleOptions = ref<RoleItem[]>([])

const form = reactive({
  username: '',
  real_name: '',
  password: '',
  role_codes: [] as string[]
})

async function loadData() {
  loading.value = true
  try {
    const [userData, roleData] = await Promise.all([listUsers(), listRoles()])
    rows.value = userData.items
    roleOptions.value = roleData.items
  } finally {
    loading.value = false
  }
}

async function onCreate() {
  if (!form.username || !form.real_name || !form.password) {
    ElMessage.warning('请填写完整账号、姓名、密码')
    return
  }
  await createUser({ ...form })
  ElMessage.success('账号创建成功')
  form.username = ''
  form.real_name = ''
  form.password = ''
  form.role_codes = []
  await loadData()
}

onMounted(loadData)
</script>
