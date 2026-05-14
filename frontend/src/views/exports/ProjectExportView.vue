<template>
  <el-card shadow="never">
    <template #header>项目清单导出</template>

    <el-form :model="filters" label-width="120px" class="filter-form">
      <el-row :gutter="12">
        <el-col :span="6"><el-form-item label="项目编号"><el-input v-model="filters.project_no" clearable /></el-form-item></el-col>
        <el-col :span="6"><el-form-item label="项目名称"><el-input v-model="filters.project_name" clearable /></el-form-item></el-col>
        <el-col :span="6"><el-form-item label="报告编号"><el-input v-model="filters.report_no" clearable /></el-form-item></el-col>
        <el-col :span="6"><el-form-item label="项目负责人"><el-input v-model="filters.project_leader_name" clearable /></el-form-item></el-col>
        <el-col :span="6">
          <el-form-item label="承接单位">
            <el-select v-model="filters.undertaking_unit" clearable>
              <el-option label="中勤" value="中勤" />
              <el-option label="中立国际" value="中立国际" />
              <el-option label="中众" value="中众" />
              <el-option label="其他" value="其他" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="6">
          <el-form-item label="报告类型">
            <el-select v-model="filters.report_type" clearable>
              <el-option label="评估报告" value="评估报告" />
              <el-option label="估值报告" value="估值报告" />
              <el-option label="咨询报告" value="咨询报告" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="6"><el-form-item label="项目承接业务员"><el-input v-model="filters.business_salesman" clearable /></el-form-item></el-col>
        <el-col :span="6">
          <el-form-item label="项目来源">
            <el-select v-model="filters.project_source" clearable>
              <el-option label="内部项目" value="INTERNAL" />
              <el-option label="外部项目" value="EXTERNAL" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="6"><el-form-item label="外部项目负责人"><el-input v-model="filters.external_project_leader_name" clearable /></el-form-item></el-col>
        <el-col :span="6"><el-form-item label="签字评估师"><el-input v-model="filters.signer_name" clearable /></el-form-item></el-col>
        <el-col :span="6"><el-form-item label="收费金额下限"><el-input-number v-model="filters.amount_min" :min="0" :precision="2" style="width:100%" /></el-form-item></el-col>
        <el-col :span="6"><el-form-item label="收费金额上限"><el-input-number v-model="filters.amount_max" :min="0" :precision="2" style="width:100%" /></el-form-item></el-col>
        <el-col :span="6"><el-form-item label="立项开始日期"><el-date-picker v-model="filters.project_date_from" value-format="YYYY-MM-DD" type="date" style="width:100%" /></el-form-item></el-col>
        <el-col :span="6"><el-form-item label="立项结束日期"><el-date-picker v-model="filters.project_date_to" value-format="YYYY-MM-DD" type="date" style="width:100%" /></el-form-item></el-col>
        <el-col :span="6"><el-form-item label="基准日开始"><el-date-picker v-model="filters.valuation_base_date_from" value-format="YYYY-MM-DD" type="date" style="width:100%" /></el-form-item></el-col>
        <el-col :span="6"><el-form-item label="基准日结束"><el-date-picker v-model="filters.valuation_base_date_to" value-format="YYYY-MM-DD" type="date" style="width:100%" /></el-form-item></el-col>
        <el-col :span="6"><el-form-item label="已删除项目"><el-switch v-model="filters.include_deleted" /></el-form-item></el-col>
        <el-col :span="12">
          <el-form-item>
            <el-button type="primary" @click="load">筛选</el-button>
            <el-button @click="reset">重置</el-button>
            <el-button type="success" @click="onExport">导出Excel</el-button>
          </el-form-item>
        </el-col>
      </el-row>
    </el-form>

    <el-table :data="rows" size="small" v-loading="loading" class="wide-table">
      <el-table-column prop="project_no" label="项目编号" min-width="140" fixed="left" />
      <el-table-column prop="project_name" label="项目名称" min-width="180" fixed="left" show-overflow-tooltip />
      <el-table-column prop="project_created_date" label="项目立项日期" min-width="120" />
      <el-table-column prop="project_progress" label="项目进度" min-width="100" />
      <el-table-column prop="report_no" label="报告编号" min-width="140" />
      <el-table-column prop="project_leader_name" label="项目负责人姓名" min-width="130" />
      <el-table-column prop="undertaking_unit" label="承接单位" min-width="100" />
      <el-table-column prop="report_type" label="报告类型" min-width="110" />
      <el-table-column prop="valuation_base_date" label="评估基准日" min-width="120" />
      <el-table-column prop="business_salesman" label="项目承接业务员" min-width="140" />
      <el-table-column prop="project_source_display" label="项目来源" min-width="100" />
      <el-table-column prop="external_project_leader_name" label="外部项目负责人" min-width="140" />
      <el-table-column prop="amount" label="收费金额" min-width="110" />
      <el-table-column prop="invoiced_amount" label="累计开票金额" min-width="130" />
      <el-table-column prop="signer_names" label="签字评估师姓名" min-width="160" show-overflow-tooltip />
      <el-table-column prop="first_reviewer_name" label="一审人员姓名" min-width="120" />
      <el-table-column prop="second_reviewer_name" label="二审人员姓名" min-width="120" />
      <el-table-column prop="third_reviewer_name" label="三审人员姓名" min-width="120" />
      <el-table-column prop="archive_date" label="归档日期" min-width="120" />
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <el-button v-if="row.can_admin_delete" link type="danger" @click="requestDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="deleteDialogVisible" title="申请删除项目" width="520px">
      <el-form label-width="120px">
        <el-form-item label="共同认证管理员">
          <el-select v-model="deleteDraft.approver_user_id" style="width: 100%">
            <el-option
              v-for="item in deleteAdminOptions"
              :key="item.id"
              :label="item.real_name"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="删除原因">
          <el-input v-model="deleteDraft.reason" type="textarea" :rows="3" placeholder="可选填写删除原因" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="deleteDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="deleteSubmitting" @click="submitDeleteRequest">提交删除申请</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { exportProjectRowsExcel, listProjectExportRows, type ProjectExportFilters, type ProjectExportItem } from '@/api/projectExports'
