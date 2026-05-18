<template>
  <el-alert
    v-if="!canPrintRoom"
    type="info"
    :closable="false"
    title="当前账号仅可查看报告出具信息。"
    show-icon
    style="margin-bottom: 12px"
  />
  <el-alert
    v-if="!workOrderId"
    type="warning"
    :closable="false"
    title="当前项目暂无关联工单，无法办理报告出具。"
    show-icon
    style="margin-bottom: 12px"
  />

  <template v-if="workOrderId">
    <el-form label-width="120px">
      <el-form-item label="正式合同编号">
        <el-input v-model="contractNo" :disabled="!canPrintRoom" />
      </el-form-item>
      <el-form-item label="纸质报告编号">
        <el-input v-model="paperReportNo" :disabled="!canPrintRoom" />
      </el-form-item>
      <el-form-item label="签字评估师">
        <el-space direction="vertical" alignment="start">
          <el-input v-model="signerOne" disabled placeholder="签字评估师一" style="width: 260px" />
          <el-input v-model="signerTwo" disabled placeholder="签字评估师二" style="width: 260px" />
        </el-space>
      </el-form-item>

      <el-form-item label="签发文件">
        <div class="issue-file-grid">
          <el-card shadow="never" class="issue-file-card">
            <template #header>报告文件</template>
            <div v-if="reviewPackageFiles.length" class="download-list">
              <div v-for="file in reviewPackageFiles" :key="file.id" class="download-item">
                <span>{{ file.origin_file_name }}</span>
                <el-button type="primary" link @click="download(file)">下载</el-button>
              </div>
            </div>
            <span v-else>-</span>
          </el-card>

          <el-card shadow="never" class="issue-file-card">
            <template #header>报告附件</template>
            <div v-if="formalReportFiles.length" class="download-list">
              <div v-for="file in formalReportFiles" :key="file.id" class="download-item">
                <span>{{ file.origin_file_name }}</span>
                <el-button type="primary" link @click="download(file)">下载</el-button>
              </div>
            </div>
            <span v-else>-</span>
          </el-card>

          <el-card shadow="never" class="issue-file-card">
            <template #header>合同扫描件</template>
            <div v-if="contractFiles.length" class="download-list">
              <div v-for="file in contractFiles" :key="file.id" class="download-item">
                <span>{{ file.origin_file_name }}</span>
                <el-button type="primary" link @click="download(file)">下载</el-button>
              </div>
            </div>
            <span v-else>-</span>
          </el-card>
        </div>
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

      <el-form-item label="出具数量">
        <el-input-number v-model="copyCount" :min="1" :disabled="!canPrintRoom" />
      </el-form-item>
      <el-form-item label="备注">
        <el-input v-model="remark" type="textarea" :rows="3" :disabled="!canPrintRoom" />
      </el-form-item>
      <el-form-item>
        <div class="issue-actions">
          <el-button type="primary" :disabled="!canPrintRoom" @click="issueContract">保存正式合同编号</el-button>
          <el-button type="success" :disabled="!canPrintRoom || reportScanFiles.length === 0" @click="issueReport">登记纸质报告出具</el-button>
          <el-button v-if="canProjectMailingStart" type="primary" plain @click="goMailing">邮寄报告</el-button>
          <el-button type="warning" :disabled="!canPrintRoom" @click="rollback">撤回至三审</el-button>
          <el-button type="danger" plain :disabled="!canPrintRoom" @click="contractError">合同错误</el-button>
          <el-button v-if="canReportErrorBack" type="danger" plain @click="reportErrorBack">报告有误返回文印室</el-button>
        </div>
      </el-form-item>
    </el-form>
  </template>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch, type ComponentPublicInstance } from 'vue'
import { ElMessage, type UploadFile } from 'element-plus'
import { getPrintRoomInfo, issueOfficialContract, issuePaperReport, markContractError, reportError, rollbackThird } from '@/api/printRoom'
import { downloadWorkOrderFile, listWorkOrderFiles, replaceWorkOrderFile, uploadWorkOrderFile, type WorkOrderFileItem } from '@/api/files'
import type { ProjectFlowData } from '@/api/projectFlow'
import { startReportMailing } from '@/api/reportMailing'
import { useAuthStore } from '@/store/auth'

const props = defineProps<{ workOrderId?: number; canOperate: boolean; userRoles?: string[]; flowInfo?: ProjectFlowData }>()
const emit = defineEmits<{
  (e: 'changed'): void
  (e: 'navigate', key: string): void
}>()
const auth = useAuthStore()

