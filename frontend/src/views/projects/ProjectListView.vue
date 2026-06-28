<template>
  <div class="project-list-page">
    <el-card class="page-card project-list-card" shadow="never">
      <template #header>
        <div class="page-header">
          <div>
            <h2>{{ t.pageTitle }}</h2>
            <p>{{ t.pageSubtitle }}</p>
          </div>
          <el-button type="primary" @click="createVisible = true">{{ t.createProject }}</el-button>
        </div>
      </template>

      <div class="filter-bar">
        <el-input v-model="filters.keyword" :placeholder="t.keywordPlaceholder" clearable class="filter-item" />
        <el-select v-model="filters.status" :placeholder="t.currentStatus" clearable class="filter-item">
          <el-option v-for="status in statusOptions" :key="status" :label="status" :value="status" />
        </el-select>
        <el-select v-model="filters.reportType" :placeholder="t.reportType" clearable class="filter-item">
          <el-option v-for="item in reportTypeOptions" :key="item" :label="item" :value="item" />
        </el-select>
        <el-select v-model="filters.source" :placeholder="t.projectSource" clearable class="filter-item">
          <el-option :label="t.departmentOne" value="评估一部" />
          <el-option :label="t.departmentTwo" value="评估二部" />
        </el-select>
        <el-button @click="resetFilters">{{ t.reset }}</el-button>
      </div>

      <el-table :data="filteredRows" v-loading="loading" class="project-table">
        <el-table-column prop="project_code" :label="t.projectCode" min-width="150" />
        <el-table-column prop="project_name" :label="t.projectName" min-width="220" show-overflow-tooltip />
        <el-table-column prop="client_name" :label="t.clientName" min-width="180" show-overflow-tooltip />
        <el-table-column prop="report_type" :label="t.reportType" min-width="110" />
        <el-table-column prop="display_project_leader_name" :label="t.projectLeader" min-width="130" />
        <el-table-column prop="contract_review_status_display" :label="t.contractReviewStatus" min-width="130" />
        <el-table-column prop="status_display" :label="t.currentStatus" min-width="120" />
        <el-table-column :label="t.actions" width="260" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="goDetail(row.id)">{{ t.enterProject }}</el-button>
            <el-button type="warning" link @click="onArchive(row)">{{ t.archive }}</el-button>
            <el-button type="danger" link @click="onDelete(row)">{{ t.delete }}</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="createVisible" :title="t.createProject" width="920px">
      <el-form label-width="120px" @submit.prevent>
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item :label="t.projectCode">
              <el-input v-model="form.project_code" :placeholder="t.projectCodePlaceholder" />
              <div class="inline-action">
                <el-button text type="primary" :loading="generatingCode" @click="onGenerateCode">{{ t.generateCode }}</el-button>
              </div>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item :label="t.undertakingUnit">
              <el-select v-model="form.undertaking_unit" style="width: 100%">
                <el-option :label="u.zhongqin" :value="u.zhongqin" />
                <el-option :label="u.zhongli" :value="u.zhongli" />
                <el-option :label="u.zhongzhong" :value="u.zhongzhong" />
                <el-option :label="u.other" :value="u.other" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item :label="t.evalNature">
              <el-select v-model="form.evaluation_business_nature" style="width: 100%">
                <el-option v-for="item in evaluationBusinessOptions" :key="item" :label="item" :value="item" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item :label="t.reportType">
              <el-select v-model="form.report_type" style="width: 100%">
                <el-option v-for="item in reportTypeOptions" :key="item" :label="item" :value="item" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item :label="t.projectName">
              <el-input v-model="form.project_name" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item :label="t.clientName">
              <el-input v-model="form.client_name" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item :label="t.baseDate">
              <el-date-picker v-model="form.valuation_base_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item :label="t.salesman">
              <el-input v-model="form.business_salesman" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item :label="t.projectSource">
              <el-radio-group v-model="form.project_source">
                <el-radio-button value="INTERNAL">{{ t.departmentOne }}</el-radio-button>
                <el-radio-button value="EXTERNAL">{{ t.departmentTwo }}</el-radio-button>
              </el-radio-group>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item :label="t.projectLeader">
              <el-input
                v-if="form.project_source === 'EXTERNAL'"
                v-model="form.external_project_leader_name"
                :placeholder="t.projectLeaderPlaceholder"
              />
              <el-input v-else :model-value="currentUserDisplayName" disabled />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">{{ t.cancel }}</el-button>
        <el-button type="primary" @click="onCreate">{{ t.createProject }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import {
  archiveProject,
  createProject,
  deleteProject,
  generateProjectCode,
  listProjects,
  type EvaluationBusinessNature,
  type ProjectItem,
  type ProjectSource,
  type ProjectUndertakingUnit,
  type ReportType,
} from '@/api/projects'
import { useAuthStore } from '@/store/auth'

const t = {
  pageTitle: '项目列表',
  pageSubtitle: '按项目快速进入流程，创建入口收纳在右上角。',
  projectCode: '项目编号',
  projectCodePlaceholder: '可留空自动生成',
  generateCode: '生成编号',
  undertakingUnit: '承接单位',
  evalNature: '评估业务性质',
  reportType: '报告类型',
  projectName: '项目名称',
  clientName: '客户名称',
  baseDate: '评估基准日',
  salesman: '项目承接业务员',
  projectSource: '项目来源',
  departmentOne: '评估一部',
  departmentTwo: '评估二部',
  projectLeader: '项目负责人',
  projectLeaderPlaceholder: '请输入项目负责人姓名',
  createProject: '新建项目',
  contractReviewStatus: '合同审核状态',
  currentStatus: '当前状态',
  actions: '操作',
  enterProject: '进入项目',
  archive: '归档',
  delete: '删除',
  reset: '重置',
  cancel: '取消',
  keywordPlaceholder: '搜索项目编号 / 名称 / 客户名称',
  loginExpired: '登录状态已失效，请重新登录',
  fillBasicInfo: '请填写完整项目基础信息',
  fillSalesman: '请填写项目承接业务员',
  fillLeader: '评估二部项目必须填写项目负责人',
  created: '项目创建成功',
  noPermission: '无权限创建项目',
  paramError: '项目参数错误，请检查必填项',
  serverError: '服务器异常，请稍后重试',
  createFailed: '创建项目失败',
  generated: '已生成项目编号',
  generateFailed: '生成项目编号失败',
  deleteConfirmText: '确认删除该项目吗？删除后不可恢复。',
  deleteConfirmTitle: '删除确认',
  deleted: '项目已删除',
  archiveConfirmText: '确认归档该项目吗？归档后表示该项目流程已结束，不再进入后续工单办理范围。',
  archiveConfirmTitle: '归档确认',
  archived: '项目已归档',
}

const u = {
  zhongqin: '中勤' as ProjectUndertakingUnit,
  zhongli: '中立国际' as ProjectUndertakingUnit,
  zhongzhong: '中众' as ProjectUndertakingUnit,
  other: '其他' as ProjectUndertakingUnit,
}

const evaluationBusinessOptions: EvaluationBusinessNature[] = [
  '国有资产评估业务',
  '境外资产评估业务',
  '证券期货评估业务',
  '司法评估业务',
  '金融资产评估业务',
  '珠宝首饰评估业务',
  '其他',
]

const reportTypeOptions: ReportType[] = ['评估报告', '估值报告', '咨询报告', '复核报告', '追溯性报告']

const auth = useAuthStore()
const router = useRouter()
const loading = ref(false)
const rows = ref<ProjectItem[]>([])
const createVisible = ref(false)
const generatingCode = ref(false)
const currentUserDisplayName = auth.user?.real_name || auth.user?.username || '当前创建人'

const filters = reactive({
  keyword: '',
  status: '',
  reportType: '',
  source: '',
})

const form = reactive({
  project_code: '',
  undertaking_unit: '中勤' as ProjectUndertakingUnit,
  project_name: '',
  client_name: '',
  evaluation_business_nature: '国有资产评估业务' as EvaluationBusinessNature,
  report_type: '评估报告' as ReportType,
  valuation_base_date: '',
  business_salesman: '',
  project_source: 'INTERNAL' as ProjectSource,
  external_project_leader_name: '',
})

const statusOptions = computed(() =>
  Array.from(new Set(rows.value.map(item => item.status_display).filter((value): value is string => Boolean(value)))),
)

const filteredRows = computed(() =>
  rows.value.filter(row => {
    const keyword = filters.keyword.trim().toLowerCase()
    const matchesKeyword =
      !keyword ||
      row.project_code?.toLowerCase().includes(keyword) ||
      row.project_name?.toLowerCase().includes(keyword) ||
      row.client_name?.toLowerCase().includes(keyword)
    const matchesStatus = !filters.status || row.status_display === filters.status
    const matchesType = !filters.reportType || row.report_type === filters.reportType
    const matchesSource = !filters.source || row.project_source_display === filters.source
    return matchesKeyword && matchesStatus && matchesType && matchesSource
  }),
)

function resetForm() {
  form.project_code = ''
  form.undertaking_unit = u.zhongqin
  form.project_name = ''
  form.client_name = ''
  form.evaluation_business_nature = '国有资产评估业务'
  form.report_type = '评估报告'
  form.valuation_base_date = ''
  form.business_salesman = ''
  form.project_source = 'INTERNAL'
  form.external_project_leader_name = ''
}

function resetFilters() {
  filters.keyword = ''
  filters.status = ''
  filters.reportType = ''
  filters.source = ''
}

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
    ElMessage.success(t.generated)
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || t.generateFailed)
  } finally {
    generatingCode.value = false
  }
}

