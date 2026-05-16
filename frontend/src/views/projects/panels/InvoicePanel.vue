<template>
  <el-alert
    v-if="!workOrderId"
    type="warning"
    :closable="false"
    title="当前项目暂无关联工单，无法办理发票开具。"
    show-icon
    style="margin-bottom: 12px"
  />

  <template v-else>
    <el-alert
      v-if="projectAmount == null"
      type="warning"
      :closable="false"
      title="请先在项目基本信息模块中录入项目金额"
      show-icon
      style="margin-bottom: 12px"
    />
    <el-alert
      v-if="currentInvoice"
      :type="statusAlertType"
      :closable="false"
      :title="statusText"
      show-icon
      style="margin-bottom: 12px"
    />

    <template v-else>
      <el-descriptions :column="2" border class="invoice-summary">
        <el-descriptions-item label="项目金额">{{ formatAmount(projectAmount) }}</el-descriptions-item>
        <el-descriptions-item label="累计开票金额">{{ formatAmount(cumulativeAmount) }}</el-descriptions-item>
      </el-descriptions>
    </template>

    <el-form label-width="112px">
      <el-form-item label="开票信息">
        <el-input
          v-model="invoiceInfo"
          type="textarea"
          :rows="3"
          :disabled="!canSubmitInfo"
          placeholder="请输入开票抬头、税号、地址电话、开户行账号等信息"
        />
      </el-form-item>
      <el-form-item label="发票类型">
        <el-select v-model="invoiceType" :disabled="!canSubmitInfo" style="width: 180px">
          <el-option label="专票" value="专票" />
          <el-option label="普票" value="普票" />
        </el-select>
      </el-form-item>
      <el-form-item label="开票单位">
        <el-select v-model="invoiceUnit" :disabled="!canSubmitInfo" style="width: 180px">
          <el-option label="中勤" value="中勤" />
          <el-option label="中立国际" value="中立国际" />
          <el-option label="中众" value="中众" />
          <el-option label="其他" value="其他" />
        </el-select>
      </el-form-item>
      <el-form-item label="开票金额">
        <el-input-number v-model="amount" :min="0" :precision="2" :disabled="!canSubmitInfo" />
      </el-form-item>
      <el-form-item v-if="!canFinance" label="办理财务人员">
        <el-select v-model="financeHandlerId" :disabled="!canSubmitInfo" placeholder="请选择财务人员" style="width: 220px">
          <el-option v-for="user in financeUsers" :key="user.id" :label="user.real_name || user.username" :value="user.id" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-space wrap>
          <el-button type="primary" :disabled="!canSubmitInfo" @click="onSubmitInfo">{{ submitButtonText }}</el-button>
          <el-button v-if="canWithdraw" type="warning" plain @click="onWithdraw">撤回并修改</el-button>
          <el-button v-if="canProjectConfirm" type="success" @click="onProjectConfirm">确认完成</el-button>
          <el-button v-if="canProjectConfirm" type="danger" plain @click="onProjectReturn">退回修改</el-button>
          <el-button v-if="canFinance" @click="copyInfo">一键复制</el-button>
          <el-button v-if="canFinance" type="warning" plain :disabled="!canFinanceProcess" @click="onReject">
            信息有误，返回上一级
          </el-button>
        </el-space>
      </el-form-item>
    </el-form>

    <template v-if="canFinance">
      <el-divider>财务处理</el-divider>
      <div class="finance-actions">
        <el-upload :auto-upload="false" :on-change="onInvoiceFileSelected" :show-file-list="false">
          <el-button type="primary" :disabled="!canFinanceProcess">上传电子票</el-button>
        </el-upload>
        <el-button type="success" :disabled="!canFinanceProcess || invoiceFiles.length === 0" @click="onComplete">
          确认完成
        </el-button>
      </div>
    </template>

    <el-divider>发票下载</el-divider>
    <div v-if="invoiceFiles.length" class="download-list">
      <div v-for="file in invoiceFiles" :key="file.id" class="download-item">
        <span>{{ file.origin_file_name }}</span>
        <el-button type="primary" link @click="download(file)">下载</el-button>
        <el-button v-if="canFinanceProcess" type="warning" link @click="triggerReplace(file.id)">重新上传</el-button>
        <input
          :ref="el => setReplaceInput(file.id, el)"
          class="hidden-file-input"
          type="file"
          @change="event => onReplaceInput(file, event)"
        />
      </div>
    </div>
    <span v-else>-</span>

    <el-divider>开票记录</el-divider>
    <el-table :data="invoices" size="small" empty-text="暂无开票记录">
      <el-table-column label="状态" width="150">
        <template #default="{ row }">{{ invoiceStatusLabel(row.status) }}</template>
      </el-table-column>
      <el-table-column prop="invoice_type" label="发票类型" width="120" />
      <el-table-column prop="amount" label="开票金额" width="120" />
      <el-table-column label="办理财务" width="140">
        <template #default="{ row }">{{ userName(row.handled_by || row.finance_handler_id) }}</template>
      </el-table-column>
      <el-table-column prop="updated_at" label="更新时间" />
    </el-table>
  </template>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch, type ComponentPublicInstance } from 'vue'
