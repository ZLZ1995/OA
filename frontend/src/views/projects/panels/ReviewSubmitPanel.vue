<template>
  <el-alert
    v-if="!workOrderId"
    type="warning"
    :closable="false"
    title="当前项目暂无关联工单，无法办理报告送审。"
    show-icon
  />
  <template v-else>
    <el-form label-width="120px">
      <el-form-item label="审核轮次">
        <el-select v-model="reviewRound" style="width: 180px" :disabled="!canSubmitReview" @change="reloadRoundData">
          <el-option label="一审" value="FIRST" />
          <el-option label="二审" value="SECOND" />
          <el-option label="三审" value="THIRD" />
        </el-select>
      </el-form-item>
      <el-form-item label="审核老师" v-if="canSubmitReview && !isReplyFlow">
        <el-select v-model="reviewerUserId" placeholder="选择审核老师" style="width: 320px">
          <el-option v-for="u in userOptions" :key="u.user_id" :label="`${u.real_name}(${u.username})`" :value="u.user_id" />
        </el-select>
      </el-form-item>

      <el-form-item v-if="showContractDraftDownload" label="合同初稿下载">
        <div v-if="contractDraftFiles.length" class="contract-file-list">
          <div v-for="file in contractDraftFiles" :key="file.id" class="contract-file-item">
            <span>{{ file.origin_file_name }}（{{ formatFileSize(file.file_size) }}）</span>
            <el-button type="primary" plain @click="download(file)">下载合同初稿</el-button>
          </div>
        </div>
        <span v-else>-</span>
      </el-form-item>

      <el-form-item :label="isReplyFlow ? '意见回复文件' : '待审报告包'">
        <el-upload :auto-upload="false" :on-change="onReportSelected" :show-file-list="false" :disabled="!canSubmitReview">
          <el-button :disabled="!canSubmitReview">{{ isReplyFlow ? '上传审核意见回复' : '上传待审报告' }}</el-button>
        </el-upload>
        <div class="file-list" v-if="submitFiles.length">
          <el-tag v-for="file in submitFiles" :key="file.id" type="info" effect="plain">
            {{ file.origin_file_name }}（{{ formatFileSize(file.file_size) }}）
          </el-tag>
        </div>
      </el-form-item>
      <el-form-item label="送审备注" v-if="canSubmitReview">
        <el-input v-model="comment" type="textarea" :rows="3" />
      </el-form-item>
      <el-form-item>
        <el-space wrap>
          <el-button type="primary" :disabled="!canSubmitReview || submitFiles.length === 0" @click="onSubmit">
            {{ isReplyFlow ? '提交审核意见回复' : '提交审核' }}
          </el-button>
          <el-tag :type="statusTagType" effect="plain">{{ reviewStatusText }}</el-tag>
        </el-space>
      </el-form-item>
    </el-form>

    <template v-if="canReview">
      <el-divider>审核处理</el-divider>
      <el-form label-width="120px">
        <el-form-item label="合同初稿">
          <div v-if="contractDraftFiles.length" class="contract-file-list">
            <div v-for="file in contractDraftFiles" :key="file.id" class="contract-file-item">
              <span>{{ file.origin_file_name }}（{{ formatFileSize(file.file_size) }}）</span>
              <el-button type="primary" plain @click="download(file)">下载合同初稿</el-button>
            </div>
          </div>
          <span v-else>-</span>
        </el-form-item>
        <el-form-item label="审核意见">
          <el-input v-model="reviewComment" type="textarea" :rows="3" placeholder="请输入审核意见" />
        </el-form-item>
        <el-form-item label="意见附件">
          <el-upload :auto-upload="false" :on-change="onOpinionSelected" :show-file-list="false">
            <el-button>上传审核意见文件</el-button>
          </el-upload>
          <div class="file-list" v-if="opinionFiles.length">
            <el-tag v-for="file in opinionFiles" :key="file.id" type="info" effect="plain">
              {{ file.origin_file_name }}（{{ formatFileSize(file.file_size) }}）
            </el-tag>
          </div>
        </el-form-item>
        <el-form-item>
          <el-space>
            <el-button type="success" @click="onDecision('APPROVE')">审核通过</el-button>
            <el-button type="danger" plain @click="onDecision('REJECT_RETURN')">返回修改</el-button>
          </el-space>
        </el-form-item>
      </el-form>
    </template>

    <template v-if="showFormalReportPanel">
      <el-divider>三审通过后资料</el-divider>
      <el-alert
        v-if="!finalContractFiles.length"
        type="warning"
        :closable="false"
        title="合同扫描件为必传项，未上传前不能转发文印室。"
        show-icon
        style="margin-bottom: 12px"
      />
      <el-form label-width="120px">
        <el-form-item label="正式报告文件">
          <el-upload :auto-upload="false" :on-change="onFormalReportSelected" :show-file-list="false">
            <el-button type="primary">上传正式报告文件</el-button>
          </el-upload>
          <div class="file-list" v-if="formalReportFiles.length">
            <el-tag v-for="file in formalReportFiles" :key="file.id" type="info" effect="plain">
              {{ file.origin_file_name }}（{{ formatFileSize(file.file_size) }}）
            </el-tag>
          </div>
        </el-form-item>
        <el-form-item label="合同扫描件">
          <el-upload :auto-upload="false" :on-change="onFinalContractSelected" :show-file-list="false">
            <el-button type="primary">上传合同扫描件</el-button>
          </el-upload>
          <div class="file-list" v-if="finalContractFiles.length">
            <el-tag v-for="file in finalContractFiles" :key="file.id" type="success" effect="plain">
              {{ file.origin_file_name }}（{{ formatFileSize(file.file_size) }}）
            </el-tag>
          </div>
        </el-form-item>
        <el-form-item label="签字评估师">
          <el-space wrap>
            <el-input v-model="signerOne" placeholder="签字评估师一" style="width: 220px" />
            <el-input v-model="signerTwo" placeholder="签字评估师二" style="width: 220px" />
          </el-space>
        </el-form-item>
        <el-form-item label="出具报告数量">
          <el-input-number v-model="formalReportCount" :min="1" />
        </el-form-item>
        <el-form-item label="文印室人员">
          <el-select v-model="printRoomHandlerId" placeholder="选择文印室人员" style="width: 260px">
            <el-option v-for="user in printRoomOptions" :key="user.id" :label="`${user.real_name}(${user.username})`" :value="user.id" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="success" :disabled="formalReportFiles.length === 0" @click="onTransferPrintRoom">转发文印室</el-button>
        </el-form-item>
      </el-form>
    </template>

    <el-divider>审核记录</el-divider>
    <el-table :data="reviewRows" v-loading="loading">
      <el-table-column prop="roundLabel" label="轮次" width="180" />
      <el-table-column prop="reviewerName" label="本轮审核人" width="120" show-overflow-tooltip />
      <el-table-column prop="comment" label="意见" min-width="160" show-overflow-tooltip />
      <el-table-column label="附件" min-width="280">
        <template #default="{ row }">
          <div v-if="row.files.length" class="attachment-list">
            <div v-for="file in row.files" :key="file.id" class="attachment-item">
              <span>{{ file.origin_file_name }}（{{ formatFileSize(file.file_size) }}）</span>
              <el-button type="primary" link @click="download(file)">下载</el-button>
              <el-button v-if="canWithdrawRow(row)" type="danger" link @click="onWithdraw">撤回</el-button>
            </div>
          </div>
          <template v-else>
            <span>-</span>
            <el-button v-if="canWithdrawRow(row)" type="danger" link @click="onWithdraw">撤回</el-button>
          </template>
        </template>
      </el-table-column>
      <el-table-column prop="acted_at" label="时间" width="200" />
    </el-table>
  </template>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage, type UploadFile } from 'element-plus'
