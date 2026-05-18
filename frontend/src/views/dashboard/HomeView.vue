<template>
  <div class="workbench-page">
    <div class="workbench-hero">
      <div>
        <p>??????????</p>
        <h1>??????????????</h1>
      </div>
      <el-tag effect="plain" type="primary">?????</el-tag>
    </div>

    <div class="workbench-grid">
      <el-card class="create-card" shadow="never">
        <template #header>?????</template>
        <el-form label-width="110px">
          <el-form-item label="????">
            <el-select v-model="form.undertaking_unit">
              <el-option label="??" value="??" />
              <el-option label="????" value="????" />
              <el-option label="??" value="??" />
              <el-option label="??" value="??" />
            </el-select>
          </el-form-item>
          <el-form-item label="????">
            <el-input v-model="form.project_code" placeholder="??????" readonly disabled />
          </el-form-item>
          <el-form-item label="????">
            <el-input v-model="form.project_name" />
          </el-form-item>
          <el-form-item label="????">
            <el-input v-model="form.client_name" />
          </el-form-item>
          <el-form-item label="??????">
            <el-select v-model="form.evaluation_business_nature" style="width: 100%">
              <el-option v-for="item in evaluationBusinessOptions" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
          <el-form-item label="????">
            <el-select v-model="form.report_type">
              <el-option v-for="item in reportTypeOptions" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
          <el-form-item label="?????">
            <el-date-picker
              v-model="form.valuation_base_date"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="???????"
              style="width: 100%"
            />
          </el-form-item>
          <el-form-item label="???????">
            <el-input v-model="form.business_salesman" />
          </el-form-item>
          <el-form-item label="????">
            <el-radio-group v-model="form.project_source">
              <el-radio-button value="INTERNAL">????</el-radio-button>
              <el-radio-button value="EXTERNAL">????</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="?????">
            <el-input
              v-if="form.project_source === 'EXTERNAL'"
              v-model="form.external_project_leader_name"
              placeholder="??????????"
            />
            <el-input v-else :model-value="currentUserDisplayName" disabled />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="onCreate">????</el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <el-card class="todo-card" shadow="never">
        <template #header>????</template>
        <el-table class="wide-table" :data="todoProjects" size="small" table-layout="fixed">
          <el-table-column prop="project_no" label="????" width="118" show-overflow-tooltip />
          <el-table-column prop="project_name" label="????" min-width="96" show-overflow-tooltip />
          <el-table-column prop="client_name" label="????" min-width="120" show-overflow-tooltip />
          <el-table-column prop="project_leader_name" label="?????" width="92" show-overflow-tooltip />
          <el-table-column prop="transfer_user_name" label="???" width="82" show-overflow-tooltip />
          <el-table-column prop="current_step" label="????" width="96" show-overflow-tooltip />
          <el-table-column prop="todo_action" label="????" min-width="116" show-overflow-tooltip />
          <el-table-column label="??" width="200">
            <template #default="{ row }">
              <el-button v-if="row.can_approve_delete" link type="danger" @click="goDeleteApprovals">??????</el-button>
              <template v-else>
                <el-button link type="primary" @click="goProject(row.id, row)">????</el-button>
                <el-button link type="success" @click="goNotifications(row.id)">????</el-button>
              </template>
              <el-button v-if="row.can_approve_termination" link type="danger" @click="approveTermination(row)">????/??</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-card class="my-card" shadow="never">
        <template #header>????</template>
        <el-table class="wide-table" :data="myProjects" size="small" table-layout="fixed">
          <el-table-column prop="project_no" label="????" width="132" show-overflow-tooltip />
          <el-table-column prop="project_name" label="????" min-width="130" show-overflow-tooltip />
          <el-table-column prop="client_name" label="????" min-width="130" show-overflow-tooltip />
          <el-table-column prop="current_step" label="????" width="108" show-overflow-tooltip />
          <el-table-column prop="status_display" label="??" width="110" show-overflow-tooltip />
          <el-table-column label="??" width="420">
            <template #default="{ row }">
              <el-button link type="primary" @click="goProject(row.id)">????</el-button>
              <el-button link type="success" @click="goNotifications(row.id)">????</el-button>
              <el-button link type="primary" :disabled="!row.can_edit" @click="editProject(row)">??</el-button>
              <el-button link type="warning" :disabled="!row.can_archive" @click="archive(row.id)">??</el-button>
              <el-button link type="danger" :disabled="!row.can_request_termination" @click="requestTermination(row)">????/??</el-button>
              <el-button link type="danger" @click="remove(row)">??</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>

    <el-dialog v-model="editVisible" title="????" width="560px">
      <el-form label-width="120px">
        <el-form-item label="????">
          <el-select v-model="editForm.undertaking_unit" style="width: 100%">
            <el-option label="??" value="??" />
            <el-option label="????" value="????" />
            <el-option label="??" value="??" />
            <el-option label="??" value="??" />
          </el-select>
        </el-form-item>
        <el-form-item label="????">
          <el-input v-model="editForm.project_name" />
        </el-form-item>
        <el-form-item label="????">
          <el-input v-model="editForm.client_name" />
        </el-form-item>
        <el-form-item label="??????">
          <el-select v-model="editForm.evaluation_business_nature" style="width: 100%">
            <el-option v-for="item in evaluationBusinessOptions" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="????">
          <el-select v-model="editForm.report_type" style="width: 100%">
            <el-option v-for="item in reportTypeOptions" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="?????">
          <el-date-picker
            v-model="editForm.valuation_base_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="???????"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="???????">
          <el-input v-model="editForm.business_salesman" />
        </el-form-item>
        <el-form-item label="????">
          <el-radio-group v-model="editForm.project_source">
            <el-radio-button value="INTERNAL">????</el-radio-button>
            <el-radio-button value="EXTERNAL">????</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="?????">
          <el-input
            v-if="editForm.project_source === 'EXTERNAL'"
            v-model="editForm.external_project_leader_name"
            placeholder="??????????"
          />
          <el-input v-else :model-value="currentUserDisplayName" disabled />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">??</el-button>
        <el-button type="primary" :loading="editLoading" @click="saveProject">???????</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="deleteDialogVisible" title="??????" width="520px">
      <el-form label-width="120px">
        <el-form-item label="???????">
          <el-select v-model="deleteDraft.approver_user_id" style="width: 100%">
            <el-option
              v-for="item in deleteAdminOptions"
              :key="item.id"
              :label="item.real_name"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="????">
          <el-input v-model="deleteDraft.reason" type="textarea" :rows="3" placeholder="????????" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="deleteDialogVisible = false">??</el-button>
        <el-button type="primary" :loading="deleteSubmitting" @click="submitDeleteRequest">??????</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import { getWorkbench, type WorkbenchProjectItem } from '@/api/workbench'