import { ElMessage, type UploadFile } from 'element-plus'
import {
  completeInvoice,
  confirmInvoice,
  createInvoice,
  listInvoices,
  rejectInvoice,
  returnInvoice,
  withdrawInvoice,
  type InvoiceItem
} from '@/api/finance'
import { downloadWorkOrderFile, listWorkOrderFiles, replaceWorkOrderFile, uploadWorkOrderFile, type WorkOrderFileItem } from '@/api/files'
import type { ProjectFlowData } from '@/api/projectFlow'
import { listUserCandidates, type UserItem } from '@/api/users'
import { isFinanceRoleInCurrentFlow } from './invoicePermissions'

const props = defineProps<{
  workOrderId?: number
  canOperate: boolean
  userRoles: string[]
  userRoleInProject?: string
  flowInfo?: ProjectFlowData
}>()
const emit = defineEmits<{ (e: 'changed'): void }>()

const invoices = ref<InvoiceItem[]>([])
const invoiceFiles = ref<WorkOrderFileItem[]>([])
const financeUsers = ref<UserItem[]>([])
const invoiceInfo = ref('')
const invoiceType = ref<'专票' | '普票'>('专票')
const invoiceUnit = ref('中勤')
const amount = ref(0)
const financeHandlerId = ref<number>()
const replaceInputs = new Map<number, HTMLInputElement>()

const projectAmount = computed(() => props.flowInfo?.project.project_amount ?? null)
const canFinance = computed(() => isFinanceRoleInCurrentFlow(props.userRoleInProject))
const activeStatuses = ['SUBMITTED', 'FINANCE_COMPLETED', 'PROJECT_RETURNED', 'REJECTED']
const countedStatuses = ['SUBMITTED', 'FINANCE_COMPLETED', 'PROJECT_RETURNED', 'ISSUED']
const currentInvoice = computed(() => invoices.value.find(item => activeStatuses.includes(item.status)))
const cumulativeAmount = computed(() => props.flowInfo?.project.invoiced_amount ?? invoices.value
  .filter(item => countedStatuses.includes(item.status))
  .reduce((sum, item) => sum + Number(item.amount || 0), 0))
const canFinanceProcess = computed(() => {
  if (!canFinance.value || !currentInvoice.value) return false
  return ['SUBMITTED', 'PROJECT_RETURNED'].includes(currentInvoice.value.status)
})
const canSubmitInfo = computed(() => {
  if (!props.canOperate || canFinance.value) return false
  return !currentInvoice.value || currentInvoice.value.status === 'REJECTED'
})
const canWithdraw = computed(() => !canFinance.value && currentInvoice.value?.status === 'SUBMITTED')
const canProjectConfirm = computed(() => !canFinance.value && currentInvoice.value?.status === 'FINANCE_COMPLETED')
const submitButtonText = computed(() => (currentInvoice.value?.status === 'REJECTED' ? '重新提交开票信息' : '提交开票信息'))
const statusAlertType = computed(() => {
  if (currentInvoice.value?.status === 'REJECTED' || currentInvoice.value?.status === 'PROJECT_RETURNED') return 'warning'
  if (currentInvoice.value?.status === 'FINANCE_COMPLETED') return 'success'
  return 'info'
})
const statusText = computed(() => currentInvoice.value ? invoiceStatusLabel(currentInvoice.value.status) : '')

async function load() {
  if (!props.workOrderId) return
  invoices.value = (await listInvoices()).items.filter(item => item.work_order_id === props.workOrderId)
  const current = currentInvoice.value
  invoiceInfo.value = stripInvoiceUnit(current?.invoice_info || '')
  invoiceType.value = (current?.invoice_type as '专票' | '普票') || '专票'
  if (current?.invoice_info?.includes('开票单位：')) {
    invoiceUnit.value = current.invoice_info.split('开票单位：')[1]?.split('\n')[0] || invoiceUnit.value
  } else {
    invoiceUnit.value = props.flowInfo?.project.undertaking_unit || invoiceUnit.value
  }
  amount.value = current?.amount ?? 0
  financeHandlerId.value = current?.finance_handler_id || financeHandlerId.value
  invoiceFiles.value = (await listWorkOrderFiles(props.workOrderId)).items.filter(
    file => file.file_category === 'INVOICE_FILE' || file.business_stage === 'INVOICE'
  )
}

async function loadFinanceUsers() {
  financeUsers.value = (await listUserCandidates('FINANCE')).items
  if (!financeHandlerId.value && financeUsers.value.length === 1) {
    financeHandlerId.value = financeUsers.value[0].id
  }
}

function stripInvoiceUnit(text: string) {
  if (!text.includes('开票单位：')) return text
  return text.split('\n').slice(1).join('\n')
}