import { decideReview, listReviewCandidates, listReviews, submitReview, withdrawLatestReview, type ReviewCandidateItem, type ReviewRecordItem } from '@/api/reviews'
import { getWorkOrderFileDownloadUrl, listWorkOrderFiles, uploadWorkOrderFile, type WorkOrderFileItem } from '@/api/files'
import { useAuthStore } from '@/store/auth'
import type { ProjectFlowData } from '@/api/projectFlow'
import { updateWorkOrder } from '@/api/workorders'
import { transferPrintRoom } from '@/api/printRoom'
import { listUserCandidates, type UserItem } from '@/api/users'

const props = defineProps<{ workOrderId?: number; canEdit: boolean; userRoles: string[]; flowInfo?: ProjectFlowData }>()
const emit = defineEmits<{ (e: 'changed'): void }>()

type ReviewRound = 'FIRST' | 'SECOND' | 'THIRD'

interface ReviewRow {
  id: string
  recordId?: number
  action?: ReviewRecordItem['action']
  reviewRound?: ReviewRound
  reviewerUserId?: number
  reviewerName: string
  roundLabel: string
  comment: string
  acted_at: string
  files: WorkOrderFileItem[]
}

const auth = useAuthStore()
const reviewRound = ref<ReviewRound>('FIRST')
const reviewerUserId = ref<number>()
const comment = ref('')
const reviewComment = ref('')
const signerOne = ref('')
const signerTwo = ref('')
const formalReportCount = ref(1)
const printRoomHandlerId = ref<number>()
const printRoomOptions = ref<UserItem[]>([])
const records = ref<ReviewRecordItem[]>([])
const files = ref<WorkOrderFileItem[]>([])
const userOptions = ref<ReviewCandidateItem[]>([])
const loading = ref(false)

