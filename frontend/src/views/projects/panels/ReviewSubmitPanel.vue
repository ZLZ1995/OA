<template>
  <el-alert
    v-if="!workOrderId"
    type="warning"
    :closable="false"
    title="当前项目暂无关联工单，无法办理报告送审。"
    show-icon
  />
  <template v-else>
    <el-alert
      v-if="flowInfo?.review_submit_locked"
      type="warning"
      :closable="false"
      show-icon
      :title="flowInfo?.review_submit_lock_reason || '报告送审暂不可办理'"
      style="margin-bottom: 12px"
    />
    <el-descriptions
      v-if="showProjectSummary"
      :column="2"
      border
      style="margin-bottom: 16px"
    >
      <el-descriptions-item label="项目名称">{{ flowInfo?.project.project_name || '-' }}</el-descriptions-item>
      <el-descriptions-item label="客户名称">{{ flowInfo?.project.client_name || '-' }}</el-descriptions-item>
      <el-descriptions-item label="报告类型">{{ flowInfo?.project.report_type || '-' }}</el-descriptions-item>
      <el-descriptions-item label="评估基准日">{{ flowInfo?.project.valuation_base_date || '-' }}</el-descriptions-item>
      <el-descriptions-item label="项目来源">{{ flowInfo?.project.project_source_display || '-' }}</el-descriptions-item>
      <el-descriptions-item label="项目负责人">{{ flowInfo?.project.project_leader_display_name || '-' }}</el-descriptions-item>
      <el-descriptions-item label="项目承接业务员">{{ flowInfo?.project.business_salesman || '-' }}</el-descriptions-item>
      <el-descriptions-item label="承接单位">{{ flowInfo?.project.undertaking_unit || '-' }}</el-descriptions-item>
    </el-descriptions>

    <el-form label-width="120px">
      <el-form-item label="审核轮次">
        <el-select v-model="reviewRound" style="width: 180px" :disabled="!canSubmitReview || isReviewLocked" @change="reloadRoundData">
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
      <template v-if="showReviewerChangePanel">
        <el-form-item label="变更审核老师">
          <el-select v-model="changeReviewerUserId" placeholder="选择新的审核老师" style="width: 320px" :disabled="hasChangedReviewer">
            <el-option v-for="u in userOptions" :key="u.user_id" :label="`${u.real_name}(${u.username})`" :value="u.user_id" />
          </el-select>
        </el-form-item>
        <el-form-item label="变更备注">
          <el-input v-model="changeReviewerComment" type="textarea" :rows="2" :disabled="hasChangedReviewer" placeholder="选填" />
        </el-form-item>
        <el-alert
          v-if="pendingReviewerChange"
          type="info"
          :closable="false"
          show-icon
          title="审核人变更已保存，提交并更换审核人后正式流转给新审核人。"
          style="margin-bottom: 12px"
        />
        <el-form-item label="报告文件处理">
          <el-radio-group v-model="replyFileMode" :disabled="!canSubmitReview">
            <el-radio-button label="REUPLOAD">重新上传文件</el-radio-button>
            <el-radio-button label="REUSE">沿用上轮文件</el-radio-button>
          </el-radio-group>
        </el-form-item>
      </template>

      <el-form-item v-if="showContractDraftDownload" label="合同初稿下载">
        <div v-if="contractDraftFiles.length" class="contract-file-list">
          <div v-for="file in contractDraftFiles" :key="file.id" class="contract-file-item">
            <span>{{ file.origin_file_name }}（{{ formatFileSize(file.file_size) }}）</span>
            <el-button type="primary" plain @click="download(file)">下载合同初稿</el-button>
          </div>
        </div>
        <span v-else>-</span>
      </el-form-item>

      <el-form-item label="文件传输区">
        <div class="review-upload-block">
          <div class="review-upload-main">
            <section class="file-zone-card file-zone-card--primary">
              <div class="file-zone-header">
                <div>
                  <div class="file-zone-title">待审报告资料包</div>
                  <div class="file-zone-subtitle">评估报告、计算表、测算依据等本轮送审材料集中在这里维护。</div>
                </div>
                <el-upload v-if="canEditReportPackage" :auto-upload="false" :on-change="onReportSelected" :show-file-list="false">
                  <el-button type="primary" plain>{{ isReplyFlow ? '上传修改后报告包' : '上传待审报告包' }}</el-button>
                </el-upload>
              </div>
              <div class="review-upload-actions">
                <el-tag v-if="reusePreviousFile" type="info" effect="plain">将沿用上轮已提交文件</el-tag>
                <el-tag v-else-if="canCarryForwardApprovedFile" type="warning" effect="plain">沿用上一轮审核通过文件</el-tag>
                <el-tag v-else-if="isLockedCarryForwardStage" type="warning" effect="plain">沿用上一轮审核通过文件</el-tag>
                <el-tag v-else-if="isReportUploadLocked" type="warning" effect="plain">待审材料已锁定，不能删除或替换</el-tag>
              </div>
              <div class="file-row-list" v-if="currentReportPackageFiles.length">
                <div v-for="file in currentReportPackageFiles" :key="file.id" class="file-row">
                  <div class="file-row-main">
                    <span class="file-name">{{ file.origin_file_name }}</span>
                    <span class="file-meta">当前版本 · {{ formatFileSize(file.file_size) }}</span>
                  </div>
                  <el-space>
                    <el-button type="primary" link @click="download(file)">下载</el-button>
                    <el-button v-if="canDeleteReportPackageFile(file)" type="danger" link @click="onDeleteFile(file)">删除</el-button>
                  </el-space>
                </div>
              </div>
              <el-empty v-else description="暂无待审报告资料包" :image-size="48" />
            </section>

            <section class="file-zone-card file-zone-card--review">
              <div class="file-zone-header">
                <div>
                  <div class="file-zone-title">审核意见 / 回复</div>
                  <div class="file-zone-subtitle">审核老师上传意见，项目负责人上传回复，和待审报告资料包互不覆盖。</div>
                </div>
                <el-upload v-if="canUploadReplyFile" :auto-upload="false" :on-change="onReplySelected" :show-file-list="false">
                  <el-button plain>上传审核意见回复</el-button>
                </el-upload>
              </div>
              <el-alert
                v-if="isReplyFlow"
                type="warning"
                :closable="false"
                title="退回修改后重新送审时，审核意见回复文件或送审备注至少填写一项。"
                show-icon
              />
              <div class="file-row-list" v-if="reviewCommunicationFiles.length">
                <div v-for="file in reviewCommunicationFiles" :key="file.id" class="file-row">
                  <div class="file-row-main">
                    <span class="file-name">{{ file.origin_file_name }}</span>
                    <span class="file-meta">{{ reviewFileTypeLabel(file) }} · {{ roundLabel(roundFromStage(file.business_stage) || reviewRound) }} · {{ formatFileSize(file.file_size) }}</span>
                  </div>
                  <el-space>
                    <el-button type="primary" link @click="download(file)">下载</el-button>
                    <el-button v-if="canDeleteReplyFile(file)" type="danger" link @click="onDeleteFile(file)">删除</el-button>
                  </el-space>
                </div>
              </div>
              <el-empty v-else description="暂无审核意见或回复文件" :image-size="48" />
            </section>
          </div>
          <ReviewUploadRequirementBox v-if="showReviewRequirementBox" />
        </div>
      </el-form-item>
      <el-form-item label="送审备注" v-if="canSubmitReview && !showReviewerChangePanel">
        <el-input v-model="comment" type="textarea" :rows="3" />
      </el-form-item>
      <el-form-item>
        <el-space wrap>
          <el-button v-if="!showReviewerChangePanel" type="primary" :disabled="!canSubmitReview || requiresManualUploadBeforeSubmit" @click="onSubmit">
            {{ isReplyFlow ? '提交审核意见回复' : '提交审核' }}
          </el-button>
          <el-button v-if="canRecallRouting" type="danger" plain @click="onRecallRouting">
            撤回转交
          </el-button>
          <el-button v-if="canChangeReviewer && !showReviewerChangePanel" type="warning" plain @click="openReviewerChangePanel">
            更换审核人
          </el-button>
          <template v-if="showReviewerChangePanel">
            <el-button type="warning" :disabled="!canSubmitReviewerChange" @click="onSubmitWithReviewerChange">
              提交并更换审核人
            </el-button>
            <el-button plain @click="cancelReviewerChangePanel">取消更换</el-button>
          </template>
          <el-tag :type="statusTagType" effect="plain">{{ reviewStatusText }}</el-tag>
        </el-space>
      </el-form-item>
    </el-form>

    <template v-if="canReview">
      <el-divider>审核处理</el-divider>
      <el-form label-width="120px">
        <el-form-item
          v-if="records.find(item => item.review_round === reviewRound && item.action === 'SUBMIT' && item.source_round_comment)"
          label="上一轮审核意见"
        >
          <div class="previous-review-card">
            <div class="previous-review-meta">
              {{ records.find(item => item.review_round === reviewRound && item.action === 'SUBMIT')?.source_round_reviewer_name || '上一轮审核人' }}
            </div>
            <div>
              {{ records.find(item => item.review_round === reviewRound && item.action === 'SUBMIT')?.source_round_comment }}
            </div>
            <div v-if="previousOpinionReferenceFiles.length" class="previous-review-files">
              <div v-for="file in previousOpinionReferenceFiles" :key="file.id" class="attachment-item">
                <span>{{ file.origin_file_name }}（{{ formatFileSize(file.file_size) }}）</span>
                <el-button type="primary" link @click="download(file)">下载</el-button>
              </div>
            </div>
          </div>
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

    <el-dialog v-model="routingDialogVisible" :title="`转交${routingNextRoundLabel}`" width="520px" destroy-on-close>
      <div class="routing-dialog-body">
        <el-alert
          type="info"
          :closable="false"
          show-icon
          title="直接转交不会上传新文件，将沿用本轮审核通过的待审报告资料包。"
        />
        <el-form label-width="120px">
          <el-form-item :label="`${routingNextRoundLabel}老师`" required>
            <el-select v-model="routingReviewerUserId" placeholder="选择下一级审核老师" style="width: 100%" filterable>
              <el-option v-for="u in routingUserOptions" :key="u.user_id" :label="`${u.real_name}(${u.username})`" :value="u.user_id" />
            </el-select>
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="routingDialogVisible = false">稍后处理</el-button>
        <el-button :loading="routingSubmitting" @click="routeApprovedToLeader">退回项目负责人选择</el-button>
        <el-button type="primary" :disabled="!routingReviewerUserId" :loading="routingSubmitting" @click="routeApprovedToReviewer">直接转交</el-button>
      </template>
    </el-dialog>

    <template v-if="canRequestOwnerExternalAuditConfirm">
      <el-divider>外部审核确认</el-divider>
      <el-alert
        type="info"
        :closable="false"
        title="本流程将流转至项目负责人处，请等待项目负责人反馈。"
        show-icon
        style="margin-bottom: 12px"
      />
      <el-button type="primary" @click="onRequestOwnerExternalAuditConfirm">向项目负责人发送确认信息</el-button>
    </template>

    <template v-if="canOwnerChooseExternalAudit">
      <el-divider>项目负责人确认</el-divider>
      <el-alert
        type="warning"
        :closable="false"
        title="请确认该项目是否涉及外部审核。"
        show-icon
        style="margin-bottom: 12px"
      />
      <el-space wrap>
        <el-button type="success" @click="onMarkNoExternalAudit">不涉及外部审核</el-button>
        <el-button type="primary" plain @click="onMarkHasExternalAudit">涉及外部审核</el-button>
      </el-space>
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
import { ElMessage, ElMessageBox, type UploadFile } from 'element-plus'
import { changeReviewAssignee, decideReview, listReviewCandidates, listReviews, recallRoutedReview, routeApprovedReview, submitReview, withdrawLatestReview, type ReviewCandidateItem, type ReviewRecordItem } from '@/api/reviews'
import { deleteWorkOrderFile, downloadWorkOrderFile, listWorkOrderFiles, uploadWorkOrderFile, type WorkOrderFileItem } from '@/api/files'
import { useAuthStore } from '@/store/auth'
import type { ProjectFlowData } from '@/api/projectFlow'
import { updateWorkOrder } from '@/api/workorders'
import { transferPrintRoom } from '@/api/printRoom'
import { listUserCandidates, type UserItem } from '@/api/users'
import { markHasExternalAudit, markNoExternalAudit, requestOwnerExternalAuditConfirm } from '@/api/signoff'
import ReviewUploadRequirementBox from '@/components/common/ReviewUploadRequirementBox.vue'