async function onCreate() {
  const currentUser = auth.user ?? (await auth.ensureUserLoaded())
  if (!currentUser?.id) {
    auth.clearAuth()
    ElMessage.error(t.loginExpired)
    await router.push('/login')
    return
  }

  if (!form.project_name || !form.client_name || !form.undertaking_unit || !form.report_type) {
    ElMessage.warning(t.fillBasicInfo)
    return
  }
  if (!form.business_salesman.trim()) {
    ElMessage.warning(t.fillSalesman)
    return
  }
  if (form.project_source === 'EXTERNAL' && !form.external_project_leader_name.trim()) {
    ElMessage.warning(t.fillLeader)
    return
  }

  try {
    const projectCode = form.project_code.trim()
    await createProject({
      ...(projectCode ? { project_code: projectCode } : {}),
      undertaking_unit: form.undertaking_unit,
      project_name: form.project_name,
      client_name: form.client_name,
      evaluation_business_nature: form.evaluation_business_nature,
      report_type: form.report_type,
      valuation_base_date: form.valuation_base_date || undefined,
      business_salesman: form.business_salesman.trim(),
      project_source: form.project_source,
      external_project_leader_name: form.project_source === 'EXTERNAL' ? form.external_project_leader_name.trim() : undefined,
      business_user_id: currentUser.id,
      project_leader_id: currentUser.id,
    })
    ElMessage.success(t.created)
    createVisible.value = false
    resetForm()
    await loadProjects()
  } catch (error: any) {
    const status = error?.response?.status
    if (status === 401) {
      auth.clearAuth()
      ElMessage.error(t.loginExpired)
      await router.push('/login')
      return
    }
    if (status === 403) {
      ElMessage.error(t.noPermission)
      return
    }
    if (status === 422) {
      ElMessage.error(t.paramError)
      return
    }
    if (status >= 500) {
      ElMessage.error(t.serverError)
      return
    }
    ElMessage.error(error?.response?.data?.detail || t.createFailed)
  }
}