async function onSubmitInfo() {
  if (!props.workOrderId) {
    ElMessage.warning('当前项目暂无关联工单')
    return
  }
  if (!invoiceInfo.value.trim()) {
    ElMessage.warning('请填写开票信息')
    return
  }
  if (!invoiceType.value) {
    ElMessage.warning('请选择发票类型')
    return
  }
  if (!financeHandlerId.value) {
    ElMessage.warning('请选择办理财务人员')
    return
  }
  if (amount.value === null || amount.value < 0) {
    ElMessage.warning('请填写有效的开票金额')
    return
  }
  if (projectAmount.value == null) {
    ElMessage.warning('请先在项目基本信息模块中录入项目金额')
    return
  }
  if (cumulativeAmount.value + amount.value > projectAmount.value) {
    ElMessage.warning('累计开票金额已超过项目金额，请核对后再提交')
    return
  }
  try {
    await createInvoice({
      work_order_id: props.workOrderId,
      invoice_info: `开票单位：${invoiceUnit.value}\n${invoiceInfo.value.trim()}`,
      invoice_type: invoiceType.value,
      amount: amount.value,
      finance_handler_id: financeHandlerId.value,
      status: 'SUBMITTED'
    })
    ElMessage.success('开票信息已提交指定财务人员')
    await load()
    emit('changed')
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '提交开票信息失败')
  }
}

async function onInvoiceFileSelected(file: UploadFile) {
  if (!props.workOrderId || !file.raw) return
  try {
    await uploadWorkOrderFile({
      work_order_id: props.workOrderId,
      file_category: 'INVOICE_FILE',
      business_stage: 'INVOICE',
      file: file.raw
    })
    ElMessage.success('电子票已上传')
    await load()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '电子票上传失败')
  }
}

function setReplaceInput(fileId: number, el: Element | ComponentPublicInstance | null) {
  if (el instanceof HTMLInputElement) {
    replaceInputs.set(fileId, el)
  }
}

function triggerReplace(fileId: number) {
  replaceInputs.get(fileId)?.click()
}

async function onReplaceInput(row: WorkOrderFileItem, event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  try {
    await replaceWorkOrderFile(row.id, file)
    ElMessage.success('电子票已重新上传')
    input.value = ''
    await load()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '电子票重新上传失败')
  }
}

async function onComplete() {
  if (!currentInvoice.value) return
  try {
    await completeInvoice(currentInvoice.value.id)
    ElMessage.success('已提交项目方确认')
    await load()
    emit('changed')
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '确认完成失败')
  }
}

async function onReject() {
  if (!currentInvoice.value) return
  try {
    await rejectInvoice(currentInvoice.value.id, '开票信息有误或不全')
    ElMessage.success('已退回项目方修改开票信息')
    await load()
    emit('changed')
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '退回开票信息失败')
  }
}

async function onProjectConfirm() {
  if (!currentInvoice.value) return
  try {
    await confirmInvoice(currentInvoice.value.id)
    ElMessage.success('已确认开票完成，可再次发起开票')
    await load()
    emit('changed')
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '确认开票完成失败')
  }
}

async function onProjectReturn() {
  if (!currentInvoice.value) return
  try {
    await returnInvoice(currentInvoice.value.id, '项目方退回财务修改')
    ElMessage.success('已退回财务修改')
    await load()
    emit('changed')
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '退回财务修改失败')
  }
}

async function onWithdraw() {
  if (!currentInvoice.value) return
  try {
    await withdrawInvoice(currentInvoice.value.id)
    ElMessage.success('已撤回，可修改后重新提交')
    await load()
    emit('changed')
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '撤回失败')
  }
}

async function copyInfo() {
  const text = [
    `开票信息：${invoiceInfo.value}`,
    `发票类型：${invoiceType.value}`,
    `开票金额：${amount.value.toFixed(2)}`
  ].join('\n')
  try {
    if (!navigator.clipboard?.writeText) throw new Error('clipboard api unavailable')
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
  ElMessage.success('已复制开票信息')
}

function download(file: WorkOrderFileItem) {
  downloadWorkOrderFile(file.id, file.origin_file_name)
}

function invoiceStatusLabel(status: string) {
  const labels: Record<string, string> = {
    SUBMITTED: '开票信息已提交，等待财务处理',
    PROJECT_RETURNED: '项目方已退回，等待财务修改',
    FINANCE_COMPLETED: '财务已完成，等待项目方确认',
    REJECTED: '财务已退回，等待项目方修改',
    ISSUED: '项目方已确认完成',
    PENDING: '待提交'
  }
  return labels[status] || status
}

function userName(userId?: number | null) {
  if (!userId) return '-'
  return financeUsers.value.find(user => user.id === userId)?.real_name || `用户${userId}`
}

function formatAmount(value?: number | null) {
  if (value == null) return '-'
  return Number(value).toFixed(2)
}

onMounted(async () => {
  await loadFinanceUsers()
  await load()
})
watch(() => [props.workOrderId, props.flowInfo?.current_work_order_status], load)
</script>

<style scoped>
.download-list {
  display: grid;
  gap: 6px;
}

.download-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.finance-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.hidden-file-input {
  display: none;
}

.invoice-summary {
  margin-bottom: 12px;
}
</style>