const props = defineProps<{ workOrderId?: number; canEdit: boolean; userRoles: string[]; flowInfo?: ProjectFlowData }>()
const emit = defineEmits<{ (e: 'changed'): void }>()

type ReviewRound = 'FIRST' | 'SECOND' | 'THIRD' | 'EXTERNAL_FIRST' | 'EXTERNAL_SECOND' | 'EXTERNAL_THIRD'

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
  sourceRoundComment?: string
  sourceRoundReviewerName?: string
  autoCarriedFromPrevious?: boolean
  transferredToNext?: boolean
  transferredToRound?: ReviewRound
}

const auth = useAuthStore()
const reviewRound = ref<ReviewRound>('FIRST')
const reviewerUserId = ref<number>()
const changeReviewerUserId = ref<number>()
const replyFileMode = ref<'REUPLOAD' | 'REUSE'>('REUPLOAD')
const isReviewerChangePanelOpen = ref(false)
const comment = ref('')
const changeReviewerComment = ref('')
const reviewComment = ref('')
const signerOne = ref('')
const signerTwo = ref('')
const formalReportCount = ref(1)
const printRoomHandlerId = ref<number>()
const printRoomOptions = ref<UserItem[]>([])
const records = ref<ReviewRecordItem[]>([])
const files = ref<WorkOrderFileItem[]>([])
const userOptions = ref<ReviewCandidateItem[]>([])
const routingUserOptions = ref<ReviewCandidateItem[]>([])
const routingDialogVisible = ref(false)
const routingRound = ref<'FIRST' | 'SECOND' | 'EXTERNAL_FIRST' | 'EXTERNAL_SECOND'>('FIRST')
const routingReviewerUserId = ref<number>()
const routingSubmitting = ref(false)
const loading = ref(false)