import { createProjectDeleteRequest } from '@/api/projectDeleteRequests'
import { listUserCandidates, type UserItem } from '@/api/users'
import {
  archiveProject,
  approveProjectTermination,
  createProject,
  deleteProject,
  getProject,
  requestProjectTermination,
  updateProject,
  type EvaluationBusinessNature,
  type ProjectItem,
  type ProjectSource,
  type ProjectUndertakingUnit,
  type ReportType,
} from '@/api/projects'
import { useAuthStore } from '@/store/auth'

const evaluationBusinessOptions: EvaluationBusinessNature[] = [
  '????????',
  '????????',
  '????????',
  '??????',
  '????????',
  '????????',
  '??',
]

const reportTypeOptions: ReportType[] = ['????', '????', '????', '????', '?????']

const router = useRouter()
const auth = useAuthStore()
const myProjects = ref<WorkbenchProjectItem[]>([])
const todoProjects = ref<WorkbenchProjectItem[]>([])
const editVisible = ref(false)
const editLoading = ref(false)
const editingProjectId = ref<number>()
const deleteDialogVisible = ref(false)
const deleteSubmitting = ref(false)
const deleteTargetProjectId = ref<number>()
const deleteTargetProjectName = ref('')
const deleteAdminOptions = ref<UserItem[]>([])

const currentUserDisplayName = auth.user?.real_name || auth.user?.username || '?????'

const form = reactive({
  undertaking_unit: '??' as ProjectUndertakingUnit,
  project_code: '',
  project_name: '',
  client_name: '',
  evaluation_business_nature: '????????' as EvaluationBusinessNature,
  report_type: '????' as ReportType,
  valuation_base_date: '',
  business_salesman: '',
  project_source: 'INTERNAL' as ProjectSource,
  external_project_leader_name: '',
})

