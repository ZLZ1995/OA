<template>
  <el-card class="page-card" shadow="never">
    <template #header>项目列表</template>
    <el-form inline @submit.prevent>
      <el-form-item label="项目编号">
        <el-input v-model="form.project_code" />
      </el-form-item>
      <el-form-item label="项目名称">
        <el-input v-model="form.project_name" />
      </el-form-item>
      <el-form-item label="客户名称">
        <el-input v-model="form.client_name" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="onCreate">新建项目</el-button>
      </el-form-item>
    </el-form>

    <el-table :data="rows" style="margin-top: 12px" v-loading="loading">
      <el-table-column prop="project_code" label="项目编号" />
      <el-table-column prop="project_name" label="项目名称" />
      <el-table-column prop="client_name" label="客户名称" />
      <el-table-column prop="project_leader_id" label="项目负责人ID" />
      <el-table-column prop="status" label="状态" />
      <el-table-column label="操作" width="220">
        <template #default="scope">
          <el-button link type="primary" @click="openEditDialog(scope.row)">编辑</el-button>
          <el-button link type="danger" @click="removeProject(scope.row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="editDialogVisible" title="编辑项目" width="460px">
      <el-form label-width="88px">
        <el-form-item label="项目名称">
          <el-input v-model="editing.project_name" />
        </el-form-item>
        <el-form-item label="客户名称">
          <el-input v-model="editing.client_name" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="editing.status" style="width: 100%">
            <el-option label="ACTIVE" value="ACTIVE" />
            <el-option label="CLOSED" value="CLOSED" />
            <el-option label="CANCELLED" value="CANCELLED" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveProject">保存</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createProject, deleteProject, listProjects, type ProjectItem, updateProject } from '@/api/projects'
import { useAuthStore } from '@/store/auth'

const auth = useAuthStore()
const loading = ref(false)
const rows = ref<ProjectItem[]>([])

const form = reactive({
  project_code: '',
  project_name: '',
  client_name: ''
})

const editDialogVisible = ref(false)
const editingId = ref<number | null>(null)
const editing = reactive({
  project_name: '',
  client_name: '',
  status: 'ACTIVE'
})

async function loadProjects() {
  loading.value = true
  try {
    const data = await listProjects()
    rows.value = data.items
  } finally {
    loading.value = false
  }
}

async function onCreate() {
  const profile = auth.user ?? (await auth.ensureUserLoaded())
  if (!profile?.id) {
    ElMessage.error('登录态已失效，请重新登录')
    return
  }
  if (!form.project_code || !form.project_name || !form.client_name) {
    ElMessage.warning('请填写完整项目信息')
    return
  }
  await createProject({
    ...form,
    business_user_id: profile.id,
    project_leader_id: profile.id
  })
  ElMessage.success('项目创建成功')
  form.project_code = ''
  form.project_name = ''
  form.client_name = ''
  await loadProjects()
}

function openEditDialog(row: ProjectItem) {
  editingId.value = row.id
  editing.project_name = row.project_name
  editing.client_name = row.client_name
  editing.status = row.status
  editDialogVisible.value = true
}

async function saveProject() {
  if (!editingId.value) return
  await updateProject(editingId.value, {
    project_name: editing.project_name,
    client_name: editing.client_name,
    status: editing.status
  })
  ElMessage.success('项目已更新')
  editDialogVisible.value = false
  await loadProjects()
}

async function removeProject(projectId: number) {
  await ElMessageBox.confirm('确认删除该项目？此操作不可恢复。', '删除确认', { type: 'warning' })
  await deleteProject(projectId)
  ElMessage.success('项目已删除')
  await loadProjects()
}

onMounted(loadProjects)
</script>