const statusCode = computed(() => props.flowInfo?.current_work_order_status || '')
const isStateOwnedAsset = computed(() => props.flowInfo?.project.evaluation_business_nature === '国有资产评估业务')
const currentUserId = computed(() => auth.user?.id)
const isCurrentHandler = computed(() => Boolean(currentUserId.value && props.flowInfo?.current_handler_user_id === currentUserId.value))
const isReviewSubmitter = computed(() => {
  const roleName = props.flowInfo?.user_role_in_project
  return roleName === '项目负责人' || roleName === '项目组成员' || roleName === '创建人' || isCurrentHandler.value
})
const isReplyFlow = computed(() => ['FIRST_REVIEW_REJECTED', 'SECOND_REVIEW_REJECTED', 'THIRD_REVIEW_REJECTED'].includes(statusCode.value))
const isLockedCarryForwardStage = computed(() => ['WAIT_SECOND_REVIEW_SUBMIT', 'WAIT_THIRD_REVIEW_SUBMIT', 'WAIT_EXTERNAL_SECOND_REVIEW_SUBMIT', 'WAIT_EXTERNAL_THIRD_REVIEW_SUBMIT'].includes(statusCode.value))
const isReviewerSelectNextStage = computed(() => ['FIRST_APPROVED_WAIT_FIRST_SELECT_SECOND', 'SECOND_APPROVED_WAIT_SECOND_SELECT_THIRD', 'EXTERNAL_FIRST_APPROVED_WAIT_RECALL_OR_SECOND', 'EXTERNAL_SECOND_APPROVED_WAIT_RECALL_OR_THIRD'].includes(statusCode.value))
const isLeaderSelectNextStage = computed(() => ['FIRST_APPROVED_WAIT_LEADER_SUBMIT_SECOND', 'SECOND_APPROVED_WAIT_LEADER_SUBMIT_THIRD', 'WAIT_EXTERNAL_SECOND_REVIEW_SUBMIT', 'WAIT_EXTERNAL_THIRD_REVIEW_SUBMIT'].includes(statusCode.value))
const isLeaderSubmitNextStage = computed(() => isLeaderSelectNextStage.value && isCurrentHandler.value)
const isReportUploadLocked = computed(() => reusePreviousFile.value || isLockedCarryForwardStage.value || canCarryForwardApprovedFile.value || isLeaderSelectNextStage.value || isReviewerSelectNextStage.value)
const canEditReportPackage = computed(() => canSubmitReview.value && !isReportUploadLocked.value && !showReviewerChangePanel.value)
const canUploadReplyFile = computed(() => canSubmitReview.value && isReplyFlow.value && !showReviewerChangePanel.value)
const canRecallRouting = computed(() => {
  if (!currentUserId.value) return false
  if (reviewRound.value === 'SECOND') return statusCode.value === 'SECOND_REVIEWING' && props.flowInfo?.first_reviewer_id === currentUserId.value
  if (reviewRound.value === 'THIRD') return statusCode.value === 'THIRD_REVIEWING' && props.flowInfo?.second_reviewer_id === currentUserId.value
  if (reviewRound.value === 'EXTERNAL_SECOND') return statusCode.value === 'EXTERNAL_SECOND_REVIEWING' && props.flowInfo?.first_reviewer_id === currentUserId.value
  if (reviewRound.value === 'EXTERNAL_THIRD') return statusCode.value === 'EXTERNAL_THIRD_REVIEWING' && props.flowInfo?.second_reviewer_id === currentUserId.value
  return false
})
const latestSubmitAt = computed(() => {
  const latest = records.value
    .filter(record => record.review_round === reviewRound.value && record.action === 'SUBMIT')
    .sort((a, b) => new Date(b.acted_at).getTime() - new Date(a.acted_at).getTime())[0]
  return latest ? new Date(latest.acted_at).getTime() : 0
})
const pendingReviewerChange = computed(() => records.value
  .filter(record => record.review_round === reviewRound.value && record.action === 'CHANGE_REVIEWER')
  .filter(record => new Date(record.acted_at).getTime() > latestSubmitAt.value)
  .sort((a, b) => new Date(b.acted_at).getTime() - new Date(a.acted_at).getTime())[0])