const contractNo = ref('')
const paperReportNo = ref('')
const copyCount = ref(1)
const remark = ref('')
const signerOne = ref('')
const signerTwo = ref('')
const contractFiles = ref<WorkOrderFileItem[]>([])
const formalReportFiles = ref<WorkOrderFileItem[]>([])
const reportScanFiles = ref<WorkOrderFileItem[]>([])
const reviewPackageFiles = ref<WorkOrderFileItem[]>([])
const replaceInputs = new Map<number, HTMLInputElement>()
const REVIEW_STAGE_ORDER: Record<string, number> = {
  REVIEW_FIRST: 1,
  REVIEW_SECOND: 2,
  REVIEW_THIRD: 3,
  REVIEW_EXTERNAL_FIRST: 4,
  REVIEW_EXTERNAL_SECOND: 5,
  REVIEW_EXTERNAL_THIRD: 6
}

const isPrintRoomRole = computed(() => Boolean(props.userRoles?.includes('PRINT_ROOM')))
const isAssignedPrintRoomHandler = computed(() => Boolean(
  auth.user?.id &&
  (
    props.flowInfo?.current_handler_user_id === auth.user.id ||
    props.flowInfo?.print_room_handler_id === auth.user.id
  )
))
const isReportIssueStage = computed(() =>
  props.flowInfo?.current_work_order_status === 'PRINTROOM_PROCESSING' ||
  props.flowInfo?.project.current_step === '报告出具'
)
const canHandlePrintRoom = computed(() => Boolean(
  isReportIssueStage.value &&
  (
    props.userRoles?.some(role => ['PRINT_ROOM', 'ADMIN', '文印室'].includes(role)) ||
    isAssignedPrintRoomHandler.value ||
    props.flowInfo?.user_role_in_project === '文印室'
  )
))
const canReplaceReportScan = computed(() => canHandlePrintRoom.value)
const canPrintRoom = computed(() => Boolean(
  canHandlePrintRoom.value
))
const canReportErrorBack = computed(() => Boolean(
  props.userRoles?.some(role => ['PROJECT_LEADER', 'PROJECT_MEMBER', 'ADMIN'].includes(role)) &&
  !isPrintRoomRole.value &&
  ['WAIT_INVOICE_INFO', 'PAPER_REPORT_ISSUED', 'INVOICE_INFO_REJECTED'].includes(props.flowInfo?.current_work_order_status || '')
))
const canProjectMailingStart = computed(() => Boolean(
  props.userRoles?.some(role => ['PROJECT_LEADER', 'PROJECT_MEMBER', 'ADMIN'].includes(role)) &&
  !isPrintRoomRole.value &&
  ['PAPER_REPORT_ISSUED', 'WAIT_INVOICE_INFO', 'INVOICE_INFO_REJECTED', 'INVOICE_PROCESSING', 'INVOICE_ISSUED', 'REPORT_MAILING', 'REPORT_MAILING_COMPLETED'].includes(props.flowInfo?.current_work_order_status || '')
))

async function loadFiles() {
  signerOne.value = props.flowInfo?.signer_one || ''
  signerTwo.value = props.flowInfo?.signer_two || ''
  copyCount.value = props.flowInfo?.formal_report_count || copyCount.value
  if (!props.workOrderId) {
    contractFiles.value = []
    formalReportFiles.value = []
    reportScanFiles.value = []
    reviewPackageFiles.value = []
    return
  }
  const info = await getPrintRoomInfo(props.workOrderId)
  contractNo.value = info.contract_no || ''
  paperReportNo.value = info.paper_report_no || ''
  copyCount.value = info.copy_count || info.formal_report_count || props.flowInfo?.formal_report_count || copyCount.value || 1
  remark.value = info.remark || ''
  const files = (await listWorkOrderFiles(props.workOrderId)).items
  contractFiles.value = latestByCategory(files, 'FINAL_CONTRACT_SCAN')
  formalReportFiles.value = latestByCategory(files, 'FORMAL_REPORT')
  reportScanFiles.value = latestByCategory(files, 'REPORT_SCAN')
  reviewPackageFiles.value = latestReviewPackage(files)
}

function activeManualFiles(files: WorkOrderFileItem[]) {
  return files.filter(file => file.is_current && file.source_type !== 'SIGNOFF_SYNC')
}

function fileSortValue(file: WorkOrderFileItem) {
  const uploadedAt = file.uploaded_at ? new Date(file.uploaded_at).getTime() : 0
  return uploadedAt || file.id
}