const statusCode = computed(() => props.flowInfo?.current_work_order_status || '')
const currentUserId = computed(() => auth.user?.id)
const isCurrentHandler = computed(() => Boolean(currentUserId.value && props.flowInfo?.current_handler_user_id === currentUserId.value))
const isReviewSubmitter = computed(() => {
  const roleName = props.flowInfo?.user_role_in_project
  return roleName === '项目负责人' || roleName === '创建人' || isCurrentHandler.value
})
const isReplyFlow = computed(() => ['FIRST_REVIEW_REJECTED', 'SECOND_REVIEW_REJECTED', 'THIRD_REVIEW_REJECTED'].includes(statusCode.value))
const currentRoundReviewerId = computed(() => {
  if (reviewRound.value === 'FIRST') return props.flowInfo?.first_reviewer_id
  if (reviewRound.value === 'SECOND') return props.flowInfo?.second_reviewer_id
  return props.flowInfo?.third_reviewer_id
})
const canSubmitReview = computed(() => props.canEdit && isReviewSubmitter.value && isSubmitStatus(statusCode.value))
const canReview = computed(() => {
  if (!currentUserId.value || props.flowInfo?.current_handler_user_id !== currentUserId.value) return false
  if (props.userRoles.includes('ADMIN')) return true
  return (
    (reviewRound.value === 'FIRST' && props.userRoles.includes('FIRST_REVIEWER') && statusCode.value === 'FIRST_REVIEWING') ||
    (reviewRound.value === 'SECOND' && props.userRoles.includes('SECOND_REVIEWER') && statusCode.value === 'SECOND_REVIEWING') ||
    (reviewRound.value === 'THIRD' && props.userRoles.includes('THIRD_REVIEWER') && statusCode.value === 'THIRD_REVIEWING')
  )
})
const canUploadFormalReport = computed(() => {
  if (!props.canEdit || statusCode.value !== 'THIRD_APPROVED_WAIT_PRINTROOM') return false
  if (props.userRoles.includes('ADMIN')) return true
  return Boolean(
    currentUserId.value &&
    currentUserId.value === props.flowInfo?.third_reviewer_id &&
    props.userRoles.includes('THIRD_REVIEWER')
  )
})
const showFormalReportPanel = computed(() => canUploadFormalReport.value)
const showContractDraftDownload = computed(() => ['FIRST_REVIEWER', 'SECOND_REVIEWER', 'THIRD_REVIEWER'].some(role => props.userRoles.includes(role)))

const reviewPackageFiles = computed(() => files.value.filter(file => file.file_category === 'REPORT_ZIP' && file.business_stage === reviewStage(reviewRound.value)))
const replyFiles = computed(() => files.value.filter(file => file.file_category === 'REVIEW_REPLY' && file.business_stage === reviewStage(reviewRound.value)))
const submitFiles = computed(() => isReplyFlow.value ? replyFiles.value : reviewPackageFiles.value)
const opinionFiles = computed(() => files.value.filter(file => file.file_category === 'REVIEW_OPINION' && file.business_stage === reviewStage(reviewRound.value)))
const formalReportFiles = computed(() => files.value.filter(file => file.file_category === 'FORMAL_REPORT' && file.business_stage === 'FORMAL_REPORT'))
const contractDraftFiles = computed(() => files.value.filter(file => file.file_category === 'CONTRACT_DRAFT' && file.business_stage === 'CONTRACT_DRAFT' && file.is_current))
const finalContractFiles = computed(() => files.value.filter(file => file.file_category === 'FINAL_CONTRACT_SCAN' && file.business_stage === 'FINAL_CONTRACT_SCAN' && file.is_current))