const editForm = reactive({
  undertaking_unit: '??' as ProjectUndertakingUnit,
  project_name: '',
  client_name: '',
  evaluation_business_nature: '????????' as EvaluationBusinessNature,
  report_type: '????' as ReportType,
  valuation_base_date: '',
  business_salesman: '',
  project_source: 'INTERNAL' as ProjectSource,
  external_project_leader_name: '',
})

const deleteDraft = reactive({
  approver_user_id: undefined as number | undefined,
  reason: '',
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
    ElMessage.warning('???????????')
    return
  }
  if (form.project_source === 'EXTERNAL' && !form.external_project_leader_name.trim()) {
    ElMessage.warning('???????????????')
    return
  }

  const created = await createProject({
    undertaking_unit: form.undertaking_unit,
    project_name: form.project_name,
    client_name: form.client_name,
    evaluation_business_nature: form.evaluation_business_nature,
    report_type: form.report_type,
    valuation_base_date: form.valuation_base_date || undefined,
    business_salesman: form.business_salesman.trim(),
    project_source: form.project_source,
    external_project_leader_name: form.project_source === 'EXTERNAL' ? form.external_project_leader_name.trim() : undefined,
    business_user_id: user.id,
    project_leader_id: user.id,
  })
  form.project_code = created.project_code
  form.project_name = ''
  form.client_name = ''
  form.evaluation_business_nature = '????????'
  form.business_salesman = ''
  form.valuation_base_date = ''
  form.project_source = 'INTERNAL'
  form.external_project_leader_name = ''
  ElMessage.success('??????')
  await load()
}

async function editProject(row: WorkbenchProjectItem) {
  const project = await getProject(row.id)
  fillEditForm(project)
  editingProjectId.value = row.id
  editVisible.value = true
}

async function archive(id: number) {
  await archiveProject(id)
  ElMessage.success('?????')
  await load()
}

async function requestTermination(row: WorkbenchProjectItem) {
  const { value } = await ElMessageBox.prompt(
    '???????/???????????????????????',
    '????/??',
    {
      confirmButtonText: '?????????',
      cancelButtonText: '??',
      inputType: 'textarea',
      inputPlaceholder: '?????/????',
      inputValidator: value => Boolean(value?.trim()) || '???????/????',
    },
  )
  await requestProjectTermination(row.id, value.trim())
  ElMessage.success('??/???????????')
  await load()
}

async function approveTermination(row: WorkbenchProjectItem) {
  await ElMessageBox.alert(row.termination_reason || '?????', '????/????', {
    confirmButtonText: '????/??',
  })
  await approveProjectTermination(row.id)
  ElMessage.success('?????/????????????')
  await load()
}

async function remove(row: WorkbenchProjectItem) {
  if (row.status_display === '?????') {
    ElMessage.warning('?????????')
    return
  }
  if (row.status_display === '???') {
    ElMessage.warning('?????????')
    return
  }
  try {
    await deleteProject(row.id)
    ElMessage.success('?????')
    await load()
  } catch (error: any) {
    if (error?.response?.status === 400) {
      await openDeleteDialog(row.id, row.project_name)
      return
    }
    throw error
  }
}

async function openDeleteDialog(projectId: number, projectName: string) {
  const admins = (await listUserCandidates('ADMIN')).items.filter(item => item.id !== auth.user?.id)
  if (!admins.length) {
    ElMessage.warning('????????????')
    return
  }
  deleteAdminOptions.value = admins
  deleteTargetProjectId.value = projectId
  deleteTargetProjectName.value = projectName
  deleteDraft.approver_user_id = admins[0].id
  deleteDraft.reason = ''
  deleteDialogVisible.value = true
}

async function submitDeleteRequest() {
  if (!deleteTargetProjectId.value || !deleteDraft.approver_user_id) {
    ElMessage.warning('??????????')
    return
  }
  deleteSubmitting.value = true
  try {
    const approver = deleteAdminOptions.value.find(item => item.id === deleteDraft.approver_user_id)
    await createProjectDeleteRequest(deleteTargetProjectId.value, {
      approver_user_id: deleteDraft.approver_user_id,
      reason: deleteDraft.reason.trim() || undefined,
    })
    deleteDialogVisible.value = false
    ElMessage.success(`??????${deleteTargetProjectName.value}?????????? ${approver?.real_name || ''} ??`)
    await load()
  } finally {
    deleteSubmitting.value = false
  }
}

