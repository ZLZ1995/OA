<template>
  <el-alert
    v-if="!workOrderId"
    type="warning"
    :closable="false"
    title="当前项目暂无关联工单，无法办理合同流程。"
    show-icon
    style="margin-bottom: 12px"
  />
  <template v-else>
    <div class="stage-summary-card">
      <div class="stage-summary-grid">
        <div class="stage-summary-item">
          <span>项目名称</span>
          <strong>{{ flowInfo?.project.project_name || '-' }}</strong>
        </div>
        <div class="stage-summary-item">
          <span>客户名称</span>
          <strong>{{ flowInfo?.project.client_name || '-' }}</strong>
        </div>
        <div class="stage-summary-item">
          <span>项目负责人</span>
          <strong>{{ flowInfo?.project.project_leader_display_name || '-' }}</strong>
        </div>
        <div class="stage-summary-item">
          <span>合同流程状态</span>
          <strong>{{ flowInfo?.contract_review_status_display || '-' }}</strong>
        </div>
      </div>
    </div>

    <el-card shadow="never" style="margin-bottom: 16px">
      <template #header>原合同文件</template>
      <el-table :data="contractFiles" v-loading="loading" empty-text="暂无合同文件">
        <el-table-column prop="origin_file_name" label="文件名" min-width="240" />
        <el-table-column prop="uploaded_by_name" label="上传人" min-width="120" />
        <el-table-column prop="uploaded_at" label="上传时间" min-width="190" />
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button type="primary" link @click="download(row)">下载</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card v-if="canReview" shadow="never" style="margin-bottom: 16px">
      <template #header>合同审核处理</template>
      <el-form label-width="120px">
        <el-form-item label="审核意见">
          <el-input v-model="reviewComment" type="textarea" :rows="3" placeholder="请输入审核意见" />
        </el-form-item>
        <el-form-item label="审核附件">
          <el-upload :auto-upload="false" :on-change="onAttachmentSelected" :show-file-list="false">
            <el-button>上传审核附件</el-button>
          </el-upload>
          <div v-if="reviewAttachment" class="inline-file">
            <span>{{ reviewAttachment.origin_file_name }}</span>
            <el-button type="primary" link @click="download(reviewAttachment)">下载</el-button>
          </div>
        </el-form-item>
        <el-form-item label="文印室人员">
          <el-select v-model="printRoomHandlerId" placeholder="请选择文印室人员" style="width: 280px">
            <el-option
              v-for="user in printRoomOptions"
              :key="user.id"
              :label="`${user.real_name}(${user.username})`"
              :value="user.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-space>
            <el-button type="success" @click="onApproveAndTransfer">审核通过并转发文印室</el-button>
            <el-button type="danger" plain @click="onReject">退回修改</el-button>
          </el-space>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card v-if="canTransferApprovedContract" shadow="never" style="margin-bottom: 16px">
      <template #header>转送文印室</template>
      <el-form label-width="120px">
        <el-form-item label="文印室人员">
          <el-select v-model="printRoomHandlerId" placeholder="请选择文印室人员" style="width: 280px">
            <el-option
              v-for="user in printRoomOptions"
              :key="user.id"
              :label="`${user.real_name}(${user.username})`"
              :value="user.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="转送说明">
          <el-input v-model="printRoomRemark" type="textarea" :rows="2" placeholder="可选，转送给文印室时附言" />
        </el-form-item>
        <el-form-item>
          <el-button type="success" @click="onTransferApprovedContract">转送文印室</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card v-if="showPrintRoomSection" shadow="never" style="margin-bottom: 16px">
      <template #header>文印室处理</template>
      <div class="contract-stage-layout">
        <div class="contract-stage-main">
          <el-descriptions :column="2" border style="margin-bottom: 16px">
            <el-descriptions-item label="当前文印室人员">{{ flowInfo?.project.print_room_handler_name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="项目负责人">{{ flowInfo?.project.project_leader_display_name || '-' }}</el-descriptions-item>
          </el-descriptions>
          <el-form label-width="140px">
            <el-form-item label="上传盖章扫描件" v-if="canPrintRoomProcess">
              <el-upload :auto-upload="false" :on-change="onStampedScanSelected" :show-file-list="false">
                <el-button type="primary">上传盖章扫描件</el-button>
              </el-upload>
            </el-form-item>
            <el-form-item label="发送说明" v-if="canPrintRoomProcess">
              <el-input v-model="printRoomRemark" type="textarea" :rows="2" placeholder="可选，发送给项目负责人时附言" />
            </el-form-item>
            <el-form-item v-if="canPrintRoomProcess">
              <el-button type="success" :disabled="stampedFiles.length === 0" @click="onSendToProjectLeader">发送给项目负责人</el-button>
            </el-form-item>
          </el-form>
          <el-table :data="stampedFiles" empty-text="暂无盖章扫描件">
            <el-table-column prop="origin_file_name" label="文件名" min-width="240" />
            <el-table-column prop="uploaded_by_name" label="上传人" min-width="120" />
            <el-table-column prop="uploaded_at" label="上传时间" min-width="190" />
            <el-table-column label="操作" width="120">
              <template #default="{ row }">
                <el-button type="primary" link @click="download(row)">下载</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
        <aside class="contract-stage-side">
          <div class="stage-note-card">
            <div class="stage-note-title">当前环节所需文件要求</div>
            <ol class="stage-note-list">
              <li>上传已盖章合同扫描件。</li>
              <li>确认文件清晰、页数完整、顺序正确。</li>
              <li>发送前核对接收人为当前项目负责人。</li>
            </ol>
            <p class="stage-note-emphasis">本环节只处理合同盖章扫描件，不承载报告送审材料要求。</p>
          </div>
        </aside>
      </div>
    </el-card>

    <el-card v-if="showLeaderConfirmSection" shadow="never" style="margin-bottom: 16px">
      <template #header>项目负责人确认</template>
      <div class="contract-stage-layout">
        <div class="contract-stage-main">
          <el-alert
            type="info"
            :closable="false"
            show-icon
            title="文印室已上传盖章扫描件，请确认是否无误。"
            style="margin-bottom: 16px"
          />
          <el-table :data="stampedFiles" empty-text="暂无盖章扫描件" style="margin-bottom: 16px">
            <el-table-column prop="origin_file_name" label="文件名" min-width="240" />
            <el-table-column prop="uploaded_by_name" label="上传人" min-width="120" />
            <el-table-column prop="uploaded_at" label="上传时间" min-width="190" />
            <el-table-column label="操作" width="120">
              <template #default="{ row }">
                <el-button type="primary" link @click="download(row)">下载</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-form label-width="120px">
            <el-form-item label="退回原因">
              <el-input v-model="leaderRemark" type="textarea" :rows="2" placeholder="退回文印室时请填写原因" />
            </el-form-item>
            <el-form-item v-if="canProjectLeaderConfirm">
              <el-space>
                <el-button type="danger" plain @click="onReturnToPrintRoom">退回文印室</el-button>
                <el-button type="success" @click="onConfirmComplete">确认办结</el-button>
              </el-space>
            </el-form-item>
            <el-form-item v-else-if="canReopenContractReview">
              <el-button type="warning" plain @click="onReopenContractReview">报告重新审核</el-button>
            </el-form-item>
          </el-form>
        </div>
        <aside class="contract-stage-side">
          <div class="stage-note-card">
            <div class="stage-note-title">确认说明</div>
            <ol class="stage-note-list">
              <li>核对扫描件是否完整清晰。</li>
              <li>核对页数、盖章位置与原合同是否一致。</li>
              <li>如有问题，退回文印室重新上传。</li>
            </ol>
            <p class="stage-note-emphasis">本页不展示“待审文件要求”，仅保留负责人的确认说明。</p>
          </div>
        </aside>
      </div>
    </el-card>

    <el-divider>合同流程记录</el-divider>
    <el-table :data="records">
      <el-table-column prop="actionLabel" label="动作" width="180" />
      <el-table-column prop="operator_user_name" label="操作人" width="120" />
      <el-table-column prop="reviewer_user_name" label="审核人" width="120" />
      <el-table-column prop="comment" label="意见" min-width="220" show-overflow-tooltip />
      <el-table-column label="合同文件" min-width="220">
        <template #default="{ row }">
          <template v-if="row.contract_file">
            <span>{{ row.contract_file.origin_file_name }}</span>
            <el-button type="primary" link @click="download(row.contract_file)">下载</el-button>
          </template>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column label="审核附件" min-width="220">
        <template #default="{ row }">
          <template v-if="row.review_attachment_file">
            <span>{{ row.review_attachment_file.origin_file_name }}</span>
            <el-button type="primary" link @click="download(row.review_attachment_file)">下载</el-button>
          </template>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="时间" min-width="180" />
    </el-table>
  </template>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox, type UploadFile } from 'element-plus'
import type { ProjectFlowData } from '@/api/projectFlow'
import type { WorkOrderFileItem } from '@/api/files'
import { downloadWorkOrderFile, listWorkOrderFiles, uploadWorkOrderFile } from '@/api/files'
import {
  approveAndTransferContractReview,
  rejectContractReview,
  listContractReviewRecords,
  transferApprovedContractToPrintRoom,
  type ContractReviewRecordItem
} from '@/api/contractReviews'
import { confirmContractComplete, reopenContractReview, returnContractToPrintRoom, sendContractToProjectLeader } from '@/api/printRoom'
import { listUserCandidates, type UserItem } from '@/api/users'
import { useAuthStore } from '@/store/auth'

const props = defineProps<{
  projectId?: number
  workOrderId?: number
  flowInfo?: ProjectFlowData
  userRoles?: string[]
  canEdit?: boolean
  canOperate?: boolean
  userRoleInProject?: string
}>()
const emit = defineEmits<{
  (e: 'changed'): void
  (e: 'navigate', key: string): void
}>()
const auth = useAuthStore()

const loading = ref(false)
const records = ref<(ContractReviewRecordItem & { actionLabel: string })[]>([])
const contractFiles = ref<WorkOrderFileItem[]>([])
const stampedFiles = ref<WorkOrderFileItem[]>([])
const reviewAttachment = ref<WorkOrderFileItem | null>(null)
const reviewComment = ref('')
const leaderRemark = ref('')
const printRoomRemark = ref('')
const printRoomHandlerId = ref<number>()
const printRoomOptions = ref<UserItem[]>([])

const currentSubmitRecord = computed(() => records.value.find(item => item.action_type === 'SUBMIT_CONTRACT'))
const currentUserId = computed(() => auth.user?.id)
const isAdmin = computed(() => Boolean(props.userRoles?.includes('ADMIN')))
const contractPrintRoomStatus = computed(() => props.flowInfo?.contract_print_room_status || props.flowInfo?.current_work_order_status || '')

const canReview = computed(() => Boolean(
  currentUserId.value &&
  props.flowInfo?.current_work_order_status === 'CONTRACT_REVIEWING' &&
  props.flowInfo?.contract_reviewer_id === currentUserId.value &&
  props.userRoles?.some(role => ['CONTRACT_REVIEWER', 'ADMIN'].includes(role))
))

const canPrintRoomProcess = computed(() => Boolean(
  contractPrintRoomStatus.value === 'WAIT_PRINT_ROOM_PROCESS' &&
  (props.flowInfo?.print_room_handler_id === currentUserId.value || isAdmin.value)
))

const canProjectLeaderConfirm = computed(() => Boolean(
  currentUserId.value &&
  contractPrintRoomStatus.value === 'WAIT_PROJECT_LEADER_CONTRACT_CONFIRM' &&
  (
    props.flowInfo?.project.project_leader_id === currentUserId.value ||
    props.flowInfo?.user_role_in_project === '项目负责人' ||
    isAdmin.value
  )
))

const canReopenContractReview = computed(() => Boolean(
  currentUserId.value &&
  contractPrintRoomStatus.value === 'CONTRACT_PROCESS_COMPLETED' &&
  (
    props.flowInfo?.project.project_leader_id === currentUserId.value ||
    props.flowInfo?.user_role_in_project === '项目负责人' ||
    isAdmin.value
  )
))

const canTransferApprovedContract = computed(() => Boolean(
  currentUserId.value &&
  props.flowInfo?.current_work_order_status === 'CONTRACT_APPROVED' &&
  !props.flowInfo?.contract_print_room_status &&
  (
    props.flowInfo?.contract_reviewer_id === currentUserId.value ||
    props.userRoles?.some(role => ['CONTRACT_REVIEWER'].includes(role)) ||
    props.flowInfo?.project.project_leader_id === currentUserId.value ||
    ['项目负责人', '项目组成员', '创建人'].includes(props.flowInfo?.user_role_in_project || '') ||
    isAdmin.value
  )
))

const showPrintRoomSection = computed(() => ['WAIT_PRINT_ROOM_PROCESS'].includes(contractPrintRoomStatus.value))
const showLeaderConfirmSection = computed(() => ['WAIT_PROJECT_LEADER_CONTRACT_CONFIRM', 'CONTRACT_PROCESS_COMPLETED'].includes(contractPrintRoomStatus.value))

function actionLabel(actionType: ContractReviewRecordItem['action_type']) {
  if (actionType === 'SUBMIT_CONTRACT') return '提交审核'
  if (actionType === 'APPROVE_CONTRACT') return '审核通过'
  if (actionType === 'APPROVE_AND_TRANSFER_PRINT_ROOM') return '审核通过并转文印室'
  if (actionType === 'TRANSFER_APPROVED_PRINT_ROOM') return '转送文印室'
  if (actionType === 'REOPEN_CONTRACT_REVIEW') return '报告重新审核'
  return '退回修改'
}

async function load() {
  if (!props.workOrderId) {
    records.value = []
    contractFiles.value = []
    stampedFiles.value = []
    reviewAttachment.value = null
    return
  }
  loading.value = true
  try {
    await auth.ensureUserLoaded()
    const [recordData, fileData, printUsers] = await Promise.all([
      listContractReviewRecords(props.workOrderId),
      listWorkOrderFiles(props.workOrderId),
      listUserCandidates('PRINT_ROOM')
    ])
    records.value = recordData.items.map(item => ({ ...item, actionLabel: actionLabel(item.action_type) }))
    contractFiles.value = fileData.items.filter(file => file.file_category === 'CONTRACT_DRAFT' && file.is_current)
    stampedFiles.value = fileData.items.filter(file => file.file_category === 'STAMPED_CONTRACT_SCAN' && file.business_stage === 'PRINT_ROOM_CONTRACT_SCAN' && file.is_current)
    reviewAttachment.value = fileData.items.filter(file => file.file_category === 'CONTRACT_REVIEW_ATTACHMENT').sort((a, b) => b.id - a.id)[0] || null
    printRoomOptions.value = printUsers.items
    if (!printRoomHandlerId.value && props.flowInfo?.print_room_handler_id) {
      printRoomHandlerId.value = props.flowInfo.print_room_handler_id
    }
  } finally {
    loading.value = false
  }
}

async function onAttachmentSelected(file: UploadFile) {
  if (!props.workOrderId || !file.raw) return
  reviewAttachment.value = await uploadWorkOrderFile({
    work_order_id: props.workOrderId,
    file_category: 'CONTRACT_REVIEW_ATTACHMENT',
    business_stage: 'CONTRACT_REVIEW',
    file: file.raw
  })
  ElMessage.success('审核附件已上传')
}

async function onStampedScanSelected(file: UploadFile) {
  if (!props.workOrderId || !file.raw) return
  await uploadWorkOrderFile({
    work_order_id: props.workOrderId,
    file_category: 'STAMPED_CONTRACT_SCAN',
    business_stage: 'PRINT_ROOM_CONTRACT_SCAN',
    file: file.raw
  })
  ElMessage.success('盖章扫描件已上传')
  await load()
}

async function onApproveAndTransfer() {
  const submitRecord = currentSubmitRecord.value
  if (!submitRecord) return ElMessage.warning('未找到待处理的提交记录')
  if (!printRoomHandlerId.value) return ElMessage.warning('请选择文印室人员')
  await approveAndTransferContractReview(submitRecord.id, {
    comment: reviewComment.value || undefined,
    review_attachment_file_id: reviewAttachment.value?.id,
    print_room_handler_id: printRoomHandlerId.value
  })
  ElMessage.success('已审核通过并转发文印室')
  reviewComment.value = ''
  reviewAttachment.value = null
  emit('changed')
}

async function onReject() {
  const submitRecord = currentSubmitRecord.value
  if (!submitRecord) return ElMessage.warning('未找到待处理的提交记录')
  await rejectContractReview(submitRecord.id, {
    comment: reviewComment.value || undefined,
    review_attachment_file_id: reviewAttachment.value?.id
  })
  ElMessage.success('已退回修改')
  reviewComment.value = ''
  reviewAttachment.value = null
  emit('changed')
}

async function onTransferApprovedContract() {
  if (!props.workOrderId) return
  if (!printRoomHandlerId.value) return ElMessage.warning('请选择文印室人员')
  await transferApprovedContractToPrintRoom(props.workOrderId, {
    comment: printRoomRemark.value || undefined,
    print_room_handler_id: printRoomHandlerId.value
  })
  ElMessage.success('已转送文印室')
  printRoomRemark.value = ''
  emit('changed')
}

async function onSendToProjectLeader() {
  if (!props.workOrderId) return
  if (stampedFiles.value.length === 0) return ElMessage.warning('请先上传盖章扫描件')
  await sendContractToProjectLeader({
    work_order_id: props.workOrderId,
    remark: printRoomRemark.value || undefined
  })
  ElMessage.success('已发送项目负责人确认')
  printRoomRemark.value = ''
  emit('changed')
}

async function onReturnToPrintRoom() {
  if (!props.workOrderId) return
  if (!leaderRemark.value.trim()) return ElMessage.warning('请输入退回原因')
  await returnContractToPrintRoom({
    work_order_id: props.workOrderId,
    remark: leaderRemark.value.trim()
  })
  ElMessage.success('已退回文印室')
  leaderRemark.value = ''
  emit('changed')
}

async function onConfirmComplete() {
  if (!props.workOrderId) return
  await confirmContractComplete({
    work_order_id: props.workOrderId,
    remark: leaderRemark.value.trim() || undefined
  })
  ElMessage.success('合同流程已办结')
  leaderRemark.value = ''
  emit('changed')
}

async function onReopenContractReview() {
  if (!props.workOrderId) return
  try {
    await ElMessageBox.confirm(
      '确认后原合同作废，OA流程将重新进入合同送审环节。是否继续？',
      '报告重新审核',
      {
        type: 'warning',
        confirmButtonText: '确认重新审核',
        cancelButtonText: '取消'
      }
    )
  } catch {
    return
  }
  await reopenContractReview({
    work_order_id: props.workOrderId,
    remark: leaderRemark.value.trim() || undefined
  })
  ElMessage.success('已重新进入合同送审环节')
  leaderRemark.value = ''
  emit('changed')
}

function download(file: Pick<WorkOrderFileItem, 'id' | 'origin_file_name'>) {
  downloadWorkOrderFile(file.id, file.origin_file_name)
}

onMounted(load)
watch(() => [props.workOrderId, props.flowInfo?.current_work_order_status], load)
</script>

<style scoped>
.inline-file {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: 12px;
}

.stage-summary-card {
  margin-bottom: 16px;
  border: 1px solid #d8e5f2;
  border-radius: 10px;
  padding: 14px 16px;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
}

.stage-summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.stage-summary-item {
  min-width: 0;
}

.stage-summary-item span {
  display: block;
  color: #64748b;
  font-size: 12px;
}

.stage-summary-item strong {
  display: block;
  margin-top: 6px;
  color: #153a63;
  font-size: 14px;
  line-height: 1.5;
  word-break: break-word;
}

.contract-stage-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 16px;
  align-items: start;
}

.contract-stage-main {
  min-width: 0;
}

.contract-stage-side {
  min-width: 0;
}

.stage-note-card {
  border: 1px solid #d8e5f2;
  border-radius: 10px;
  padding: 16px;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
}

.stage-note-title {
  color: #0c3157;
  font-size: 15px;
  font-weight: 700;
}

.stage-note-list {
  margin: 12px 0 0;
  padding-left: 20px;
  color: #475569;
  line-height: 1.7;
}

.stage-note-emphasis {
  margin: 12px 0 0;
  color: #d45b2c;
  font-size: 12px;
  line-height: 1.6;
}

@media (max-width: 960px) {
  .stage-summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .contract-stage-layout {
    grid-template-columns: 1fr;
  }
}
</style>
