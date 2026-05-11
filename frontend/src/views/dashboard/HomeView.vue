<template>
  <div class="workbench-grid">
    <el-card class="create-card" shadow="never">
      <template #header>项目创建区</template>
      <el-form label-width="88px">
        <el-form-item label="承接单位">
          <el-select v-model="form.undertaking_unit">
            <el-option label="中勤" value="中勤" />
            <el-option label="中立国际" value="中立国际" />
            <el-option label="中众" value="中众" />
            <el-option label="其他" value="其他" />
          </el-select>
        </el-form-item>
        <el-form-item label="项目编号">
          <el-input v-model="form.project_code" placeholder="系统自动生成" readonly disabled />
        </el-form-item>
        <el-form-item label="项目名称">
          <el-input v-model="form.project_name" />
        </el-form-item>
        <el-form-item label="客户名称">
          <el-input v-model="form.client_name" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="onCreate">创建项目</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="todo-card" shadow="never">
      <template #header>待办项目</template>
      <el-table class="wide-table" :data="todoProjects" size="small">
        <el-table-column prop="project_no" label="项目编号" min-width="120" />
        <el-table-column prop="project_name" label="项目名称" min-width="130" show-overflow-tooltip />
        <el-table-column prop="client_name" label="客户名称" min-width="120" show-overflow-tooltip />
        <el-table-column prop="project_leader_name" label="项目负责人" min-width="110" show-overflow-tooltip />
        <el-table-column prop="transfer_user_name" label="转交人" min-width="100" show-overflow-tooltip />
        <el-table-column prop="current_step" label="当前步骤" min-width="100" />
        <el-table-column prop="todo_action" label="待办事项" min-width="140" show-overflow-tooltip />
        <el-table-column label="操作" width="108" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="goProject(row.id)">进入项目</el-button>
            <el-button v-if="row.can_approve_termination" link type="danger" @click="approveTermination(row)">允许终止/废止</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card class="my-card" shadow="never">
      <template #header>我的项目</template>
      <el-table class="wide-table" :data="myProjects" size="small">
        <el-table-column prop="project_no" label="项目编号" min-width="140" />
        <el-table-column prop="project_name" label="项目名称" min-width="180" show-overflow-tooltip />
        <el-table-column prop="client_name" label="客户名称" min-width="150" show-overflow-tooltip />
        <el-table-column prop="current_step" label="当前步骤" min-width="110" />
        <el-table-column prop="status_display" label="状态" min-width="100" />
        <el-table-column label="操作" width="340" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="goProject(row.id)">进入项目</el-button>
            <el-button link type="primary" :disabled="!row.can_edit" @click="editProject(row)">编辑</el-button>
            <el-button link type="warning" :disabled="!row.can_archive" @click="archive(row.id)">归档</el-button>
            <el-button link type="danger" :disabled="!row.can_request_termination" @click="requestTermination(row)">项目终止/废止</el-button>
            <el-button link type="danger" :disabled="!row.can_delete" @click="remove(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import { getWorkbench, type WorkbenchProjectItem } from '@/api/workbench'
import {
  archiveProject,
  approveProjectTermination,
  createProject,
  deleteProject,
  requestProjectTermination,
  updateProject,
  type ProjectUndertakingUnit
} from '@/api/projects'
import { useAuthStore } from '@/store/auth'

const router = useRouter()
const auth = useAuthStore()
const myProjects = ref<WorkbenchProjectItem[]>([])
const todoProjects = ref<WorkbenchProjectItem[]>([])

const form = reactive({
  undertaking_unit: '中勤' as ProjectUndertakingUnit,
  project_code: '',
  project_name: '',
  client_name: ''
})

async function load() {
  const data = await getWorkbench()
  myProjects.value = data.my_projects
  todoProjects.value = data.todo_projects
}

async function onCreate() {
  const user = auth.user ?? await auth.ensureUserLoaded()
  if (!user?.id) return

  const created = await createProject({
    undertaking_unit: form.undertaking_unit,
    project_name: form.project_name,
    client_name: form.client_name,
    business_user_id: user.id,
    project_leader_id: user.id
  })
  form.project_code = created.project_code
  form.project_name = ''
  form.client_name = ''
  ElMessage.success('项目创建成功')
  await load()
}

async function editProject(row: WorkbenchProjectItem) {
  await updateProject(row.id, { project_name: row.project_name, client_name: row.client_name })
  ElMessage.success('项目已更新')
  await load()
}

async function archive(id: number) {
  await archiveProject(id)
  ElMessage.success('项目已归档')
  await load()
}

async function requestTermination(row: WorkbenchProjectItem) {
  const { value } = await ElMessageBox.prompt(
    '请填写项目终止/废止原因，保存后项目将锁定并发送给管理员审核。',
    '项目终止/废止',
    {
      confirmButtonText: '保存并发送给管理员',
      cancelButtonText: '取消',
      inputType: 'textarea',
      inputPlaceholder: '请输入终止/废止原因',
      inputValidator: value => Boolean(value?.trim()) || '请填写项目终止/废止原因'
    }
  )
  await requestProjectTermination(row.id, value.trim())
  ElMessage.success('终止/废止申请已发送给管理员')
  await load()
}

async function approveTermination(row: WorkbenchProjectItem) {
  await ElMessageBox.alert(row.termination_reason || '未填写原因', '项目终止/废止原因', {
    confirmButtonText: '允许终止/废止'
  })
  await approveProjectTermination(row.id)
  ElMessage.success('已允许终止/废止，项目方现在可以归档')
  await load()
}

async function remove(id: number) {
  await deleteProject(id)
  ElMessage.success('项目已删除')
  await load()
}

function goProject(id: number) {
  router.push(`/projects/${id}/flow`)
}

onMounted(load)
</script>

<style scoped>
.workbench-grid {
  display: grid;
  grid-template-columns: minmax(320px, 380px) minmax(0, 1fr);
  grid-template-areas:
    "create todo"
    "mine mine";
  gap: 16px;
  align-items: start;
}

.create-card {
  grid-area: create;
}

.todo-card {
  grid-area: todo;
}

.my-card {
  grid-area: mine;
}

.wide-table {
  width: 100%;
}

.wide-table :deep(.cell) {
  white-space: nowrap;
}

.wide-table :deep(.el-button + .el-button) {
  margin-left: 10px;
}

@media (max-width: 960px) {
  .workbench-grid {
    grid-template-columns: 1fr;
    grid-template-areas:
      "create"
      "todo"
      "mine";
  }
}
</style>
