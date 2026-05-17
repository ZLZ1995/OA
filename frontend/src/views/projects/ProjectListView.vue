<template>
  <el-card class="page-card" shadow="never">
    <template #header>&#39033;&#30446;&#21015;&#34920;</template>

    <el-form label-width="120px" @submit.prevent>
      <el-row :gutter="12">
        <el-col :span="8">
          <el-form-item :label="t.projectCode">
            <el-input v-model="form.project_code" :placeholder="t.projectCodePlaceholder" />
            <div style="margin-top: 8px">
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
        <el-col :span="24">
          <el-form-item>
            <el-button type="primary" @click="onCreate">{{ t.createProject }}</el-button>
          </el-form-item>
        </el-col>
      </el-row>
    </el-form>

    <el-table :data="rows" style="margin-top: 12px" v-loading="loading">
      <el-table-column prop="project_code" :label="t.projectCode" min-width="150" />
      <el-table-column prop="project_name" :label="t.projectName" min-width="160" />
      <el-table-column prop="client_name" :label="t.clientName" min-width="160" />
      <el-table-column prop="evaluation_business_nature" :label="t.evalNature" min-width="160" />
      <el-table-column prop="report_type" :label="t.reportType" min-width="110" />
      <el-table-column prop="valuation_base_date" :label="t.baseDate" min-width="120" />
      <el-table-column prop="business_salesman" :label="t.salesman" min-width="140" />
      <el-table-column prop="project_source_display" :label="t.projectSource" min-width="100" />
      <el-table-column prop="display_project_leader_name" :label="t.projectLeader" min-width="130" />
      <el-table-column prop="contract_review_status_display" :label="t.contractReviewStatus" min-width="130" />
      <el-table-column prop="status_display" :label="t.currentStatus" min-width="120" />
      <el-table-column :label="t.actions" width="220" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link @click="goDetail(row.id)">{{ t.detail }}</el-button>
          <el-button type="warning" link @click="onArchive(row)">{{ t.archive }}</el-button>
          <el-button type="danger" link @click="onDelete(row)">{{ t.delete }}</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
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
  projectCode: '\u9879\u76ee\u7f16\u53f7',
  projectCodePlaceholder: '\u53ef\u7559\u7a7a\u81ea\u52a8\u751f\u6210',
  generateCode: '\u751f\u6210\u7f16\u53f7',
  undertakingUnit: '\u627f\u63a5\u5355\u4f4d',
  evalNature: '\u8bc4\u4f30\u4e1a\u52a1\u6027\u8d28',
  reportType: '\u62a5\u544a\u7c7b\u578b',
  projectName: '\u9879\u76ee\u540d\u79f0',
  clientName: '\u5ba2\u6237\u540d\u79f0',
  baseDate: '\u8bc4\u4f30\u57fa\u51c6\u65e5',
  salesman: '\u9879\u76ee\u627f\u63a5\u4e1a\u52a1\u5458',
  projectSource: '\u9879\u76ee\u6765\u6e90',
  departmentOne: '\u8bc4\u4f30\u4e00\u90e8',
  departmentTwo: '\u8bc4\u4f30\u4e8c\u90e8',
  projectLeader: '\u9879\u76ee\u8d1f\u8d23\u4eba',
  projectLeaderPlaceholder: '\u8bf7\u8f93\u5165\u9879\u76ee\u8d1f\u8d23\u4eba\u59d3\u540d',
  createProject: '\u65b0\u5efa\u9879\u76ee',
  contractReviewStatus: '\u5408\u540c\u5ba1\u6838\u72b6\u6001',
  currentStatus: '\u5f53\u524d\u72b6\u6001',
  actions: '\u64cd\u4f5c',
  detail: '\u8be6\u60c5',
  archive: '\u5f52\u6863',
  delete: '\u5220\u9664',
  loginExpired: '\u767b\u5f55\u72b6\u6001\u5df2\u5931\u6548\uff0c\u8bf7\u91cd\u65b0\u767b\u5f55',
  fillBasicInfo: '\u8bf7\u586b\u5199\u5b8c\u6574\u9879\u76ee\u57fa\u7840\u4fe1\u606f',
  fillSalesman: '\u8bf7\u586b\u5199\u9879\u76ee\u627f\u63a5\u4e1a\u52a1\u5458',
  fillLeader: '\u8bc4\u4f30\u4e8c\u90e8\u9879\u76ee\u5fc5\u987b\u586b\u5199\u9879\u76ee\u8d1f\u8d23\u4eba',
  created: '\u9879\u76ee\u521b\u5efa\u6210\u529f',
  noPermission: '\u65e0\u6743\u9650\u521b\u5efa\u9879\u76ee',
  paramError: '\u9879\u76ee\u53c2\u6570\u9519\u8bef\uff0c\u8bf7\u68c0\u67e5\u5fc5\u586b\u9879',
  serverError: '\u670d\u52a1\u5668\u5f02\u5e38\uff0c\u8bf7\u7a0d\u540e\u91cd\u8bd5',
  createFailed: '\u521b\u5efa\u9879\u76ee\u5931\u8d25',
  generated: '\u5df2\u751f\u6210\u9879\u76ee\u7f16\u53f7',
  generateFailed: '\u751f\u6210\u9879\u76ee\u7f16\u53f7\u5931\u8d25',
  deleteConfirmText: '\u786e\u8ba4\u5220\u9664\u8be5\u9879\u76ee\u5417\uff1f\u5220\u9664\u540e\u4e0d\u53ef\u6062\u590d\u3002',
  deleteConfirmTitle: '\u5220\u9664\u786e\u8ba4',
  deleted: '\u9879\u76ee\u5df2\u5220\u9664',
  archiveConfirmText: '\u786e\u8ba4\u5f52\u6863\u8be5\u9879\u76ee\u5417\uff1f\u5f52\u6863\u540e\u8868\u793a\u8be5\u9879\u76ee\u6d41\u7a0b\u5df2\u7ed3\u675f\uff0c\u4e0d\u518d\u8fdb\u5165\u540e\u7eed\u5de5\u5355\u529e\u7406\u8303\u56f4\u3002',
  archiveConfirmTitle: '\u5f52\u6863\u786e\u8ba4',
  archived: '\u9879\u76ee\u5df2\u5f52\u6863',
}

