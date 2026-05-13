<template>
  <el-alert
    v-if="!workOrderId"
    type="warning"
    :closable="false"
    title="当前项目暂无关联工单，无法办理报告邮寄。"
    show-icon
    style="margin-bottom: 12px"
  />
  <template v-else>
    <el-alert
      v-if="showConfirmHint"
      type="info"
      :closable="false"
      title="请先在报告出具环节确认报告内容后，再进入报告邮寄。"
      show-icon
      style="margin-bottom: 12px"
    />

    <div class="mailing-layout">
      <el-form v-if="showProjectEditForm" label-width="120px" class="mailing-form">
        <el-form-item label="收件人">
          <el-input v-model="form.receiver_name" />
        </el-form-item>
        <el-form-item label="联系电话">
          <el-input v-model="form.receiver_phone" />
        </el-form-item>
        <el-form-item label="收件地址">
          <el-input v-model="form.receiver_address" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.receiver_remark" type="textarea" :rows="2" />
        </el-form-item>
        <div class="mailing-actions">
          <el-button type="primary" @click="submitMailing">{{ hasSubmittedOnce ? '重新提交' : '提交邮寄信息' }}</el-button>
          <el-button v-if="canCancelEditing" @click="cancelEditing">取消修改</el-button>
        </div>
      </el-form>

      <el-form v-else-if="showProjectSubmittedView" label-width="120px" class="mailing-form">
        <el-form-item label="收件人">
          <el-input :model-value="latestProjectRecord?.receiver_name || '-'" disabled />
        </el-form-item>
        <el-form-item label="联系电话">
          <el-input :model-value="latestProjectRecord?.receiver_phone || '-'" disabled />
        </el-form-item>
        <el-form-item label="收件地址">
          <el-input :model-value="latestProjectRecord?.receiver_address || '-'" type="textarea" :rows="3" disabled />
        </el-form-item>
        <el-form-item label="备注">
          <el-input :model-value="latestProjectRecord?.receiver_remark || '-'" type="textarea" :rows="2" disabled />
        </el-form-item>
        <el-alert type="success" :closable="false" title="邮寄信息已提交，等待文印室录入快递单号。" show-icon />
        <div class="mailing-actions mailing-actions-top">
          <el-button type="warning" plain @click="startModify">撤回并修改</el-button>
        </div>
      </el-form>

      <el-form v-else-if="canPrintRoomHandle" label-width="120px" class="mailing-form">
        <el-form-item label="收件人">
          <el-input :model-value="latestProjectRecord?.receiver_name || '-'" disabled />
        </el-form-item>
        <el-form-item label="联系电话">
          <el-input :model-value="latestProjectRecord?.receiver_phone || '-'" disabled />
        </el-form-item>
        <el-form-item label="收件地址">
          <el-input :model-value="latestProjectRecord?.receiver_address || '-'" type="textarea" :rows="3" disabled />
        </el-form-item>
        <el-form-item label="备注">
          <el-input :model-value="latestProjectRecord?.receiver_remark || '-'" type="textarea" :rows="2" disabled />
        </el-form-item>
        <el-form-item label="快递单号">
          <el-input v-model="expressNo" />
        </el-form-item>
        <div class="mailing-actions">
          <el-button @click="copyMailingInfo">一键复制信息</el-button>
          <el-button type="primary" @click="submitExpress">提交快递单号</el-button>
        </div>
      </el-form>

      <el-form v-else-if="canProjectConfirm" label-width="120px" class="mailing-form">
        <el-form-item label="收件人">
          <el-input :model-value="latestProjectRecord?.receiver_name || '-'" disabled />
        </el-form-item>
        <el-form-item label="联系电话">
          <el-input :model-value="latestProjectRecord?.receiver_phone || '-'" disabled />
        </el-form-item>
        <el-form-item label="收件地址">
          <el-input :model-value="latestProjectRecord?.receiver_address || '-'" type="textarea" :rows="3" disabled />
        </el-form-item>
        <el-form-item label="备注">
          <el-input :model-value="latestProjectRecord?.receiver_remark || '-'" type="textarea" :rows="2" disabled />
        </el-form-item>
        <el-form-item label="快递单号">
          <el-input :model-value="latestPrintRoomRecord?.express_no || '-'" disabled />
        </el-form-item>
        <el-form-item v-if="latestInvalidatedExpressNo" label="失效快递单号">
          <el-input :model-value="latestInvalidatedExpressNo" disabled />
        </el-form-item>
        <div class="mailing-actions">
          <el-button type="success" @click="confirmMailing">确认已寄出</el-button>
          <el-button type="warning" plain @click="startModify">更改邮寄信息</el-button>
        </div>
      </el-form>
    </div>

    <el-divider>邮寄记录</el-divider>
    <el-table :data="tableRows" size="small">
      <el-table-column prop="action_type_display" label="动作" min-width="140" />
      <el-table-column prop="operator_user_name" label="操作人" min-width="120" />
      <el-table-column prop="receiver_name" label="收件人" min-width="120" />
      <el-table-column prop="receiver_phone" label="联系电话" min-width="120" />
      <el-table-column prop="express_no" label="快递单号" min-width="140" />
      <el-table-column prop="created_at" label="时间" min-width="180" />
    </el-table>
  </template>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import type { ProjectFlowData } from '@/api/projectFlow'