async function onDelete(row: ProjectItem) {
  await ElMessageBox.confirm(t.deleteConfirmText, t.deleteConfirmTitle, { type: 'warning' })
  await deleteProject(row.id)
  ElMessage.success(t.deleted)
  await loadProjects()
}

async function onArchive(row: ProjectItem) {
  await ElMessageBox.confirm(t.archiveConfirmText, t.archiveConfirmTitle, { type: 'warning' })
  await archiveProject(row.id)
  ElMessage.success(t.archived)
  await loadProjects()
}

function goDetail(projectId: number) {
  router.push(`/projects/${projectId}`)
}

onMounted(loadProjects)
</script>

<style scoped>
.project-list-page {
  display: grid;
  gap: 16px;
}

.project-list-card :deep(.el-card__header) {
  padding-bottom: 12px;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.page-header h2,
.page-header p {
  margin: 0;
}

.page-header h2 {
  font-size: 20px;
  color: #153a63;
}

.page-header p {
  margin-top: 6px;
  color: #64748b;
  font-size: 13px;
}

.filter-bar {
  display: grid;
  grid-template-columns: minmax(220px, 1.5fr) repeat(3, minmax(160px, 1fr)) auto;
  gap: 12px;
  margin-bottom: 16px;
}

.filter-item {
  width: 100%;
}

.project-table :deep(.el-button + .el-button) {
  margin-left: 8px;
}

.inline-action {
  margin-top: 8px;
}

@media (max-width: 960px) {
  .page-header {
    flex-direction: column;
    align-items: stretch;
  }

  .filter-bar {
    grid-template-columns: 1fr;
  }
}
</style>