const u = {
  zhongqin: '\u4e2d\u52e4' as ProjectUndertakingUnit,
  zhongli: '\u4e2d\u7acb\u56fd\u9645' as ProjectUndertakingUnit,
  zhongzhong: '\u4e2d\u4f17' as ProjectUndertakingUnit,
  other: '\u5176\u4ed6' as ProjectUndertakingUnit,
}

const evaluationBusinessOptions: EvaluationBusinessNature[] = [
  '\u56fd\u6709\u8d44\u4ea7\u8bc4\u4f30\u4e1a\u52a1',
  '\u5883\u5916\u8d44\u4ea7\u8bc4\u4f30\u4e1a\u52a1',
  '\u8bc1\u5238\u671f\u8d27\u8bc4\u4f30\u4e1a\u52a1',
  '\u53f8\u6cd5\u8bc4\u4f30\u4e1a\u52a1',
  '\u91d1\u878d\u8d44\u4ea7\u8bc4\u4f30\u4e1a\u52a1',
  '\u73e0\u5b9d\u9996\u9970\u8bc4\u4f30\u4e1a\u52a1',
  '\u5176\u4ed6',
]

const reportTypeOptions: ReportType[] = ['\u8bc4\u4f30\u62a5\u544a', '\u4f30\u503c\u62a5\u544a', '\u54a8\u8be2\u62a5\u544a', '\u590d\u6838\u62a5\u544a', '\u8ffd\u6eaf\u6027\u62a5\u544a']

const auth = useAuthStore()
const router = useRouter()
const loading = ref(false)
const rows = ref<ProjectItem[]>([])
const generatingCode = ref(false)
const currentUserDisplayName = auth.user?.real_name || auth.user?.username || '\u5f53\u524d\u521b\u5efa\u4eba'

const form = reactive({
  project_code: '',
  undertaking_unit: '\u4e2d\u52e4' as ProjectUndertakingUnit,
  project_name: '',
  client_name: '',
  evaluation_business_nature: '\u56fd\u6709\u8d44\u4ea7\u8bc4\u4f30\u4e1a\u52a1' as EvaluationBusinessNature,
  report_type: '\u8bc4\u4f30\u62a5\u544a' as ReportType,
  valuation_base_date: '',
  business_salesman: '',
  project_source: 'INTERNAL' as ProjectSource,
  external_project_leader_name: '',
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
    form.project_code = ''
    form.undertaking_unit = u.zhongqin
    form.project_name = ''
    form.client_name = ''
    form.evaluation_business_nature = '\u56fd\u6709\u8d44\u4ea7\u8bc4\u4f30\u4e1a\u52a1'
    form.report_type = '\u8bc4\u4f30\u62a5\u544a'
    form.valuation_base_date = ''
    form.business_salesman = ''
    form.project_source = 'INTERNAL'
    form.external_project_leader_name = ''
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