import {
  confirmReportMailing,
  listReportMailingRecords,
  startReportMailing,
  submitReportMailing,
  submitReportMailingExpress,
  type ReportMailingRecordItem
} from '@/api/reportMailing'

const props = defineProps<{ workOrderId?: number; canOperate: boolean; userRoles?: string[]; flowInfo?: ProjectFlowData }>()
const emit = defineEmits<{ (e: 'changed'): void }>()

const records = ref<ReportMailingRecordItem[]>([])
const expressNo = ref('')
const editing = ref(false)
const form = reactive({
  receiver_name: '',
  receiver_phone: '',
  receiver_address: '',
  receiver_remark: ''
})

const actionTypeDisplayMap: Record<string, string> = {
  SUBMIT_MAILING: '提交邮寄信息',
  RESUBMIT_MAILING: '重新提交邮寄信息',
  PRINT_ROOM_SUBMIT_EXPRESS: '文印室填写快递单号',
  PROJECT_CONFIRM_MAILING: '项目方确认已寄出'
}

const isProjectParty = computed(() =>
  ['项目负责人', '项目组成员', '创建人'].includes(props.flowInfo?.user_role_in_project || '')
)
const latestRecord = computed(() => records.value[0] || null)
const latestProjectRecord = computed(() =>
  records.value.find(item => ['SUBMIT_MAILING', 'RESUBMIT_MAILING'].includes(item.action_type)) || null
)
const latestPrintRoomRecord = computed(() =>
  records.value.find(item => item.action_type === 'PRINT_ROOM_SUBMIT_EXPRESS') || null
)
const hasSubmittedOnce = computed(() =>
  records.value.some(item => ['SUBMIT_MAILING', 'RESUBMIT_MAILING'].includes(item.action_type))
)
const latestInvalidatedExpressNo = computed(() =>
  records.value.find(item => Boolean(item.invalidated_express_no))?.invalidated_express_no || null
)

const showProjectEditForm = computed(() =>
  isProjectParty.value &&
  (editing.value || !latestRecord.value || props.flowInfo?.mailing_status === 'PROJECT_EDITING')
)
const showProjectSubmittedView = computed(() =>
  isProjectParty.value &&
  !editing.value &&
  props.flowInfo?.mailing_status === 'PRINT_ROOM_PENDING'
)
const canCancelEditing = computed(() => editing.value && hasSubmittedOnce.value)
const canPrintRoomHandle = computed(() =>
  (props.flowInfo?.user_role_in_project === '文印室' || props.userRoles?.includes('PRINT_ROOM')) &&
  props.flowInfo?.mailing_status === 'PRINT_ROOM_PENDING'
)
const canProjectConfirm = computed(() =>
  isProjectParty.value && props.flowInfo?.mailing_status === 'PROJECT_CONFIRMING'
)
const showConfirmHint = computed(() =>
  !showProjectEditForm.value &&
  !showProjectSubmittedView.value &&
  !canPrintRoomHandle.value &&
  !canProjectConfirm.value &&
  !records.value.length
)

