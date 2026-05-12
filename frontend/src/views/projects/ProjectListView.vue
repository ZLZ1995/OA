<template>
  <el-card class="page-card" shadow="never">
    <template #header>项目列表</template>

    <el-form label-width="120px" @submit.prevent>
      <el-row :gutter="12">
        <el-col :span="8">
          <el-form-item label="项目编号">
            <el-input v-model="form.project_code" placeholder="可留空自动生成" />
            <div style="margin-top: 8px">
              <el-button text type="primary" :loading="generatingCode" @click="onGenerateCode">生成编号</el-button>
            </div>
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="承接单位">
            <el-select v-model="form.undertaking_unit" style="width: 100%">
              <el-option label="中勤" value="中勤" />
              <el-option label="中联国际" value="中联国际" />
              <el-option label="中众" value="中众" />
              <el-option label="其他" value="其他" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="报告类型">
            <el-select v-model="form.report_type" style="width: 100%">
              <el-option label="评估报告" value="评估报告" />
              <el-option label="估值报告" value="估值报告" />
              <el-option label="咨询报告" value="咨询报告" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="项目名称">
            <el-input v-model="form.project_name" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="客户名称">
            <el-input v-model="form.client_name" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="评估基准日">
            <el-date-picker v-model="form.valuation_base_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="项目承接业务员">
            <el-input v-model="form.business_salesman" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="项目来源">
            <el-radio-group v-model="form.project_source">
              <el-radio-button label="INTERNAL">内部项目</el-radio-button>
              <el-radio-button label="EXTERNAL">外部项目</el-radio-button>
            </el-radio-group>
          </el-form-item>
        </el-col>
        <el-col v-if="form.project_source === 'EXTERNAL'" :span="8">
          <el-form-item label="外部项目负责人">
            <el-input v-model="form.external_project_leader_name" />
          </el-form-item>
        </el-col>
        <el-col :span="24">
          <el-form-item>
            <el-button type="primary" @click="onCreate">新建项目</el-button>
          </el-form-item>
        </el-col>
      </el-row>
    </el-form>

    <el-table :data="rows" style="margin-top: 12px" v-loading="loading">
      <el-table-column prop="project_code" label="项目编号" min-width="150" />
      <el-table-column prop="project_name" label="项目名称" min-width="160" />
      <el-table-column prop="client_name" label="客户名称" min-width="160" />
      <el-table-column prop="report_type" label="报告类型" min-width="110" />
      <el-table-column prop="valuation_base_date" label="评估基准日" min-width="120" />
      <el-table-column prop="business_salesman" label="项目承接业务员" min-width="140" />
      <el-table-column prop="project_source_display" label="项目来源" min-width="100" />
      <el-table-column prop="project_leader_display_name" label="项目负责人" min-width="130" />
      <el-table-column prop="contract_review_status_display" label="合同审核状态" min-width="130" />
      <el-table-column prop="status_display" label="当前状态" min-width="120" />
      <el-table-column label="操作" width="220" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link @click="goDetail(row.id)">详情</el-button>
          <el-button type="warning" link @click="onArchive(row)">归档</el-button>
          <el-button type="danger" link @click="onDelete(row)">删除</el-button>
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
  type ProjectItem,
  type ProjectUndertakingUnit,
  type ReportType,
  type ProjectSource
} from '@/api/projects'
import { useAuthStore } from '@/store/auth'

const auth = useAuthStore()
const router = useRouter()
const loading = ref(false)
const rows = ref<ProjectItem[]>([])
const generatingCode = ref(false)

const form = reactive({
  project_code: '',
  undertaking_unit: '中勤' as ProjectUndertakingUnit,
  project_name: '',
  client_name: '',
  report_type: '评估报告' as ReportType,
  valuation_base_date: '',
  business_salesman: '',
  project_source: 'INTERNAL' as ProjectSource,
  external_project_leader_name: ''
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

  if (!form.project_name || !form.client_name || !form.undertaking_unit || !form.report_type) {
    ElMessage.warning('请填写完整项目基础信息')
    return
  }
  if (!form.business_salesman.trim()) {
    ElMessage.warning('请填写项目承接业务员')
    return
  }
  if (form.project_source === 'EXTERNAL' && !form.external_project_leader_name.trim()) {
    ElMessage.warning('外部项目必须填写外部项目负责人姓名')
    return
  }

  try {
    const projectCode = form.project_code.trim()
    await createProject({
      ...(projectCode ? { project_code: projectCode } : {}),
      undertaking_unit: form.undertaking_unit,
      project_name: form.project_name,
      client_name: form.client_name,
      report_type: form.report_type,
      valuation_base_date: form.valuation_base_date || undefined,
      business_salesman: form.business_salesman.trim(),
      project_source: form.project_source,
      external_project_leader_name: form.project_source === 'EXTERNAL' ? form.external_project_leader_name.trim() : undefined,
      business_user_id: currentUser.id,
      project_leader_id: currentUser.id
    })
    ElMessage.success('项目创建成功')
    form.project_code = ''
    form.undertaking_unit = '中勤'
    form.project_name = ''
    form.client_name = ''
    form.report_type = '评估报告'
    form.valuation_base_date = ''
    form.business_salesman = ''
    form.project_source = 'INTERNAL'
    form.external_project_leader_name = ''
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
    '确认归档该项目吗？归档后表示该项目流程已结束，不再进入后续工单办理范围。',
    '归档确认',
    { type: 'warning' }
  )
  await archiveProject(row.id)
  ElMessage.success('项目已归档')
  await loadProjects()
}

function goDetail(projectId: number) {
  router.push(`/projects/${projectId}`)
}

onMounted(loadProjects)
</script>
