<template>
  <div class="project-basic-panel">
    <el-form v-if="editing" label-width="120px" class="edit-form">
      <el-form-item label="项目编号">
        <el-input :model-value="flowInfo.project.project_no" disabled />
      </el-form-item>
      <el-form-item label="项目名称">
        <el-input v-model="form.project_name" />
      </el-form-item>
      <el-form-item label="客户名称">
        <el-input v-model="form.client_name" />
      </el-form-item>
      <el-form-item label="承接单位">
        <el-select v-model="form.undertaking_unit" style="width: 100%">
          <el-option label="中勤" value="中勤" />
          <el-option label="中立国际" value="中立国际" />
          <el-option label="中众" value="中众" />
          <el-option label="其他" value="其他" />
        </el-select>
      </el-form-item>
      <el-form-item label="报告类型">
        <el-select v-model="form.report_type" style="width: 100%">
          <el-option label="评估报告" value="评估报告" />
          <el-option label="估值报告" value="估值报告" />
          <el-option label="咨询报告" value="咨询报告" />
        </el-select>
      </el-form-item>
      <el-form-item label="评估基准日">
        <el-date-picker
          v-model="form.valuation_base_date"
          type="date"
          value-format="YYYY-MM-DD"
          placeholder="选择评估基准日"
          style="width: 100%"
        />
      </el-form-item>
      <el-form-item label="项目承接业务员">
        <el-input v-model="form.business_salesman" />
      </el-form-item>
      <el-form-item label="项目金额">
        <el-input-number v-model="form.project_amount" :min="0" :precision="2" style="width: 100%" />
      </el-form-item>
      <el-form-item label="项目来源">
        <el-radio-group v-model="form.project_source">
          <el-radio-button label="INTERNAL">内部项目</el-radio-button>
          <el-radio-button label="EXTERNAL">外部项目</el-radio-button>
        </el-radio-group>
      </el-form-item>
      <el-form-item v-if="form.project_source === 'EXTERNAL'" label="外部项目负责人">
        <el-input v-model="form.external_project_leader_name" />
      </el-form-item>

      <el-divider />

      <el-form-item label="项目负责人">
        <el-input :model-value="projectLeaderName" disabled />
      </el-form-item>
      <el-form-item label="一审人员姓名">
        <el-input :model-value="flowInfo.project.first_reviewer_name || '-'" disabled />
      </el-form-item>
      <el-form-item label="二审人员姓名">
        <el-input :model-value="flowInfo.project.second_reviewer_name || '-'" disabled />
      </el-form-item>
      <el-form-item label="三审人员姓名">
        <el-input :model-value="flowInfo.project.third_reviewer_name || '-'" disabled />
      </el-form-item>
      <el-form-item label="文印室人员姓名">
        <el-input :model-value="flowInfo.project.print_room_handler_name || '-'" disabled />
      </el-form-item>
      <el-form-item label="开票人姓名">
        <el-input :model-value="flowInfo.project.invoice_handler_name || '-'" disabled />
      </el-form-item>
      <el-form-item label="档案管理员姓名">
        <el-input :model-value="flowInfo.project.archive_reviewer_name || '-'" disabled />
      </el-form-item>
      <el-form-item label="报告编号">
        <el-input :model-value="flowInfo.project.report_no || '-'" disabled />
      </el-form-item>
      <el-form-item label="合同编号">
        <el-input :model-value="flowInfo.project.contract_no || '-'" disabled />
      </el-form-item>
      <el-form-item label="当前步骤">
        <el-input :model-value="flowInfo.project.current_step" disabled />
      </el-form-item>
      <el-form-item label="项目状态">
        <el-input :model-value="flowInfo.project.status_display" disabled />
      </el-form-item>
      <el-form-item label="合同初稿审核状态">
        <el-input :model-value="flowInfo.contract_review_status_display || '-'" disabled />
      </el-form-item>
      <el-form-item label="合同审核人">
        <el-input :model-value="flowInfo.contract_reviewer_name || '-'" disabled />
      </el-form-item>

      <div class="panel-actions">
        <el-button @click="cancelEdit">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </div>
    </el-form>

    <template v-else>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="项目编号">{{ flowInfo.project.project_no }}</el-descriptions-item>
        <el-descriptions-item label="项目名称">{{ flowInfo.project.project_name }}</el-descriptions-item>
        <el-descriptions-item label="客户名称">{{ flowInfo.project.client_name }}</el-descriptions-item>
        <el-descriptions-item label="承接单位">{{ flowInfo.project.undertaking_unit || '-' }}</el-descriptions-item>
        <el-descriptions-item label="报告类型">{{ flowInfo.project.report_type || '-' }}</el-descriptions-item>
        <el-descriptions-item label="评估基准日">{{ flowInfo.project.valuation_base_date || '-' }}</el-descriptions-item>
        <el-descriptions-item label="项目承接业务员">{{ flowInfo.project.business_salesman || '-' }}</el-descriptions-item>
        <el-descriptions-item label="项目金额">{{ formatAmount(flowInfo.project.project_amount) }}</el-descriptions-item>
        <el-descriptions-item label="项目来源">{{ flowInfo.project.project_source_display }}</el-descriptions-item>
        <el-descriptions-item label="项目负责人">{{ projectLeaderName }}</el-descriptions-item>
        <el-descriptions-item label="一审人员姓名">{{ flowInfo.project.first_reviewer_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="二审人员姓名">{{ flowInfo.project.second_reviewer_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="三审人员姓名">{{ flowInfo.project.third_reviewer_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="文印室人员姓名">{{ flowInfo.project.print_room_handler_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="开票人姓名">{{ flowInfo.project.invoice_handler_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="档案管理员姓名">{{ flowInfo.project.archive_reviewer_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="报告编号">{{ flowInfo.project.report_no || '-' }}</el-descriptions-item>
        <el-descriptions-item label="合同编号">{{ flowInfo.project.contract_no || '-' }}</el-descriptions-item>
        <el-descriptions-item label="当前步骤">{{ flowInfo.project.current_step }}</el-descriptions-item>
        <el-descriptions-item label="项目状态">{{ flowInfo.project.status_display }}</el-descriptions-item>
        <el-descriptions-item label="合同初稿审核状态">{{ flowInfo.contract_review_status_display || '-' }}</el-descriptions-item>
        <el-descriptions-item label="合同审核人">{{ flowInfo.contract_reviewer_name || '-' }}</el-descriptions-item>
      </el-descriptions>

      <div class="panel-actions" v-if="canEditBasicInfo">
        <el-button type="success" plain @click="openQuoteCalculator">报价计算器</el-button>
        <el-button type="primary" @click="startEdit">编辑</el-button>
      </div>
    </template>

    <el-divider>修改记录</el-divider>
    <el-table :data="logs" size="small">
      <el-table-column prop="operator_user_name" label="操作人" min-width="120" />
      <el-table-column label="修改项目" min-width="360" show-overflow-tooltip>
        <template #default="{ row }">
          {{ formatChangedFields(row.changed_fields) }}
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="时间" min-width="180" />
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import type { ProjectFlowData } from '@/api/projectFlow'
import { updateProject, type ProjectSource, type ProjectUndertakingUnit, type ReportType } from '@/api/projects'

const props = defineProps<{ flowInfo: ProjectFlowData; userRoles?: string[]; canEdit?: boolean }>()
const emit = defineEmits<{ (e: 'changed'): void }>()

const editing = ref(false)
const saving = ref(false)
const logs = computed(() => props.flowInfo.project_update_logs || [])
const canEditBasicInfo = computed(() => Boolean(
  props.canEdit &&
  props.userRoles?.some(role => ['PROJECT_LEADER', 'PROJECT_MEMBER', 'ADMIN'].includes(role))
))
const projectLeaderName = computed(() => (
  props.flowInfo.project.external_project_leader_name ||
  props.flowInfo.project.project_leader_display_name ||
  '-'
))

const form = reactive({
  undertaking_unit: '中勤' as ProjectUndertakingUnit,
  project_name: '',
  client_name: '',
  report_type: '评估报告' as ReportType,
  valuation_base_date: '',
  business_salesman: '',
  project_amount: 0,
  project_source: 'INTERNAL' as ProjectSource,
  external_project_leader_name: ''
})

function fillForm() {
  form.undertaking_unit = (props.flowInfo.project.undertaking_unit || '中勤') as ProjectUndertakingUnit
  form.project_name = props.flowInfo.project.project_name || ''
  form.client_name = props.flowInfo.project.client_name || ''
  form.report_type = (props.flowInfo.project.report_type || '评估报告') as ReportType
  form.valuation_base_date = props.flowInfo.project.valuation_base_date || ''
  form.business_salesman = props.flowInfo.project.business_salesman || ''
  form.project_amount = props.flowInfo.project.project_amount ?? 0
  form.project_source = props.flowInfo.project.project_source || 'INTERNAL'
  form.external_project_leader_name = props.flowInfo.project.external_project_leader_name || ''
}

function startEdit() {
  fillForm()
  editing.value = true
}

function cancelEdit() {
  editing.value = false
}

function openQuoteCalculator() {
  window.open('https://zqbjxt.zeabur.app/', '_blank', 'noopener,noreferrer')
}

function formatAmount(value?: number | null) {
  if (value === undefined || value === null) return '-'
  return Number(value).toFixed(2)
}

function formatChangedFields(changedFields: string) {
  try {
    const parsed = JSON.parse(changedFields) as Record<string, { before?: unknown; after?: unknown }>
    const fieldLabelMap: Record<string, string> = {
      undertaking_unit: '承接单位',
      project_name: '项目名称',
      client_name: '客户名称',
      report_type: '报告类型',
      valuation_base_date: '评估基准日',
      business_salesman: '项目承接业务员',
      project_amount: '项目金额',
      project_source: '项目来源',
      external_project_leader_name: '外部项目负责人姓名'
    }
    const labels = Object.keys(parsed).map(key => fieldLabelMap[key] || key)
    return labels.length ? labels.join('、') : '-'
  } catch {
    return changedFields || '-'
  }
}

async function save() {
  if (!form.project_name.trim() || !form.client_name.trim()) {
    ElMessage.warning('请填写项目名称和客户名称')
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

  saving.value = true
  try {
    await updateProject(props.flowInfo.project.id, {
      undertaking_unit: form.undertaking_unit,
      project_name: form.project_name.trim(),
      client_name: form.client_name.trim(),
      report_type: form.report_type,
      valuation_base_date: form.valuation_base_date || undefined,
      business_salesman: form.business_salesman.trim(),
      project_amount: form.project_amount,
      project_source: form.project_source,
      external_project_leader_name: form.project_source === 'EXTERNAL' ? form.external_project_leader_name.trim() : null
    })
    ElMessage.success('项目基本信息已更新')
    editing.value = false
    emit('changed')
  } finally {
    saving.value = false
  }
}

watch(() => props.flowInfo.project.id, fillForm, { immediate: true })
</script>

<style scoped>
.project-basic-panel {
  display: grid;
  gap: 16px;
}

.panel-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 16px;
}

.edit-form {
  padding-top: 4px;
}
</style>
