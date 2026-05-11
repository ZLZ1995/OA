<template>
  <el-alert v-if="!canPrintRoom" type="info" :closable="false" title="当前账号仅可查看报告出具信息。" show-icon style="margin-bottom:12px" />
  <el-alert v-if="!workOrderId" type="warning" :closable="false" title="当前项目暂无关联工单，无法办理报告出具。" show-icon style="margin-bottom:12px" />
  <template v-if="workOrderId">
    <el-form label-width="120px">
      <el-form-item label="正式合同编号"><el-input v-model="contractNo" :disabled="!canPrintRoom" /></el-form-item>
      <el-form-item label="纸质报告编号"><el-input v-model="paperReportNo" :disabled="!canPrintRoom" /></el-form-item>
      <el-form-item label="签字评估师姓名">
        <el-space direction="vertical" alignment="start">
          <el-input v-model="signerOne" disabled placeholder="签字评估师一" style="width: 260px" />
          <el-input v-model="signerTwo" disabled placeholder="签字评估师二" style="width: 260px" />
        </el-space>
      </el-form-item>
      <el-form-item label="合同扫描件下载">
        <div v-if="contractFiles.length" class="download-list">
          <div v-for="file in contractFiles" :key="file.id" class="download-item">
            <span>{{ file.origin_file_name }}</span>
            <el-button type="primary" link @click="download(file)">下载</el-button>
            <el-button v-if="canPrintRoom" type="warning" link @click="triggerReplace(file.id)">更换文件</el-button>
            <input
              :ref="el => setReplaceInput(file.id, el)"
              class="hidden-file-input"
              type="file"
              @change="event => onReplaceInput(file, event)"
            />
          </div>
        </div>
        <span v-else>-</span>
      </el-form-item>
      <el-form-item label="正式报告下载">
        <div v-if="formalReportFiles.length" class="download-list">
          <div v-for="file in formalReportFiles" :key="file.id" class="download-item">
            <span>{{ file.origin_file_name }}</span>
            <el-button type="primary" link @click="download(file)">下载</el-button>
          </div>
        </div>
        <span v-else>-</span>
      </el-form-item>
      <el-form-item label="报告扫描件">
        <el-upload v-if="canPrintRoom" :auto-upload="false" :on-change="onScanSelected" :show-file-list="false">
          <el-button type="primary">上传报告扫描件</el-button>
        </el-upload>
        <div v-if="reportScanFiles.length" class="download-list">
          <div v-for="file in reportScanFiles" :key="file.id" class="download-item">
            <span>{{ file.origin_file_name }}</span>
            <el-button type="primary" link @click="download(file)">下载</el-button>
            <el-button v-if="canReplaceReportScan" type="warning" link @click="triggerReplace(file.id)">重新上传</el-button>
            <input
              :ref="el => setReplaceInput(file.id, el)"
              class="hidden-file-input"
              type="file"
              @change="event => onReplaceInput(file, event)"
            />
          </div>
        </div>
        <span v-if="!reportScanFiles.length && !canPrintRoom">-</span>
      </el-form-item>
      <el-form-item label="出具数量"><el-input-number v-model="copyCount" :min="1" :disabled="!canPrintRoom" /></el-form-item>
      <el-form-item label="备注"><el-input v-model="remark" type="textarea" :rows="3" :disabled="!canPrintRoom" /></el-form-item>
      <el-form-item>
        <el-button type="primary" :disabled="!canPrintRoom" @click="issueContract">保存正式合同编号</el-button>
        <el-button type="success" :disabled="!canPrintRoom || reportScanFiles.length === 0" @click="issueReport">登记纸质报告出具</el-button>
        <el-button type="warning" :disabled="!canPrintRoom" @click="rollback">撤回至三审</el-button>
        <el-button type="danger" plain :disabled="!canPrintRoom" @click="contractError">合同错误</el-button>
        <el-button v-if="canReportErrorBack" type="danger" plain @click="reportErrorBack">报告有误返回文印室</el-button>
      </el-form-item>
    </el-form>
  </template>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch, type ComponentPublicInstance } from 'vue'
import { ElMessage, type UploadFile } from 'element-plus'
import { getPrintRoomInfo, issueOfficialContract, issuePaperReport, markContractError, reportError, rollbackThird } from '@/api/printRoom'
import { getWorkOrderFileDownloadUrl, listWorkOrderFiles, replaceWorkOrderFile, uploadWorkOrderFile, type WorkOrderFileItem } from '@/api/files'
import type { ProjectFlowData } from '@/api/projectFlow'