const reviewStatusText = computed(() => {
  if (isReplyFlow.value) return `${roundLabel(reviewRound.value)}意见已返回等待回复`
  if (isSubmitStatus(statusCode.value)) {
    return submitFiles.value.length ? '待提交审核' : '待上传文件'
  }
  return REVIEW_STATUS_TEXT[statusCode.value] || '当前暂无报告送审任务'
})
const statusTagType = computed(() => {
  if (statusCode.value.includes('REJECTED')) return 'warning'
  if (statusCode.value.includes('REVIEWING')) return 'primary'
  if (statusCode.value.includes('APPROVED')) return 'success'
  return 'info'
})

const reviewRows = computed<ReviewRow[]>(() => {
  const rows: ReviewRow[] = records.value.map(record => ({
    id: `record-${record.id}`,
    recordId: record.id,
    action: record.action,
    reviewRound: record.review_round,
    reviewerUserId: record.reviewer_user_id,
    reviewerName: record.reviewer_name || '-',
    roundLabel: recordRoundLabel(record),
    comment: recordCommentText(record),
    acted_at: record.acted_at,
    files: filesForRecord(record)
  }))
  const recordedReplyRounds = new Set(records.value.filter(record => record.action === 'SUBMIT').map(record => record.review_round))
  for (const file of files.value.filter(item => item.file_category === 'REVIEW_REPLY')) {
    const round = roundFromStage(file.business_stage)
    if (round && !recordedReplyRounds.has(round)) {
      rows.push({
        id: `reply-file-${file.id}`,
        reviewerName: '-',
        roundLabel: `${roundLabel(round)}意见回复`,
        comment: '-',
        acted_at: file.uploaded_at,
        files: [file]
      })
    }
  }
  return rows
})

const REVIEW_STATUS_TEXT: Record<string, string> = {
  CONTRACT_APPROVED: '合同初稿审核已通过，待上传待审报告',
  WAIT_FIRST_REVIEW_SUBMIT: '待上传文件',
  FIRST_REVIEWING: '一审审核中',
  FIRST_REVIEW_REJECTED: '一审意见已返回等待回复',
  WAIT_SECOND_REVIEW_SUBMIT: '一审已通过，待提交二审',
  SECOND_REVIEWING: '二审审核中',
  SECOND_REVIEW_REJECTED: '二审意见已返回等待回复',
  WAIT_THIRD_REVIEW_SUBMIT: '二审已通过，待提交三审',
  THIRD_REVIEWING: '三审审核中',
  THIRD_REVIEW_REJECTED: '三审意见已返回等待回复',
  THIRD_APPROVED_WAIT_PRINTROOM: '三审已通过，待补充正式报告与合同扫描件'
}

function isSubmitStatus(status: string) {
  return ['CONTRACT_APPROVED', 'WAIT_FIRST_REVIEW_SUBMIT', 'FIRST_REVIEW_REJECTED', 'WAIT_SECOND_REVIEW_SUBMIT', 'SECOND_REVIEW_REJECTED', 'WAIT_THIRD_REVIEW_SUBMIT', 'THIRD_REVIEW_REJECTED'].includes(status)
}

function syncRoundWithStatus() {
  const status = statusCode.value
  if (status.includes('SECOND')) reviewRound.value = 'SECOND'
  else if (status.includes('THIRD')) reviewRound.value = 'THIRD'
  else reviewRound.value = 'FIRST'
}

function reviewStage(round: ReviewRound) {
  return `REVIEW_${round}`
}

function roundLabel(round: ReviewRound) {
  return ({ FIRST: '一审', SECOND: '二审', THIRD: '三审' } as const)[round]
}

function roundFromStage(stage: string): ReviewRound | undefined {
  if (stage === 'REVIEW_FIRST') return 'FIRST'
  if (stage === 'REVIEW_SECOND') return 'SECOND'
  if (stage === 'REVIEW_THIRD') return 'THIRD'
  return undefined
}

function recordRoundLabel(record: ReviewRecordItem) {
  if (record.action === 'SUBMIT') return hasEarlierReject(record) ? `${roundLabel(record.review_round)}意见回复` : '报告送审'
  if (record.action === 'REJECT_RETURN') return `${roundLabel(record.review_round)}意见发出`
  if (record.action === 'APPROVE' && record.review_round === 'THIRD') return '报告审核通过待提交正式报告文件'
  return roundLabel(record.review_round)
}

function recordCommentText(record: ReviewRecordItem) {
  if (record.action === 'APPROVE') return record.comment || '审核通过'
  return record.comment || '-'
}