const hasChangedReviewer = computed(() => Boolean(pendingReviewerChange.value))
const isReviewLocked = computed(() => Boolean(props.flowInfo?.review_submit_locked))
const canChangeReviewer = computed(() => canSubmitReview.value && isReplyFlow.value && !isReviewLocked.value)
const reusePreviousFile = computed(() => isReplyFlow.value && replyFileMode.value === 'REUSE')
const canCarryForwardApprovedFile = computed(() => (isLeaderSelectNextStage.value || isReviewerSelectNextStage.value) && !isReplyFlow.value)
const showReviewerChangePanel = computed(() => canChangeReviewer.value && isReviewerChangePanelOpen.value)
const requiresManualUploadBeforeSubmit = computed(() =>
  !reusePreviousFile.value &&
  !canCarryForwardApprovedFile.value &&
  submitFiles.value.length === 0
)
const canSubmitReviewerChange = computed(() =>
  canSubmitReview.value &&
  Boolean(changeReviewerUserId.value || pendingReviewerChange.value?.reviewer_user_id) &&
  (reusePreviousFile.value || submitFiles.value.length > 0)
)
const currentRoundReviewerId = computed(() => {
  if (reviewRound.value === 'FIRST') return props.flowInfo?.first_reviewer_id
  if (reviewRound.value === 'SECOND') return props.flowInfo?.second_reviewer_id
  if (reviewRound.value === 'EXTERNAL_FIRST') return props.flowInfo?.first_reviewer_id
  if (reviewRound.value === 'EXTERNAL_SECOND') return props.flowInfo?.second_reviewer_id
  return props.flowInfo?.third_reviewer_id
})
const canSubmitReview = computed(() => props.canEdit && !isReviewLocked.value && isReviewSubmitter.value && (isSubmitStatus(statusCode.value) || isLeaderSubmitNextStage.value || isReviewerSelectNextStage.value))
const canReviewerSelectNext = computed(() =>
  props.canEdit &&
  !isReviewLocked.value &&
  isReviewerSelectNextStage.value &&
  Boolean(currentUserId.value && props.flowInfo?.current_handler_user_id === currentUserId.value) &&
  (
    (statusCode.value === 'FIRST_APPROVED_WAIT_FIRST_SELECT_SECOND' && props.userRoles.includes('FIRST_REVIEWER')) ||
    (statusCode.value === 'SECOND_APPROVED_WAIT_SECOND_SELECT_THIRD' && props.userRoles.includes('SECOND_REVIEWER')) ||
    props.userRoles.includes('ADMIN')
  )
)
const canReview = computed(() => {
  if (!currentUserId.value || props.flowInfo?.current_handler_user_id !== currentUserId.value) return false
  if (props.userRoles.includes('ADMIN')) return true
  return (
    (reviewRound.value === 'FIRST' && props.userRoles.includes('FIRST_REVIEWER') && statusCode.value === 'FIRST_REVIEWING') ||
    (reviewRound.value === 'SECOND' && props.userRoles.includes('SECOND_REVIEWER') && statusCode.value === 'SECOND_REVIEWING') ||
    (reviewRound.value === 'THIRD' && props.userRoles.includes('THIRD_REVIEWER') && statusCode.value === 'THIRD_REVIEWING') ||
    (reviewRound.value === 'EXTERNAL_FIRST' && props.userRoles.includes('FIRST_REVIEWER') && statusCode.value === 'EXTERNAL_FIRST_REVIEWING') ||
    (reviewRound.value === 'EXTERNAL_SECOND' && props.userRoles.includes('SECOND_REVIEWER') && statusCode.value === 'EXTERNAL_SECOND_REVIEWING') ||
    (reviewRound.value === 'EXTERNAL_THIRD' && props.userRoles.includes('THIRD_REVIEWER') && statusCode.value === 'EXTERNAL_THIRD_REVIEWING')
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
const canRequestOwnerExternalAuditConfirm = computed(() =>
  statusCode.value === 'THIRD_APPROVED_WAIT_OWNER_CONFIRM_SEND' &&
  Boolean(currentUserId.value && currentUserId.value === props.flowInfo?.third_reviewer_id) &&
  (props.userRoles.includes('THIRD_REVIEWER') || props.userRoles.includes('ADMIN'))
)
const canOwnerChooseExternalAudit = computed(() =>
  statusCode.value === 'WAIT_OWNER_EXTERNAL_AUDIT_CONFIRM' &&
  isReviewSubmitter.value
)
const showContractDraftDownload = computed(() => ['FIRST_REVIEWER', 'SECOND_REVIEWER', 'THIRD_REVIEWER'].some(role => props.userRoles.includes(role)))
const showProjectSummary = computed(() => ['FIRST_REVIEWER', 'SECOND_REVIEWER', 'THIRD_REVIEWER', 'ADMIN'].some(role => props.userRoles.includes(role)))

const reviewPackageFiles = computed(() => files.value.filter(file => file.file_category === 'REPORT_ZIP' && file.business_stage === reviewStage(reviewRound.value)))
const currentReportPackageFiles = computed(() => reviewPackageFiles.value.filter(file => file.is_current))
const replyFiles = computed(() => files.value.filter(file => file.file_category === 'REVIEW_REPLY' && file.business_stage === reviewStage(reviewRound.value)))
const currentReplyFiles = computed(() => replyFiles.value.filter(file => file.is_current))
const submitFiles = computed(() => currentReportPackageFiles.value)
const previousOpinionReferenceFiles = computed(() => files.value.filter(file => file.file_category === 'REVIEW_OPINION' && file.business_stage === reviewStage(reviewRound.value)))
const opinionFiles = computed(() => files.value.filter(file => file.file_category === 'REVIEW_OPINION' && file.business_stage === reviewStage(reviewRound.value)))
const reviewCommunicationFiles = computed(() => files.value
  .filter(file => ['REVIEW_OPINION', 'REVIEW_REPLY'].includes(file.file_category) && file.business_stage.startsWith('REVIEW_') && file.is_current)
  .sort((a, b) => new Date(b.uploaded_at).getTime() - new Date(a.uploaded_at).getTime())
)
const formalReportFiles = computed(() => files.value.filter(file => file.file_category === 'FORMAL_REPORT' && file.business_stage === 'FORMAL_REPORT'))
const contractDraftFiles = computed(() => files.value.filter(file => file.file_category === 'CONTRACT_DRAFT' && file.business_stage === 'CONTRACT_DRAFT' && file.is_current))
const finalContractFiles = computed(() => files.value.filter(file => file.file_category === 'FINAL_CONTRACT_SCAN' && file.business_stage === 'FINAL_CONTRACT_SCAN' && file.is_current))
const showReviewRequirementBox = computed(() => !isReplyFlow.value && !showReviewerChangePanel.value)
const routingNextRound = computed<ReviewRound>(() => {
  if (routingRound.value === 'FIRST') return 'SECOND'
  if (routingRound.value === 'SECOND') return 'THIRD'
  if (routingRound.value === 'EXTERNAL_FIRST') return 'EXTERNAL_SECOND'
  return 'EXTERNAL_THIRD'
})
const routingNextRoundLabel = computed(() => roundLabel(routingNextRound.value))
const reviewerSelectSourceRound = computed<'FIRST' | 'SECOND' | 'EXTERNAL_FIRST' | 'EXTERNAL_SECOND' | undefined>(() => {
  if (statusCode.value === 'FIRST_APPROVED_WAIT_FIRST_SELECT_SECOND') return 'FIRST'
  if (statusCode.value === 'SECOND_APPROVED_WAIT_SECOND_SELECT_THIRD') return 'SECOND'
  if (statusCode.value === 'EXTERNAL_FIRST_APPROVED_WAIT_RECALL_OR_SECOND') return 'EXTERNAL_FIRST'
  if (statusCode.value === 'EXTERNAL_SECOND_APPROVED_WAIT_RECALL_OR_THIRD') return 'EXTERNAL_SECOND'
  return undefined
})
const projectPartyIds = computed(() => {
  const ids = new Set<number>()
  if (props.flowInfo?.project?.project_leader_id) ids.add(props.flowInfo.project.project_leader_id)
  return ids
})

const reviewStatusText = computed(() => {
  if (isReplyFlow.value) return `${roundLabel(reviewRound.value)}意见已返回等待回复`
  if (canCarryForwardApprovedFile.value) return '待提交审核'
  if (isSubmitStatus(statusCode.value)) {
    return currentReportPackageFiles.value.length ? '待提交审核' : '待上传文件'
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
    files: filesForRecord(record),
    sourceRoundComment: record.source_round_comment || undefined,
    sourceRoundReviewerName: record.source_round_reviewer_name || undefined,
    autoCarriedFromPrevious: Boolean(record.auto_carried_from_previous),
    transferredToNext: Boolean(record.transferred_to_next),
    transferredToRound: record.transferred_to_round || undefined
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
  FIRST_APPROVED_WAIT_LEADER_SUBMIT_SECOND: '一审已通过，待一审老师决定二审流向',
  WAIT_SECOND_REVIEW_SUBMIT: '已确定二审老师，待提交二审',
  SECOND_REVIEWING: '二审审核中',
  SECOND_REVIEW_REJECTED: '二审意见已返回等待回复',
  SECOND_APPROVED_WAIT_LEADER_SUBMIT_THIRD: '二审已通过，待二审老师决定三审流向',
  WAIT_THIRD_REVIEW_SUBMIT: '已确定三审老师，待提交三审',
  THIRD_REVIEWING: '三审审核中',
  THIRD_REVIEW_REJECTED: '三审意见已返回等待回复',
  THIRD_APPROVED_WAIT_PRINTROOM: '三审已通过，待补充正式报告与合同扫描件'
}

function isSubmitStatus(status: string) {
  return ['CONTRACT_APPROVED', 'WAIT_FIRST_REVIEW_SUBMIT', 'FIRST_REVIEW_REJECTED', 'FIRST_APPROVED_WAIT_LEADER_SUBMIT_SECOND', 'FIRST_APPROVED_WAIT_FIRST_SELECT_SECOND', 'WAIT_SECOND_REVIEW_SUBMIT', 'SECOND_REVIEW_REJECTED', 'SECOND_APPROVED_WAIT_LEADER_SUBMIT_THIRD', 'SECOND_APPROVED_WAIT_SECOND_SELECT_THIRD', 'WAIT_THIRD_REVIEW_SUBMIT', 'THIRD_REVIEW_REJECTED'].includes(status)
}

function syncRoundWithStatus() {
  const status = statusCode.value
  if (status.includes('EXTERNAL_THIRD')) reviewRound.value = 'EXTERNAL_THIRD'
  else if (status.includes('EXTERNAL_SECOND')) reviewRound.value = 'EXTERNAL_SECOND'
  else if (status.includes('EXTERNAL_FIRST')) reviewRound.value = 'EXTERNAL_FIRST'
  else if (status.includes('SECOND')) reviewRound.value = 'SECOND'
  else if (status.includes('THIRD')) reviewRound.value = 'THIRD'
  else reviewRound.value = 'FIRST'
}

function reviewStage(round: ReviewRound) {
  return `REVIEW_${round}`
}

function roundLabel(round: ReviewRound) {
  return ({
    FIRST: '一审',
    SECOND: '二审',
    THIRD: '三审',
    EXTERNAL_FIRST: '外部一级复核',
    EXTERNAL_SECOND: '外部二级复核',
    EXTERNAL_THIRD: '外部三级复核',
  } as const)[round]
}

function roundFromStage(stage: string): ReviewRound | undefined {
  if (stage === 'REVIEW_FIRST') return 'FIRST'
  if (stage === 'REVIEW_SECOND') return 'SECOND'
  if (stage === 'REVIEW_THIRD') return 'THIRD'
  if (stage === 'REVIEW_EXTERNAL_FIRST') return 'EXTERNAL_FIRST'
  if (stage === 'REVIEW_EXTERNAL_SECOND') return 'EXTERNAL_SECOND'
  if (stage === 'REVIEW_EXTERNAL_THIRD') return 'EXTERNAL_THIRD'
  return undefined
}

function recordRoundLabel(record: ReviewRecordItem) {
  if (record.action === 'CHANGE_REVIEWER' && record.comment?.includes('决定')) return `${roundLabel(record.review_round)}流向决定`
  if (record.action === 'CHANGE_REVIEWER') return `${roundLabel(record.review_round)}审核人变更`
  if (record.action === 'SUBMIT') return hasEarlierReject(record) ? `${roundLabel(record.review_round)}意见回复` : '报告送审'
  if (record.action === 'REJECT_RETURN') return `${roundLabel(record.review_round)}意见发出`
  if (record.action === 'APPROVE' && record.review_round === 'THIRD') return '报告审核通过待提交正式报告文件'
  return roundLabel(record.review_round)
}

function recordCommentText(record: ReviewRecordItem) {
  if (record.action === 'CHANGE_REVIEWER') return record.comment || '审核人已变更'
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
    const categories = hasEarlierReject(record) ? ['REPORT_ZIP', 'REVIEW_REPLY'] : ['REPORT_ZIP']
    return files.value.filter(file => categories.includes(file.file_category) && file.business_stage === stage && inCurrentRecordWindow(file))
  }
  return files.value.filter(file => file.file_category === 'REVIEW_OPINION' && file.business_stage === stage && inCurrentRecordWindow(file))
}

function reviewFileTypeLabel(file: WorkOrderFileItem) {
  if (file.file_category === 'REVIEW_OPINION') return '审核意见'
  if (file.file_category === 'REVIEW_REPLY') return '意见回复'
  return '附件'
}

function formatFileSize(size?: number | null) {
  if (!size) return '-'
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / 1024 / 1024).toFixed(1)} MB`
}

async function loadCandidates() {
  if (isReplyFlow.value && !canChangeReviewer.value) {
    reviewerUserId.value = currentRoundReviewerId.value || undefined
    userOptions.value = []
    return
  }
  if (!props.workOrderId || (!canSubmitReview.value && !canReviewerSelectNext.value)) {
    userOptions.value = []
    return
  }
  userOptions.value = (await listReviewCandidates(props.workOrderId, reviewRound.value)).items.filter(user => {
    if (user.user_id === currentRoundReviewerId.value) return false
    if (projectPartyIds.value.has(user.user_id)) return false
    if (reviewRound.value === 'FIRST' && [props.flowInfo?.second_reviewer_id, props.flowInfo?.third_reviewer_id].includes(user.user_id)) return false
    if (reviewRound.value === 'SECOND' && [props.flowInfo?.first_reviewer_id, props.flowInfo?.third_reviewer_id].includes(user.user_id)) return false
    if (reviewRound.value === 'THIRD' && [props.flowInfo?.first_reviewer_id, props.flowInfo?.second_reviewer_id].includes(user.user_id)) return false
    return true
  })
  if (pendingReviewerChange.value) {
    changeReviewerUserId.value = pendingReviewerChange.value.reviewer_user_id
    isReviewerChangePanelOpen.value = true
  }
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
  if (isReviewLocked.value) return ElMessage.warning(props.flowInfo?.review_submit_lock_reason || '报告送审暂不可办理')
  await uploadWorkOrderFile({
    work_order_id: props.workOrderId,
    file_category: 'REPORT_ZIP',
    business_stage: reviewStage(reviewRound.value),
    file: file.raw
  })
  ElMessage.success('待审报告资料包已上传')
  await loadFiles()
}

async function onReplySelected(file: UploadFile) {
  if (!props.workOrderId || !file.raw) return
  await uploadWorkOrderFile({
    work_order_id: props.workOrderId,
    file_category: 'REVIEW_REPLY',
    business_stage: reviewStage(reviewRound.value),
    file: file.raw
  })
  ElMessage.success('审核意见回复已上传')
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
  if (reviewerSelectSourceRound.value) {
    await routeApprovedReview({
      work_order_id: props.workOrderId,
      review_round: reviewerSelectSourceRound.value,
      route_mode: 'REVIEWER_SELECT_NEXT',
      reviewer_user_id: targetReviewerId,
      comment: comment.value || undefined
    })
    ElMessage.success(`已直接转交${roundLabel(reviewRound.value)}`)
    comment.value = ''
    await Promise.all([loadRecords(), loadFiles(), loadCandidates()])
    emit('changed')
    return
  }
  if (requiresManualUploadBeforeSubmit.value) return ElMessage.warning('请先上传待审报告资料包')
  if (isReplyFlow.value && !currentReplyFiles.value.length && !comment.value.trim()) {
    return ElMessage.warning('退回修改后重新送审时，审核意见回复文件或送审备注至少填写一项')
  }
  await submitReview({ work_order_id: props.workOrderId, review_round: reviewRound.value, reviewer_user_id: targetReviewerId, comment: comment.value || undefined })
  ElMessage.success(isReplyFlow.value ? '审核意见回复已提交' : '提交审核成功')
  comment.value = ''
  replyFileMode.value = 'REUPLOAD'
  await Promise.all([loadRecords(), loadFiles()])
  emit('changed')
}

function openReviewerChangePanel() {
  isReviewerChangePanelOpen.value = true
  changeReviewerUserId.value = pendingReviewerChange.value?.reviewer_user_id
  changeReviewerComment.value = pendingReviewerChange.value?.comment || changeReviewerComment.value
}

function cancelReviewerChangePanel() {
  isReviewerChangePanelOpen.value = false
  if (!pendingReviewerChange.value) {
    changeReviewerUserId.value = undefined
    changeReviewerComment.value = ''
  }
  replyFileMode.value = 'REUPLOAD'
}

async function onSubmitWithReviewerChange() {
  if (!props.workOrderId) return
  const targetReviewerId = pendingReviewerChange.value?.reviewer_user_id || changeReviewerUserId.value
  if (!targetReviewerId) return ElMessage.warning('请选择新的审核老师')
  if (!reusePreviousFile.value && !currentReportPackageFiles.value.length) return ElMessage.warning('请重新上传待审报告资料包，或选择沿用上轮文件')
  if (!pendingReviewerChange.value) {
    await changeReviewAssignee({
      work_order_id: props.workOrderId,
      review_round: reviewRound.value,
      reviewer_user_id: targetReviewerId,
      comment: changeReviewerComment.value || undefined
    })
  }
  await submitReview({
    work_order_id: props.workOrderId,
    review_round: reviewRound.value,
    reviewer_user_id: targetReviewerId,
    comment: changeReviewerComment.value || undefined
  })
  ElMessage.success('已提交审核意见回复并更换审核人')
  changeReviewerComment.value = ''
  comment.value = ''
  replyFileMode.value = 'REUPLOAD'
  isReviewerChangePanelOpen.value = false
  await Promise.all([loadRecords(), loadCandidates(), loadFiles()])
  emit('changed')
}

async function onDecision(action: 'APPROVE' | 'REJECT_RETURN') {
  if (!props.workOrderId) return
  if (action === 'REJECT_RETURN' && !reviewComment.value.trim() && !opinionFiles.value.some(file => file.is_current)) {
    return ElMessage.warning('返回修改时，审核意见文件或审核备注必须填写一项')
  }
  await decideReview({ work_order_id: props.workOrderId, review_round: reviewRound.value, action, comment: reviewComment.value || undefined })
  if (action === 'APPROVE' && ['FIRST', 'SECOND', 'EXTERNAL_FIRST', 'EXTERNAL_SECOND'].includes(reviewRound.value)) {
    const routedRound = reviewRound.value as 'FIRST' | 'SECOND' | 'EXTERNAL_FIRST' | 'EXTERNAL_SECOND'
    await openRoutingDialog(routedRound)
  } else {
    ElMessage.success(action === 'APPROVE' ? '审核通过' : '已退回修改')
  }
  reviewComment.value = ''
  await Promise.all([loadRecords(), loadFiles(), loadCandidates()])
  emit('changed')
}

async function openRoutingDialog(round: 'FIRST' | 'SECOND' | 'EXTERNAL_FIRST' | 'EXTERNAL_SECOND') {
  if (!props.workOrderId) return
  routingRound.value = round
  routingReviewerUserId.value = undefined
  routingUserOptions.value = []
  const nextRound = round === 'FIRST' ? 'SECOND' : round === 'SECOND' ? 'THIRD' : round === 'EXTERNAL_FIRST' ? 'EXTERNAL_SECOND' : 'EXTERNAL_THIRD'
  routingUserOptions.value = (await listReviewCandidates(props.workOrderId, nextRound)).items.filter(user => {
    if (projectPartyIds.value.has(user.user_id)) return false
    if (nextRound === 'SECOND' && [props.flowInfo?.first_reviewer_id, props.flowInfo?.third_reviewer_id].includes(user.user_id)) return false
    if (nextRound === 'THIRD' && [props.flowInfo?.first_reviewer_id, props.flowInfo?.second_reviewer_id].includes(user.user_id)) return false
    return true
  })
  routingReviewerUserId.value = routingUserOptions.value[0]?.user_id
  routingDialogVisible.value = true
}

async function routeApprovedToReviewer() {
  if (!props.workOrderId || !routingReviewerUserId.value) return ElMessage.warning(`请选择${routingNextRoundLabel.value}老师`)
  routingSubmitting.value = true
  try {
    await routeApprovedReview({
      work_order_id: props.workOrderId,
      review_round: routingRound.value,
      route_mode: 'REVIEWER_SELECT_NEXT',
      reviewer_user_id: routingReviewerUserId.value
    })
    ElMessage.success(`已直接转交${routingNextRoundLabel.value}`)
    routingDialogVisible.value = false
    await Promise.all([loadRecords(), loadFiles(), loadCandidates()])
    emit('changed')
  } finally {
    routingSubmitting.value = false
  }
}

async function routeApprovedToLeader() {
  if (!props.workOrderId) return
  routingSubmitting.value = true
  try {
    await routeApprovedReview({
      work_order_id: props.workOrderId,
      review_round: routingRound.value,
      route_mode: 'RETURN_TO_PROJECT_LEADER'
    })
    ElMessage.success('已转交项目负责人选择下一轮审核老师')
    routingDialogVisible.value = false
    await Promise.all([loadRecords(), loadFiles(), loadCandidates()])
    emit('changed')
  } finally {
    routingSubmitting.value = false
  }
}

async function onRequestOwnerExternalAuditConfirm() {
  if (!props.workOrderId) return
  await requestOwnerExternalAuditConfirm(props.workOrderId)
  ElMessage.success('已发送项目负责人确认信息')
  emit('changed')
}

async function onMarkNoExternalAudit() {
  if (!props.workOrderId) return
  await markNoExternalAudit(props.workOrderId)
  ElMessage.success('已进入附件上传流程')
  emit('changed')
}

async function onMarkHasExternalAudit() {
  if (!props.workOrderId) return
  await markHasExternalAudit(props.workOrderId)
  ElMessage.success('已进入外部审核复核准备流程')
  emit('changed')
}

async function onRecallRouting() {
  if (!props.workOrderId) return
  const targetLabel = reviewRound.value === 'SECOND'
    ? '二审转交'
    : reviewRound.value === 'THIRD'
      ? '三审转交'
      : reviewRound.value === 'EXTERNAL_SECOND'
        ? '外审二级复核转交'
        : '外审三级复核转交'
  await ElMessageBox.confirm(
    `确认撤回${targetLabel}吗？撤回后流程将回到上一审核/复核人员处。`,
    '撤回转交',
    {
      confirmButtonText: '确认撤回',
      cancelButtonText: '取消',
      type: 'warning'
    }
  )
  await recallRoutedReview({
    work_order_id: props.workOrderId,
    review_round: reviewRound.value as 'SECOND' | 'THIRD' | 'EXTERNAL_SECOND' | 'EXTERNAL_THIRD',
  })
  ElMessage.success('已撤回转交')
  await Promise.all([loadRecords(), loadFiles(), loadCandidates()])
  emit('changed')
}

function download(file: WorkOrderFileItem) {
  downloadWorkOrderFile(file.id, file.origin_file_name)
}

function canDeleteReportPackageFile(file: WorkOrderFileItem) {
  return canEditReportPackage.value && file.is_current && !file.locked
}

function canDeleteReplyFile(file: WorkOrderFileItem) {
  return canUploadReplyFile.value && file.file_category === 'REVIEW_REPLY' && file.is_current && !file.locked
}

async function onDeleteFile(file: WorkOrderFileItem) {
  await ElMessageBox.confirm(`确认删除当前文件「${file.origin_file_name}」吗？历史审核记录仍会保留。`, '删除文件', {
    type: 'warning',
    confirmButtonText: '确认删除',
    cancelButtonText: '取消'
  })
  await deleteWorkOrderFile(file.id)
  ElMessage.success('文件已删除')
  await loadFiles()
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
  if (!isReplyFlow.value) {
    replyFileMode.value = 'REUPLOAD'
    isReviewerChangePanelOpen.value = false
  }
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
}

.review-upload-block {
  width: 100%;
  display: flex;
  align-items: flex-start;
  gap: 16px;
  flex-wrap: wrap;
}

.review-upload-main {
  flex: 1;
  min-width: 260px;
  display: grid;
  gap: 14px;
}

.review-upload-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.file-zone-card {
  border: 1px solid #d8e5f2;
  border-radius: 10px;
  padding: 14px 16px;
  background: linear-gradient(135deg, #f8fbff 0%, #ffffff 68%);
  box-shadow: 0 8px 22px rgba(21, 78, 128, 0.06);
}

.file-zone-card--primary {
  border-left: 4px solid #1f5f99;
}

.file-zone-card--review {
  border-left: 4px solid #67a14b;
}

.file-zone-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  margin-bottom: 12px;
}

.file-zone-title {
  color: #0c3157;
  font-weight: 700;
  font-size: 15px;
}

.file-zone-subtitle {
  color: #6b7d90;
  font-size: 12px;
  margin-top: 4px;
}

.file-row-list {
  display: grid;
  gap: 8px;
}

.file-row {
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 9px 10px;
  border: 1px solid #e4edf6;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.86);
}

.file-row-main {
  min-width: 0;
  display: grid;
  gap: 2px;
}

.file-name {
  color: #163b5c;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-meta {
  color: #8090a0;
  font-size: 12px;
}

.routing-dialog-body {
  display: grid;
  gap: 16px;
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

@media (max-width: 900px) {
  .review-upload-block {
    flex-direction: column;
  }

  .review-upload-main {
    width: 100%;
    min-width: 100%;
  }

  .file-zone-header,
  .file-row {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