const props = defineProps<{ workOrderId?: number; canOperate: boolean; userRoles?: string[]; flowInfo?: ProjectFlowData }>()
const emit = defineEmits<{ (e: 'changed'): void }>()
const contractNo = ref('')
const paperReportNo = ref('')
const copyCount = ref(1)
const remark = ref('')
const signerOne = ref('')
const signerTwo = ref('')
const contractFiles = ref<WorkOrderFileItem[]>([])
const formalReportFiles = ref<WorkOrderFileItem[]>([])
const reportScanFiles = ref<WorkOrderFileItem[]>([])
const isPrintRoomRole = computed(() => Boolean(props.userRoles?.includes('PRINT_ROOM')))
const canReplaceReportScan = computed(() => Boolean(props.userRoles?.some(role => ['PRINT_ROOM', 'ADMIN'].includes(role))))
const canPrintRoom = computed(() => Boolean(
  props.userRoles?.some(role => ['PRINT_ROOM', 'ADMIN'].includes(role)) &&
  props.flowInfo?.current_work_order_status === 'PRINTROOM_PROCESSING'
))
const canReportErrorBack = computed(() => Boolean(
  props.userRoles?.some(role => ['PROJECT_LEADER', 'PROJECT_MEMBER', 'ADMIN'].includes(role)) &&
  !isPrintRoomRole.value &&
  ['WAIT_INVOICE_INFO', 'PAPER_REPORT_ISSUED', 'INVOICE_INFO_REJECTED'].includes(props.flowInfo?.current_work_order_status || '')
))
const replaceInputs = new Map<number, HTMLInputElement>()

async function loadFiles() {
  signerOne.value = props.flowInfo?.signer_one || ''
  signerTwo.value = props.flowInfo?.signer_two || ''
  copyCount.value = props.flowInfo?.formal_report_count || copyCount.value
  if (!props.workOrderId) {
    contractFiles.value = []
    formalReportFiles.value = []
    reportScanFiles.value = []
    return
  }
  const info = await getPrintRoomInfo(props.workOrderId)
  contractNo.value = info.contract_no || contractNo.value
  paperReportNo.value = info.paper_report_no || paperReportNo.value
  copyCount.value = info.copy_count || copyCount.value
  remark.value = info.remark || remark.value
  const files = (await listWorkOrderFiles(props.workOrderId)).items
  contractFiles.value = files.filter(file => file.file_category === 'CONTRACT' || file.business_stage === 'CONTRACT')
  formalReportFiles.value = files.filter(file => file.file_category === 'FORMAL_REPORT' || file.business_stage === 'FORMAL_REPORT')
  reportScanFiles.value = files.filter(file => file.file_category === 'REPORT_SCAN' || file.business_stage === 'REPORT_SCAN')
}

async function issueContract() {
  if (!props.workOrderId || !contractNo.value) return ElMessage.warning('请填写正式合同编号')
  await issueOfficialContract({ work_order_id: props.workOrderId, contract_no: contractNo.value, remark: remark.value || undefined })
  ElMessage.success('正式合同出具成功')
  emit('changed')
}

async function issueReport() {
  if (!props.workOrderId || !paperReportNo.value) return ElMessage.warning('请填写纸质报告编号')
  if (!reportScanFiles.value.length) return ElMessage.warning('请先上传报告扫描件')
  await issuePaperReport({ work_order_id: props.workOrderId, paper_report_no: paperReportNo.value, copy_count: copyCount.value, remark: remark.value || undefined })
  ElMessage.success('纸质报告登记成功')
  emit('changed')
}

async function onScanSelected(file: UploadFile) {
  if (!props.workOrderId || !file.raw) return
  await uploadWorkOrderFile({ work_order_id: props.workOrderId, file_category: 'REPORT_SCAN', business_stage: 'REPORT_SCAN', file: file.raw })
  ElMessage.success('报告扫描件已上传')
  await loadFiles()
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
  await replaceWorkOrderFile(row.id, file)
  ElMessage.success('报告扫描件已更换')
  input.value = ''
  await loadFiles()
}

async function rollback() {
  if (!props.workOrderId) return
  await rollbackThird({ work_order_id: props.workOrderId, remark: remark.value || undefined })
  ElMessage.success('已撤回至三审')
  emit('changed')
}

async function contractError() {
  if (!props.workOrderId) return
  await markContractError({ work_order_id: props.workOrderId, remark: remark.value || undefined })
  ElMessage.success('已退回合同上传')
  emit('changed')
}

async function reportErrorBack() {
  if (!props.workOrderId) return
  await reportError({ work_order_id: props.workOrderId, remark: remark.value || undefined })
  ElMessage.success('已退回文印室')
  emit('changed')
}

function download(file: WorkOrderFileItem) {
  window.open(getWorkOrderFileDownloadUrl(file.id), '_blank')
}

onMounted(loadFiles)
watch(() => [props.workOrderId, props.flowInfo?.signer_one, props.flowInfo?.signer_two], loadFiles)
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
