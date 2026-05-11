<template>
  <el-card class="page-card" shadow="never">
    <template #header>项目列表</template>
    <el-form inline @submit.prevent>
      <el-form-item label="项目编号">
        <el-input v-model="form.project_code" placeholder="可留空自动生成" />
        <div style="margin-top: 8px">
          <el-button text type="primary" :loading="generatingCode" @click="onGenerateCode">生成编号</el-button>
        </div>
      </el-form-item>
      <el-form-item label="承接单位">
        <el-select v-model="form.undertaking_unit" style="width: 160px">
          <el-option label="中勤" value="中勤" />
          <el-option label="中立国际" value="中立国际" />
          <el-option label="中众" value="中众" />
          <el-option label="其他" value="其他" />
        </el-select>
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
      <el-table-column prop="status_display" label="状态显示" />
            <el-table-column label="操作" width="200">
        <template #default="{ row }">
          <el-button type="warning" link @click="onArchive(row)">归档</el-button>
          <el-button type="danger" link @click="onDelete(row)">删除</el-button>
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
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import {
  archiveProject,
  createProject,
  deleteProject,
  generateProjectCode,
  listProjects,
  updateProject,
  type ProjectItem
} from '@/api/projects'
import { useAuthStore } from '@/store/auth'

const auth = useAuthStore()
const router = useRouter()
const loading = ref(false)
const rows = ref<ProjectItem[]>([])
const generatingCode = ref(false)
const editDialogVisible = ref(false)
const editing = reactive({
  id: 0,
  project_name: '',
  client_name: ''
})

const form = reactive({
  project_code: '',
  undertaking_unit: '中勤' as '中勤' | '中立国际' | '中众' | '其他',
  project_name: '',
  client_name: ''
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



async function onGenerateCode() {
  generatingCode.value = true
  try {
    const data = await generateProjectCode(form.undertaking_unit)
    form.project_code = data.project_code
    ElMessage.success('已生成项目编号')
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '生成项目编号失败')
  } finally {
    generatingCode.value = false
  }
}

async function onCreate() {
  const currentUser = auth.user ?? (await auth.ensureUserLoaded())
  if (!currentUser?.id) {
    auth.clearAuth()
    ElMessage.error('登录状态已失效，请重新登录')
    await router.push('/login')
    return
  }
  if (!form.project_name || !form.client_name || !form.undertaking_unit) {
    ElMessage.warning('请填写完整项目信息')
    return
  }
  try {
    const projectCode = form.project_code.trim()
    await createProject({
      ...(projectCode ? { project_code: projectCode } : {}),
      undertaking_unit: form.undertaking_unit,
      project_name: form.project_name,
      client_name: form.client_name,
      business_user_id: currentUser.id,
      project_leader_id: currentUser.id
    })
    ElMessage.success('项目创建成功')
    form.project_code = ''
    form.undertaking_unit = '中勤'
    form.project_name = ''
    form.client_name = ''
    await loadProjects()
  } catch (error: any) {
    const status = error?.response?.status
    if (status === 401) {
      auth.clearAuth()
      ElMessage.error('登录状态已失效，请重新登录')
      await router.push('/login')
      return
    }
    if (status === 403) {
      ElMessage.error('无权限创建项目')
      return
    }
    if (status === 422) {
      ElMessage.error('项目参数错误，请检查必填项')
      return
    }
    if (status >= 500) {
      ElMessage.error('服务器异常，请稍后重试')
      return
    }
    ElMessage.error(error?.response?.data?.detail || '创建项目失败')
  }
}

async function onDelete(row: ProjectItem) {
  await ElMessageBox.confirm('确认删除该项目吗？删除后不可恢复。', '删除确认', { type: 'warning' })
  await deleteProject(row.id)
  ElMessage.success('项目已删除')
  await loadProjects()
}

async function onArchive(row: ProjectItem) {
  await ElMessageBox.confirm(
    '确认归档该项目吗？归档后表示该项目流程已结束，项目将不再进入后续工单管理选择范围。',
    '归档确认',
    { type: 'warning' }
  )
  await archiveProject(row.id)
  ElMessage.success('项目已归档')
  await loadProjects()
}

async function saveProject() {
  if (!editing.id) return
  await updateProject(editing.id, {
    project_name: editing.project_name,
    client_name: editing.client_name
  })
  editDialogVisible.value = false
  ElMessage.success('项目已更新')
  await loadProjects()
}

onMounted(loadProjects)
</script>
