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
      <el-form-item label="角色">
        <el-select
          v-model="form.role_codes"
          multiple
          placeholder="角色"
          :loading="rolesLoading"
          :disabled="rolesLoading || roleOptions.length === 0"
          style="min-width: 240px"
        >
          <el-option v-for="role in roleOptions" :key="role.code" :label="role.name" :value="role.code" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="onCreate">新增账号</el-button>
      </el-form-item>
    </el-form>

    <el-table :data="rows" style="margin-top: 12px" v-loading="loading">
      <el-table-column prop="username" label="账号" width="180" />
      <el-table-column prop="real_name" label="姓名" width="160" />
      <el-table-column label="当前角色" min-width="220">
        <template #default="scope">
          <el-space wrap>
            <el-tag v-for="code in scope.row.roles" :key="`${scope.row.id}-${code}`" size="small" type="info">
              {{ roleNameMap[code] || code }}
            </el-tag>
          </el-space>
        </template>
      </el-table-column>
      <el-table-column label="权限编辑" min-width="320">
        <template #default="scope">
          <el-select
            v-model="editableRoleCodes[scope.row.id]"
            multiple
            placeholder="选择角色"
            :loading="rolesLoading"
            :disabled="rolesLoading || roleOptions.length === 0"
            style="width: 100%"
          >
            <el-option v-for="role in roleOptions" :key="role.code" :label="role.name" :value="role.code" />
          </el-select>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="scope">{{ scope.row.is_active ? '启用' : '禁用' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="scope">
          <el-button
            type="primary"
            :loading="savingUserId === scope.row.id"
            @click="saveRowRoles(scope.row.id)"
          >
            保存
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { listRoles, type RoleItem } from '@/api/roles'
import { bindUserRoles, createUser, listUsers, type UserItem } from '@/api/users'

const loading = ref(false)
const rolesLoading = ref(false)
const savingUserId = ref<number | null>(null)
const rows = ref<UserItem[]>([])
const roleOptions = ref<RoleItem[]>([])
const editableRoleCodes = ref<Record<number, string[]>>({})

const roleNameMap = computed<Record<string, string>>(() => {
  return roleOptions.value.reduce((acc, item) => {
    acc[item.code] = item.name
    return acc
  }, {} as Record<string, string>)
})

const form = reactive({
  username: '',
  real_name: '',
  password: '',
  role_codes: [] as string[]
})

function hydrateEditableRoles(users: UserItem[]) {
  const next: Record<number, string[]> = {}
  users.forEach((item) => {
    next[item.id] = [...item.roles]
  })
  editableRoleCodes.value = next
}

async function loadUsers() {
  loading.value = true
  try {
    const userData = await listUsers()
    rows.value = userData.items
    hydrateEditableRoles(userData.items)
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '账号列表加载失败')
  } finally {
    loading.value = false
  }
}

async function loadRoles() {
  rolesLoading.value = true
  try {
    const roleData = await listRoles()
    roleOptions.value = roleData.items
  } catch (error: any) {
    roleOptions.value = []
    ElMessage.error(error?.response?.data?.detail || '角色权限加载失败')
  } finally {
    rolesLoading.value = false
  }
}

async function onCreate() {
  if (!form.username || !form.real_name || !form.password) {
    ElMessage.warning('请填写完整账号、姓名、密码')
    return
  }
  if (form.role_codes.length === 0) {
    ElMessage.warning('请至少选择一个角色/权限')
    return
  }
  try {
    await createUser({ ...form })
    ElMessage.success('账号创建成功')
    form.username = ''
    form.real_name = ''
    form.password = ''
    form.role_codes = []
    await loadUsers()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '账号创建失败')
  }
}

async function saveRowRoles(userId: number) {
  const roleCodes = editableRoleCodes.value[userId] || []
  savingUserId.value = userId
  try {
    await bindUserRoles(userId, roleCodes)
    ElMessage.success('角色已更新')
    await loadUsers()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '角色更新失败')
  } finally {
    savingUserId.value = null
  }
}

onMounted(async () => {
  await Promise.all([loadUsers(), loadRoles()])
})
</script>