import { createProjectDeleteRequest } from '@/api/projectDeleteRequests'
import { listUserCandidates, type UserItem } from '@/api/users'
import { useAuthStore } from '@/store/auth'

const loading = ref(false)
const auth = useAuthStore()
const rows = ref<ProjectExportItem[]>([])
const filters = reactive<ProjectExportFilters>({})
const deleteDialogVisible = ref(false)
const deleteSubmitting = ref(false)
const deleteAdminOptions = ref<UserItem[]>([])
const deleteTargetProjectId = ref<number>()
const deleteTargetProjectName = ref('')
const deleteDraft = reactive({
  approver_user_id: undefined as number | undefined,
  reason: ''
})

async function load() {
  loading.value = true
  try {
    rows.value = (await listProjectExportRows(filters)).items
  } finally {
    loading.value = false
  }
}

function reset() {
  Object.keys(filters).forEach(key => delete filters[key as keyof ProjectExportFilters])
  load()
}

async function onExport() {
  await exportProjectRowsExcel(filters)
  ElMessage.success('Excel已生成')
}

async function requestDelete(row: ProjectExportItem) {
  const user = auth.user ?? await auth.ensureUserLoaded()
  await ElMessageBox.confirm('确认申请删除该已归档项目吗？', '删除确认', {
    confirmButtonText: '确认',
    cancelButtonText: '取消',
    type: 'warning'
  })
  const admins = (await listUserCandidates('ADMIN')).items.filter(item => item.id !== user?.id)
  if (!admins.length) {
    ElMessage.warning('暂无可选的共同认证管理员')
    return
  }
  deleteAdminOptions.value = admins
  deleteTargetProjectId.value = row.project_id
  deleteTargetProjectName.value = row.project_name
  deleteDraft.approver_user_id = admins[0].id
  deleteDraft.reason = ''
  deleteDialogVisible.value = true
}

async function submitDeleteRequest() {
  if (!deleteTargetProjectId.value || !deleteDraft.approver_user_id) {
    ElMessage.warning('请选择共同认证管理员')
    return
  }
  deleteSubmitting.value = true
  try {
    const approver = deleteAdminOptions.value.find(item => item.id === deleteDraft.approver_user_id)
    await createProjectDeleteRequest(deleteTargetProjectId.value, {
      approver_user_id: deleteDraft.approver_user_id,
      reason: deleteDraft.reason.trim() || undefined
    })
    deleteDialogVisible.value = false
    ElMessage.success(`已提交项目「${deleteTargetProjectName.value}」删除申请，待管理员 ${approver?.real_name || ''} 确认`)
    await load()
  } finally {
    deleteSubmitting.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.filter-form {
  margin-bottom: 12px;
}

.wide-table {
  width: 100%;
}
</style>