function latestByCategory(files: WorkOrderFileItem[], category: string) {
  const candidates = activeManualFiles(files).filter(file => file.file_category === category || file.business_stage === category)
  if (!candidates.length) return []
  return [candidates.sort((a, b) => fileSortValue(b) - fileSortValue(a) || b.version_no - a.version_no || b.id - a.id)[0]]
}

function latestReviewPackage(files: WorkOrderFileItem[]) {
  const candidates = activeManualFiles(files).filter(file => file.file_category === 'REPORT_ZIP' && file.business_stage.startsWith('REVIEW_'))
  if (!candidates.length) return []
  const maxStageOrder = Math.max(...candidates.map(file => REVIEW_STAGE_ORDER[file.business_stage] || 0))
  const finalStageFiles = candidates.filter(file => (REVIEW_STAGE_ORDER[file.business_stage] || 0) === maxStageOrder)
  const maxVersion = Math.max(...finalStageFiles.map(file => file.version_no || 0))
  return finalStageFiles
    .filter(file => (file.version_no || 0) === maxVersion)
    .sort((a, b) => fileSortValue(b) - fileSortValue(a) || b.id - a.id)
    .slice(0, 1)
}

async function issueContract() {
  if (!props.workOrderId || !contractNo.value.trim()) {
    ElMessage.warning('请填写正式合同编号')
    return
  }
  await issueOfficialContract({ work_order_id: props.workOrderId, contract_no: contractNo.value.trim(), remark: remark.value || undefined })
  ElMessage.success('正式合同出具成功')
  emit('changed')
}

async function issueReport() {
  if (!props.workOrderId || !paperReportNo.value.trim()) {
    ElMessage.warning('请填写纸质报告编号')
    return
  }
  if (!reportScanFiles.value.length) {
    ElMessage.warning('请先上传报告扫描件')
    return
  }
  await issuePaperReport({
    work_order_id: props.workOrderId,
    paper_report_no: paperReportNo.value.trim(),
    copy_count: copyCount.value,
    remark: remark.value || undefined,
  })
  ElMessage.success('纸质报告登记成功')
  emit('changed')
}

async function onScanSelected(file: UploadFile) {
  if (!props.workOrderId || !file.raw) return
  await uploadWorkOrderFile({
    work_order_id: props.workOrderId,
    file_category: 'REPORT_SCAN',
    business_stage: 'REPORT_SCAN',
    file: file.raw,
  })
  ElMessage.success('报告扫描件已上传')
  await loadFiles()
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
  await replaceWorkOrderFile(row.id, file)
  ElMessage.success('报告扫描件已替换')
  input.value = ''
  await loadFiles()
}

async function rollback() {
  if (!props.workOrderId) return
  try {
    await rollbackThird({ work_order_id: props.workOrderId, remark: remark.value || undefined })
    ElMessage.success('已撤回至三审')
    emit('changed')
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '撤回至三审失败')
  }
}

async function contractError() {
  if (!props.workOrderId) return
  await markContractError({ work_order_id: props.workOrderId, remark: remark.value || undefined })
  ElMessage.success('已退回合同初稿上传')
  emit('changed')
}

async function reportErrorBack() {
  if (!props.workOrderId) return
  await reportError({ work_order_id: props.workOrderId, remark: remark.value || undefined })
  ElMessage.success('已退回文印室')
  emit('changed')
}

async function goMailing() {
  if (!props.workOrderId) {
    ElMessage.warning('当前项目暂无关联工单')
    return
  }
  try {
    if (!['REPORT_MAILING', 'REPORT_MAILING_COMPLETED'].includes(props.flowInfo?.current_work_order_status || '')) {
      await startReportMailing(props.workOrderId)
      ElMessage.success('已进入报告邮寄')
    }
    emit('navigate', 'mailing')
    emit('changed')
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '进入报告邮寄失败')
  }
}

function download(file: WorkOrderFileItem) {
  downloadWorkOrderFile(file.id, file.origin_file_name)
}

onMounted(loadFiles)
watch(() => [props.workOrderId, props.flowInfo?.signer_one, props.flowInfo?.signer_two, props.flowInfo?.current_work_order_status], loadFiles)
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

.issue-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.hidden-file-input {
  display: none;
}

.issue-file-grid {
  width: 100%;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.issue-file-card {
  min-width: 0;
}

@media (max-width: 900px) {
  .issue-file-grid {
    grid-template-columns: 1fr;
  }
}
</style>
