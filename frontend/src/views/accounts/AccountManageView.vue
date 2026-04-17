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
        <el-select v-model="form.role_codes" multiple placeholder="角色" style="width: 220px">
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
        <template #default="scope">{{ scope.row.roles.join(', ') }}</template>
      </el-table-column>
      <el-table-column label="状态">
        <template #default="scope">{{ scope.row.is_active ? '启用' : '禁用' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="280">
        <template #default="scope">
          <el-button link type="primary" @click="openRoleDialog(scope.row)">角色绑定</el-button>
          <el-button link type="primary" @click="openEditDialog(scope.row)">编辑姓名</el-button>
          <el-button link :type="scope.row.is_active ? 'danger' : 'success'" @click="toggleActive(scope.row)">
            {{ scope.row.is_active ? '禁用' : '启用' }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="roleDialogVisible" title="绑定角色" width="420px">
      <el-select v-model="editingRoleCodes" multiple placeholder="选择角色" style="width: 100%">
        <el-option v-for="role in roleOptions" :key="role.code" :label="role.name" :value="role.code" />
      </el-select>
      <template #footer>
        <el-button @click="roleDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveRoles">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="nameDialogVisible" title="编辑姓名" width="420px">
      <el-input v-model="editingRealName" placeholder="请输入姓名" />
      <template #footer>
        <el-button @click="nameDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveName">保存</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { listRoles, type RoleItem } from '@/api/roles'
import { bindUserRoles, createUser, listUsers, type UserItem, updateUser } from '@/api/users'
import { useAuthStore } from '@/store/auth'

const auth = useAuthStore()
const loading = ref(false)
const rows = ref<UserItem[]>([])
const roleOptions = ref<RoleItem[]>([])

const roleDialogVisible = ref(false)
const nameDialogVisible = ref(false)
const editingUserId = ref<number | null>(null)
const editingRoleCodes = ref<string[]>([])
const editingRealName = ref('')

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

async function ensureAdmin() {
  const profile = auth.user ?? (await auth.ensureUserLoaded())
  if (!profile?.id) {
    ElMessage.error('登录态已失效，请重新登录')
    return false
  }
  if (!profile.roles.includes('ADMIN')) {
    ElMessage.error('仅管理员可执行账号管理操作')
    return false
  }
  return true
}

async function onCreate() {
  if (!(await ensureAdmin())) return
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

function openRoleDialog(user: UserItem) {
  editingUserId.value = user.id
  editingRoleCodes.value = [...user.roles]
  roleDialogVisible.value = true
}

async function saveRoles() {
  if (!(await ensureAdmin()) || !editingUserId.value) return
  await bindUserRoles(editingUserId.value, editingRoleCodes.value)
  ElMessage.success('角色绑定已更新')
  roleDialogVisible.value = false
  await loadData()
}

function openEditDialog(user: UserItem) {
  editingUserId.value = user.id
  editingRealName.value = user.real_name
  nameDialogVisible.value = true
}

async function saveName() {
  if (!(await ensureAdmin()) || !editingUserId.value) return
  if (!editingRealName.value.trim()) {
    ElMessage.warning('姓名不能为空')
    return
  }
  await updateUser(editingUserId.value, { real_name: editingRealName.value.trim() })
  ElMessage.success('姓名已更新')
  nameDialogVisible.value = false
  await loadData()
}

async function toggleActive(user: UserItem) {
  if (!(await ensureAdmin())) return
  await updateUser(user.id, { is_active: !user.is_active })
  ElMessage.success(user.is_active ? '账号已禁用' : '账号已启用')
  await loadData()
}

onMounted(loadData)
</script>