function hasEarlierReject(record: ReviewRecordItem) {
  return records.value.some(item =>
    item.review_round === record.review_round &&
    item.action === 'REJECT_RETURN' &&
    new Date(item.acted_at).getTime() < new Date(record.acted_at).getTime()
  )
}

function filesForRecord(record: ReviewRecordItem) {
  const stage = reviewStage(record.review_round)
  const recordTime = new Date(record.acted_at).getTime()
  const previousRecord = records.value
    .filter(item => new Date(item.acted_at).getTime() < recordTime)
    .sort((a, b) => new Date(b.acted_at).getTime() - new Date(a.acted_at).getTime())[0]
  const previousTime = previousRecord ? new Date(previousRecord.acted_at).getTime() : 0
  const inCurrentRecordWindow = (file: WorkOrderFileItem) => {
    const uploadedTime = new Date(file.uploaded_at).getTime()
    return uploadedTime > previousTime && uploadedTime <= recordTime
  }
  if (record.action === 'SUBMIT') {
    const category = hasEarlierReject(record) ? 'REVIEW_REPLY' : 'REPORT_ZIP'
    return files.value.filter(file => file.file_category === category && file.business_stage === stage && inCurrentRecordWindow(file))
  }
  return files.value.filter(file => file.file_category === 'REVIEW_OPINION' && file.business_stage === stage && inCurrentRecordWindow(file))
}