function fillEditForm(project: ProjectItem) {
  editForm.undertaking_unit = project.undertaking_unit
  editForm.project_name = project.project_name
  editForm.client_name = project.client_name
  editForm.evaluation_business_nature = (project.evaluation_business_nature || '????????') as EvaluationBusinessNature
  editForm.report_type = project.report_type
  editForm.valuation_base_date = project.valuation_base_date || ''
  editForm.business_salesman = project.business_salesman || ''
  editForm.project_source = project.project_source
  editForm.external_project_leader_name = project.external_project_leader_name || ''
}

async function saveProject() {
  if (!editingProjectId.value) return
  if (!editForm.project_name.trim() || !editForm.client_name.trim()) {
    ElMessage.warning('????????????')
    return
  }
  if (!editForm.business_salesman.trim()) {
    ElMessage.warning('??????????')
    return
  }
  if (editForm.project_source === 'EXTERNAL' && !editForm.external_project_leader_name.trim()) {
    ElMessage.warning('???????????????')
    return
  }

  editLoading.value = true
  try {
    await updateProject(editingProjectId.value, {
      undertaking_unit: editForm.undertaking_unit,
      project_name: editForm.project_name.trim(),
      client_name: editForm.client_name.trim(),
      evaluation_business_nature: editForm.evaluation_business_nature,
      report_type: editForm.report_type,
      valuation_base_date: editForm.valuation_base_date || undefined,
      business_salesman: editForm.business_salesman.trim(),
      project_source: editForm.project_source,
      external_project_leader_name: editForm.project_source === 'EXTERNAL' ? editForm.external_project_leader_name.trim() : null,
    })
    ElMessage.success('?????')
    editVisible.value = false
    await load()
  } finally {
    editLoading.value = false
  }
}

const TODO_PANEL_PRIORITY = ['contractReview', 'review', 'signoff', 'issue', 'mailing', 'invoice', 'archive'] as const

function normalizeTodoText(value?: string | null) {
  return (value || '').trim().toUpperCase()
}

function resolveTodoPanel(row: WorkbenchProjectItem) {
  if (row.can_approve_delete || row.can_approve_termination) return 'basic'

  const currentStep = normalizeTodoText(row.current_step)
  const todoAction = normalizeTodoText(row.todo_action)
  const statusDisplay = normalizeTodoText(row.status_display)
  const combined = `${currentStep} ${todoAction} ${statusDisplay}`
  const matched = new Set<string>()

  if (combined.includes('??') && (combined.includes('??') || combined.includes('??'))) matched.add('contractReview')
  if (combined.includes('??') || combined.includes('??') || combined.includes('??') || combined.includes('??') || combined.includes('??')) matched.add('review')
  if (combined.includes('??')) matched.add('signoff')
  if (combined.includes('??') || combined.includes('??')) matched.add('issue')
  if (combined.includes('??') || combined.includes('??')) matched.add('mailing')
  if (combined.includes('??') || combined.includes('??')) matched.add('invoice')
  if (combined.includes('??') || combined.includes('??')) matched.add('archive')

  return TODO_PANEL_PRIORITY.find(item => matched.has(item))
}

function resolveTodoLabel(row: WorkbenchProjectItem) {
  return row.todo_action?.trim() || row.current_step?.trim() || ''
}

function goProject(id: number, row?: WorkbenchProjectItem) {
  if (!row) {
    router.push(`/projects/${id}/flow`)
    return
  }

  const todoPanel = row ? resolveTodoPanel(row) : undefined
  if (!todoPanel) {
    router.push(`/projects/${id}/flow`)
    return
  }

  router.push({
    path: `/projects/${id}/flow`,
    query: {
      todoPanel,
      todoLabel: resolveTodoLabel(row),
      fromTodo: '1',
    },
  })
}

function goDeleteApprovals() {
  router.push('/project-delete-approvals')
}

function goNotifications(projectId?: number) {
  if (projectId) {
    router.push({ path: '/notifications', query: { project_id: String(projectId), message_type: 'REMINDER' } })
    return
  }
  router.push('/notifications')
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
