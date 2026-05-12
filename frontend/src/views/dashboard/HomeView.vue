<template>
  <div class="workbench-page">
    <div class="workbench-hero">
      <div>
        <p>中勤资产评估有限公司</p>
        <h1>中勤资产评估项目流程管理系统</h1>
      </div>
      <el-tag effect="plain" type="primary">流程工作台</el-tag>
    </div>

    <div class="workbench-grid">
      <el-card class="create-card" shadow="never">
        <template #header>项目创建区</template>
        <el-form label-width="100px">
          <el-form-item label="承接单位">
            <el-select v-model="form.undertaking_unit">
              <el-option label="中勤" value="中勤" />
              <el-option label="中联国际" value="中联国际" />
              <el-option label="中证" value="中证" />
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
          <el-form-item label="报告类型">
            <el-select v-model="form.report_type">
              <el-option label="评估报告" value="评估报告" />
              <el-option label="估值报告" value="估值报告" />
              <el-option label="咨询报告" value="咨询报告" />
            </el-select>
          </el-form-item>
          <el-form-item label="项目承接业务员">
            <el-input v-model="form.business_salesman" />
          </el-form-item>
          <el-form-item label="项目来源">
            <el-radio-group v-model="form.project_source">
              <el-radio-button label="INTERNAL">内部</el-radio-button>
              <el-radio-button label="EXTERNAL">外部</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item v-if="form.project_source === 'EXTERNAL'" label="外部负责人">
            <el-input v-model="form.external_project_leader_name" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="onCreate">创建项目</el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <el-card class="todo-card" shadow="never">
        <template #header>待办项目</template>
        <el-table class="wide-table" :data="todoProjects" size="small" table-layout="fixed">
          <el-table-column prop="project_no" label="项目编号" width="118" show-overflow-tooltip />
          <el-table-column prop="project_name" label="项目名称" min-width="96" show-overflow-tooltip />
          <el-table-column prop="client_name" label="客户名称" min-width="120" show-overflow-tooltip />
          <el-table-column prop="project_leader_name" label="项目负责人" width="92" show-overflow-tooltip />
          <el-table-column prop="transfer_user_name" label="转交人" width="82" show-overflow-tooltip />
          <el-table-column prop="current_step" label="当前步骤" width="96" show-overflow-tooltip />
          <el-table-column prop="todo_action" label="待办事项" min-width="116" show-overflow-tooltip />
          <el-table-column label="操作" width="132">
            <template #default="{ row }">
              <el-button link type="primary" @click="goProject(row.id)">进入项目</el-button>
              <el-button v-if="row.can_approve_termination" link type="danger" @click="approveTermination(row)">允许终止/废止</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-card class="my-card" shadow="never">
        <template #header>我的项目</template>
        <el-table class="wide-table" :data="myProjects" size="small" table-layout="fixed">
          <el-table-column prop="project_no" label="项目编号" width="132" show-overflow-tooltip />
          <el-table-column prop="project_name" label="项目名称" min-width="130" show-overflow-tooltip />
          <el-table-column prop="client_name" label="客户名称" min-width="130" show-overflow-tooltip />
          <el-table-column prop="current_step" label="当前步骤" width="108" show-overflow-tooltip />
          <el-table-column prop="status_display" label="状态" width="96" show-overflow-tooltip />
          <el-table-column label="操作" width="318">
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
  type ProjectUndertakingUnit,
  type ReportType,
  type ProjectSource
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
  client_name: '',
  report_type: '评估报告' as ReportType,
  business_salesman: '',
  project_source: 'INTERNAL' as ProjectSource,
  external_project_leader_name: ''
})

async function load() {
  const data = await getWorkbench()
  myProjects.value = data.my_projects
  todoProjects.value = data.todo_projects
}

async function onCreate() {
  const user = auth.user ?? await auth.ensureUserLoaded()
  if (!user?.id) return
  if (!form.project_name || !form.client_name || !form.business_salesman.trim()) {
    ElMessage.warning('请填写完整项目创建信息')
    return
  }
  if (form.project_source === 'EXTERNAL' && !form.external_project_leader_name.trim()) {
    ElMessage.warning('外部项目必须填写外部项目负责人姓名')
    return
  }

  const created = await createProject({
    undertaking_unit: form.undertaking_unit,
    project_name: form.project_name,
    client_name: form.client_name,
    report_type: form.report_type,
    business_salesman: form.business_salesman.trim(),
    project_source: form.project_source,
    external_project_leader_name: form.project_source === 'EXTERNAL' ? form.external_project_leader_name.trim() : undefined,
    business_user_id: user.id,
    project_leader_id: user.id
  })
  form.project_code = created.project_code
  form.project_name = ''
  form.client_name = ''
  form.business_salesman = ''
  form.project_source = 'INTERNAL'
  form.external_project_leader_name = ''
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
.workbench-page {
  display: grid;
  gap: 16px;
}

.workbench-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 86px;
  padding: 22px 24px;
  border: 1px solid var(--zq-border);
  border-radius: 8px;
  background:
    linear-gradient(135deg, rgba(31, 78, 121, 0.94), rgba(23, 63, 99, 0.9)),
    var(--zq-primary);
  color: #fff;
  box-shadow: 0 10px 28px rgba(31, 78, 121, 0.12);
}

.workbench-hero p,
.workbench-hero h1 {
  margin: 0;
}

.workbench-hero p {
  color: rgba(255, 255, 255, 0.72);
  font-size: 13px;
  font-weight: 600;
}

.workbench-hero h1 {
  margin-top: 8px;
  font-size: 24px;
  line-height: 1.3;
}

.workbench-hero :deep(.el-tag) {
  color: #fff;
  border-color: rgba(255, 255, 255, 0.45);
  background: rgba(255, 255, 255, 0.12);
}

.workbench-grid {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  grid-template-areas:
    "create todo"
    "mine mine";
  gap: 14px;
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

.wide-table :deep(.el-table__inner-wrapper),
.wide-table :deep(.el-scrollbar__view),
.wide-table :deep(table) {
  width: 100% !important;
}

.wide-table :deep(.cell) {
  white-space: nowrap;
  padding-left: 8px;
  padding-right: 8px;
}

.wide-table :deep(th.el-table__cell) {
  height: 42px;
}

.wide-table :deep(td.el-table__cell) {
  height: 44px;
}

.wide-table :deep(.el-button + .el-button) {
  margin-left: 8px;
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