function formatFileSize(size?: number | null) {
  if (!size) return '-'
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / 1024 / 1024).toFixed(1)} MB`
}

async function loadCandidates() {
  if (isReplyFlow.value) {
    reviewerUserId.value = currentRoundReviewerId.value || undefined
    userOptions.value = []
    return
  }
  if (!props.workOrderId || !canSubmitReview.value) {
    userOptions.value = []
    return
  }
  userOptions.value = (await listReviewCandidates(props.workOrderId, reviewRound.value)).items
}

async function loadFiles() {
  if (!props.workOrderId) {
    files.value = []
    return
  }
  files.value = (await listWorkOrderFiles(props.workOrderId)).items
}

async function loadRecords() {
  if (!props.workOrderId) return
  loading.value = true
  try {
    records.value = (await listReviews(props.workOrderId)).items
  } finally {
    loading.value = false
  }
}

async function reloadRoundData() {
  await Promise.all([loadCandidates(), loadFiles()])
}

async function onReportSelected(file: UploadFile) {
  if (!props.workOrderId || !file.raw) return
  await uploadWorkOrderFile({
    work_order_id: props.workOrderId,
    file_category: isReplyFlow.value ? 'REVIEW_REPLY' : 'REPORT_ZIP',
    business_stage: reviewStage(reviewRound.value),
    file: file.raw
  })
  ElMessage.success(isReplyFlow.value ? '审核意见回复已上传' : '待审报告已上传')
  await loadFiles()
}

async function onOpinionSelected(file: UploadFile) {
  if (!props.workOrderId || !file.raw) return
  await uploadWorkOrderFile({ work_order_id: props.workOrderId, file_category: 'REVIEW_OPINION', business_stage: reviewStage(reviewRound.value), file: file.raw })
  ElMessage.success('审核意见文件已上传')
  await loadFiles()
}

async function onFormalReportSelected(file: UploadFile) {
  if (!props.workOrderId || !file.raw) return
  if (!canUploadFormalReport.value) return ElMessage.warning('仅三审老师可上传正式报告文件')
  if (!signerOne.value || !signerTwo.value) return ElMessage.warning('请先填写两名签字评估师')
  if (!formalReportCount.value) return ElMessage.warning('请填写报告出具数量')
  await updateWorkOrder(props.workOrderId, {
    signer_one: signerOne.value,
    signer_two: signerTwo.value,
    formal_report_count: formalReportCount.value
  })
  await uploadWorkOrderFile({ work_order_id: props.workOrderId, file_category: 'FORMAL_REPORT', business_stage: 'FORMAL_REPORT', file: file.raw })
  ElMessage.success('正式报告文件已上传')
  await loadFiles()
  emit('changed')
}

async function onFinalContractSelected(file: UploadFile) {
  if (!props.workOrderId || !file.raw) return
  if (!canUploadFormalReport.value) return ElMessage.warning('仅三审老师可上传合同扫描件')
  await uploadWorkOrderFile({ work_order_id: props.workOrderId, file_category: 'FINAL_CONTRACT_SCAN', business_stage: 'FINAL_CONTRACT_SCAN', file: file.raw })
  ElMessage.success('合同扫描件已上传')
  await loadFiles()
  emit('changed')
}

async function onTransferPrintRoom() {
  if (!props.workOrderId) return
  if (!signerOne.value || !signerTwo.value) return ElMessage.warning('请填写两名签字评估师')
  if (!formalReportCount.value) return ElMessage.warning('请填写报告出具数量')
  if (!printRoomHandlerId.value) return ElMessage.warning('请选择文印室人员')
  if (!formalReportFiles.value.length) return ElMessage.warning('请先上传正式报告文件')
  if (!finalContractFiles.value.length) return ElMessage.warning('请先上传合同扫描件后再转发文印室')
  await updateWorkOrder(props.workOrderId, {
    signer_one: signerOne.value,
    signer_two: signerTwo.value,
    formal_report_count: formalReportCount.value
  })
  await transferPrintRoom({ work_order_id: props.workOrderId, handler_user_id: printRoomHandlerId.value })
  ElMessage.success('已转发文印室')
  emit('changed')
}

async function onSubmit() {
  const targetReviewerId = isReplyFlow.value ? currentRoundReviewerId.value : reviewerUserId.value
  if (!props.workOrderId || !targetReviewerId) return ElMessage.warning(isReplyFlow.value ? '当前轮次缺少原审核老师' : '请选择审核老师')
  if (!submitFiles.value.length) return ElMessage.warning(isReplyFlow.value ? '请先上传审核意见回复' : '请先上传待审报告')
  await submitReview({ work_order_id: props.workOrderId, review_round: reviewRound.value, reviewer_user_id: targetReviewerId, comment: comment.value || undefined })
  ElMessage.success(isReplyFlow.value ? '审核意见回复已提交' : '提交审核成功')
  comment.value = ''
  await Promise.all([loadRecords(), loadFiles()])
  emit('changed')
}

async function onDecision(action: 'APPROVE' | 'REJECT_RETURN') {
  if (!props.workOrderId) return
  await decideReview({ work_order_id: props.workOrderId, review_round: reviewRound.value, action, comment: reviewComment.value || undefined })
  ElMessage.success(action === 'APPROVE' ? '审核通过' : '已返回修改')
  reviewComment.value = ''
  await Promise.all([loadRecords(), loadFiles()])
  emit('changed')
}

function download(file: WorkOrderFileItem) {
  window.open(getWorkOrderFileDownloadUrl(file.id), '_blank')
}

function canWithdrawRow(row: ReviewRow) {
  if (!row.recordId || !props.workOrderId || !currentUserId.value) return false
  const latest = records.value[0]
  if (!latest || latest.id !== row.recordId) return false
  if (props.userRoles.includes('ADMIN')) return true
  if (row.action === 'SUBMIT') return isReviewSubmitter.value
  if (row.action === 'APPROVE' || row.action === 'REJECT_RETURN') return row.reviewerUserId === currentUserId.value
  return false
}

async function onWithdraw() {
  if (!props.workOrderId) return
  await withdrawLatestReview(props.workOrderId)
  ElMessage.success('已撤回最新审核操作')
  await Promise.all([loadRecords(), loadFiles()])
  emit('changed')
}

async function reloadPanelData() {
  syncRoundWithStatus()
  signerOne.value = props.flowInfo?.signer_one || signerOne.value
  signerTwo.value = props.flowInfo?.signer_two || signerTwo.value
  formalReportCount.value = props.flowInfo?.formal_report_count || formalReportCount.value
  printRoomHandlerId.value = props.flowInfo?.print_room_handler_id || printRoomHandlerId.value
  await auth.ensureUserLoaded()
  if (showFormalReportPanel.value) {
    printRoomOptions.value = (await listUserCandidates('PRINT_ROOM')).items
  }
  await Promise.all([loadCandidates(), loadRecords(), loadFiles()])
}

onMounted(reloadPanelData)
watch(() => [props.workOrderId, props.flowInfo?.current_work_order_status], reloadPanelData)
</script>

<style scoped>
.file-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-left: 12px;
}

.attachment-list {
  display: grid;
  gap: 4px;
}

.attachment-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  min-width: 0;
}

.attachment-item span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.contract-file-list {
  display: grid;
  gap: 8px;
  width: 100%;
}

.contract-file-item {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.contract-file-item span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