const tableRows = computed(() =>
  records.value.map(item => ({
    ...item,
    action_type_display: actionTypeDisplayMap[item.action_type] || item.action_type
  }))
)

function fillForm() {
  form.receiver_name = latestProjectRecord.value?.receiver_name || ''
  form.receiver_phone = latestProjectRecord.value?.receiver_phone || ''
  form.receiver_address = latestProjectRecord.value?.receiver_address || ''
  form.receiver_remark = latestProjectRecord.value?.receiver_remark || ''
}

async function load() {
  if (!props.workOrderId) return
  records.value = (await listReportMailingRecords(props.workOrderId)).items
  fillForm()
}

async function submitMailing() {
  if (!props.workOrderId) return
  if (!form.receiver_name.trim() || !form.receiver_phone.trim() || !form.receiver_address.trim()) {
    ElMessage.warning('请填写完整邮寄信息')
    return
  }
  if (!['REPORT_MAILING', 'REPORT_MAILING_COMPLETED'].includes(props.flowInfo?.current_work_order_status || '')) {
    await startReportMailing(props.workOrderId)
  }
  const resubmitting = hasSubmittedOnce.value
  await submitReportMailing(props.workOrderId, {
    receiver_name: form.receiver_name.trim(),
    receiver_phone: form.receiver_phone.trim(),
    receiver_address: form.receiver_address.trim(),
    receiver_remark: form.receiver_remark.trim() || undefined
  })
  editing.value = false
  ElMessage.success(resubmitting ? '邮寄信息已重新提交' : '邮寄信息已提交')
  await load()
  emit('changed')
}

async function submitExpress() {
  if (!props.workOrderId) return
  if (!expressNo.value.trim()) {
    ElMessage.warning('请填写快递单号')
    return
  }
  await submitReportMailingExpress(props.workOrderId, { express_no: expressNo.value.trim() })
  expressNo.value = ''
  ElMessage.success('快递单号已提交')
  await load()
  emit('changed')
}

async function confirmMailing() {
  if (!props.workOrderId) return
  await confirmReportMailing(props.workOrderId)
  ElMessage.success('报告邮寄已确认完成')
  await load()
  emit('changed')
}

function startModify() {
  editing.value = true
  fillForm()
}

function cancelEditing() {
  editing.value = false
  fillForm()
}

async function copyMailingInfo() {
  const text = [
    `收件人：${latestProjectRecord.value?.receiver_name || ''}`,
    `联系电话：${latestProjectRecord.value?.receiver_phone || ''}`,
    `收件地址：${latestProjectRecord.value?.receiver_address || ''}`,
    `备注：${latestProjectRecord.value?.receiver_remark || ''}`
  ].join('\n')
  try {
    await navigator.clipboard.writeText(text)
  } catch {
    const textarea = document.createElement('textarea')
    textarea.value = text
    textarea.style.position = 'fixed'
    textarea.style.opacity = '0'
    document.body.appendChild(textarea)
    textarea.focus()
    textarea.select()
    document.execCommand('copy')
    document.body.removeChild(textarea)
  }
  ElMessage.success('邮寄信息已复制')
}

onMounted(load)
watch(() => [props.workOrderId, props.flowInfo?.mailing_status], load)
</script>

<style scoped>
.mailing-layout {
  display: grid;
  gap: 16px;
}

.mailing-form {
  max-width: 720px;
}

.mailing-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.mailing-actions-top {
  margin-top: 12px;
}
</style>
