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
    <el-form label-width="96px">
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
      <el-form-item>
        <el-space wrap>
          <el-button type="primary" :disabled="!canSubmitInfo" @click="onSubmitInfo">提交开票信息</el-button>
          <el-button v-if="canFinance" @click="copyInfo">一键复制</el-button>
          <el-button v-if="canFinance" type="warning" plain :disabled="!currentInvoice" @click="onReject">信息有误返回上一级</el-button>
        </el-space>
      </el-form-item>
    </el-form>

    <template v-if="canFinance">
      <el-divider>财务处理</el-divider>
      <el-upload :auto-upload="false" :on-change="onInvoiceFileSelected" :show-file-list="false">
        <el-button type="primary" :disabled="!currentInvoice">上传电子票</el-button>
      </el-upload>
      <el-button
        type="success"
        style="margin-left: 12px"
        :disabled="!currentInvoice || invoiceFiles.length === 0"
        @click="onComplete"
      >
        确认完成
      </el-button>
    </template>

    <el-divider>发票下载</el-divider>
    <div v-if="invoiceFiles.length" class="download-list">
      <div v-for="file in invoiceFiles" :key="file.id" class="download-item">
        <span>{{ file.origin_file_name }}</span>
        <el-button type="primary" link @click="download(file)">下载</el-button>
        <el-button v-if="canFinance" type="warning" link @click="triggerReplace(file.id)">重新上传</el-button>
        <input
          :ref="el => setReplaceInput(file.id, el)"
          class="hidden-file-input"
          type="file"
          @change="event => onReplaceInput(file, event)"
        />
      </div>
    </div>
    <span v-else>-</span>
  </template>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch, type ComponentPublicInstance } from 'vue'
import { ElMessage, type UploadFile } from 'element-plus'
import { completeInvoice, createInvoice, listInvoices, rejectInvoice, type InvoiceItem } from '@/api/finance'
import { downloadWorkOrderFile, listWorkOrderFiles, replaceWorkOrderFile, uploadWorkOrderFile, type WorkOrderFileItem } from '@/api/files'
import type { ProjectFlowData } from '@/api/projectFlow'

const props = defineProps<{ workOrderId?: number; canOperate: boolean; userRoles: string[]; flowInfo?: ProjectFlowData }>()
const emit = defineEmits<{ (e: 'changed'): void }>()

const loading = ref(false)
const invoices = ref<InvoiceItem[]>([])
const invoiceFiles = ref<WorkOrderFileItem[]>([])
const invoiceInfo = ref('')
const invoiceType = ref<'专票' | '普票'>('专票')
const invoiceUnit = ref('中勤')
const amount = ref(0)

const statusCode = computed(() => props.flowInfo?.current_work_order_status || '')
const canFinance = computed(() => props.userRoles.some(role => ['FINANCE', 'ADMIN'].includes(role)))
const currentInvoice = computed(() => invoices.value.find(item => item.status === 'SUBMITTED' || item.status === 'REJECTED'))
const canSubmitInfo = computed(() => {
  if (!props.canOperate || canFinance.value) return false
  return !currentInvoice.value || currentInvoice.value.status === 'REJECTED'
})
const replaceInputs = new Map<number, HTMLInputElement>()

async function load() {
  if (!props.workOrderId) return
  loading.value = true
  try {
    invoices.value = (await listInvoices()).items.filter(item => item.work_order_id === props.workOrderId)
    const current = currentInvoice.value
    invoiceInfo.value = current?.invoice_info || ''
    invoiceType.value = (current?.invoice_type as '专票' | '普票') || invoiceType.value
    if (current?.invoice_info?.includes('开票单位：')) {
      invoiceUnit.value = current.invoice_info.split('开票单位：')[1]?.split('\n')[0] || invoiceUnit.value
    } else {
      invoiceUnit.value = props.flowInfo?.project.undertaking_unit || invoiceUnit.value
    }
    amount.value = current?.amount ?? 0
    invoiceFiles.value = (await listWorkOrderFiles(props.workOrderId)).items.filter(
      file => file.file_category === 'INVOICE_FILE' || file.business_stage === 'INVOICE'
    )
  } finally {
    loading.value = false
  }
}

async function onSubmitInfo() {
  if (!props.workOrderId) return
  if (!invoiceInfo.value) return ElMessage.warning('请填写开票信息')
  if (!invoiceType.value) return ElMessage.warning('请选择发票类型')
  if (!amount.value || amount.value <= 0) return ElMessage.warning('请填写开票金额')
  await createInvoice({
    work_order_id: props.workOrderId,
    invoice_info: `开票单位：${invoiceUnit.value}\n${invoiceInfo.value}`,
    invoice_type: invoiceType.value,
    amount: amount.value,
    status: 'SUBMITTED'
  })
  ElMessage.success('开票信息已提交财务')
  await load()
  emit('changed')
}

async function onInvoiceFileSelected(file: UploadFile) {
  if (!props.workOrderId || !file.raw) return
  try {
    await uploadWorkOrderFile({ work_order_id: props.workOrderId, file_category: 'INVOICE_FILE', business_stage: 'INVOICE', file: file.raw })
    ElMessage.success('电子票已上传')
    await load()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '电子票上传失败')
  }
}

function setReplaceInput(fileId: number, el: Element | ComponentPublicInstance | null) {
  if (el instanceof HTMLInputElement) replaceInputs.set(fileId, el)
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
  await completeInvoice(currentInvoice.value.id)
  ElMessage.success('开票流程已完成')
  await load()
  emit('changed')
}

async function onReject() {
  if (!currentInvoice.value) return
  await rejectInvoice(currentInvoice.value.id, '开票信息有误或不全')
  ElMessage.success('已退回上一级修改开票信息')
  await load()
  emit('changed')
}

async function copyInfo() {
  const text = `开票信息：${invoiceInfo.value}\n发票类型：${invoiceType.value}\n开票金额：${amount.value.toFixed(2)}`
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

onMounted(load)
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

.hidden-file-input {
  display: none;
}
</style>
