<template>
  <div class="signoff-panel">
    <section class="signoff-overview-card">
      <div class="signoff-overview-head">
        <div>
          <div class="signoff-overview-title">签发审核</div>
          <div class="signoff-overview-subtitle">签发环节只处理签发资料确认、首席签发决策与文印转交。</div>
        </div>
        <el-tag :type="signoffStatusTagType" effect="plain">{{ signoffStatusText }}</el-tag>
      </div>

      <div class="signoff-meta-grid">
        <div class="signoff-meta-item">
          <span class="meta-label">项目名称</span>
          <span class="meta-value">{{ flowInfo?.project.project_name || '-' }}</span>
        </div>
        <div class="signoff-meta-item">
          <span class="meta-label">客户名称</span>
          <span class="meta-value">{{ flowInfo?.project.client_name || '-' }}</span>
        </div>
        <div class="signoff-meta-item">
          <span class="meta-label">项目负责人</span>
          <span class="meta-value">{{ flowInfo?.project.project_leader_display_name || '-' }}</span>
        </div>
        <div class="signoff-meta-item">
          <span class="meta-label">承接单位</span>
          <span class="meta-value">{{ flowInfo?.project.undertaking_unit || '-' }}</span>
        </div>
      </div>
    </section>

    <el-alert
      v-if="!canSignoff && !canOwnerUpload && !canAssignPrintRoomAfterSignoff"
      type="info"
      :closable="false"
      title="当前账号仅可查看签发流程信息。"
      show-icon
      style="margin-bottom: 14px"
    />

    <template v-if="canOwnerUpload">
      <div class="signoff-layout">
        <section class="signoff-main-card">
          <div class="section-header">
            <div>
              <div class="section-title">签发资料准备</div>
              <div class="section-subtitle">项目负责人补齐签发所需资料后，再提交首席签发审核。</div>
            </div>
          </div>

          <el-form label-width="120px">
            <el-form-item label="报告附件">
              <el-upload :auto-upload="false" :on-change="onFormalReportSelected" :show-file-list="false" :disabled="isUploading">
                <el-button type="primary" :disabled="isUploading">{{ formalReportFiles.length ? '重新上传报告附件' : '上传报告附件' }}</el-button>
              </el-upload>
              <UploadProgressInline :progress="formalReportUploadProgress" />
              <div v-if="formalReportFiles.length" class="file-list">
                <el-tag v-for="file in formalReportFiles" :key="file.id" type="info" effect="plain">
                  {{ file.origin_file_name }}
                </el-tag>
              </div>
            </el-form-item>

            <el-form-item label="合同扫描件">
              <el-upload :auto-upload="false" :on-change="onFinalContractSelected" :show-file-list="false" :disabled="isUploading">
                <el-button type="primary" :disabled="isUploading">{{ contractFiles.length ? '重新上传合同扫描件' : '上传合同扫描件' }}</el-button>
              </el-upload>
              <UploadProgressInline :progress="contractUploadProgress" />
              <div v-if="contractFiles.length" class="file-list">
                <el-tag v-for="file in contractFiles" :key="file.id" type="success" effect="plain">
                  {{ file.origin_file_name }}
                </el-tag>
              </div>
            </el-form-item>

            <el-form-item label="签字评估师" required>
              <el-space wrap>
                <el-input v-model="signerOne" placeholder="签字评估师一" style="width: 220px" />
                <el-input v-model="signerTwo" placeholder="签字评估师二" style="width: 220px" />
              </el-space>
            </el-form-item>

            <el-form-item label="报告出具数量" required>
              <el-input-number v-model="formalReportCount" :min="1" :precision="0" style="width: 180px" />
            </el-form-item>

            <el-form-item>
              <el-button type="success" :disabled="!formalReportFiles.length || !contractFiles.length || isUploading" @click="onEnterSignoff">
                提交进入签发审核
              </el-button>
            </el-form-item>
          </el-form>
        </section>

        <aside class="signoff-side-card">
          <div class="section-title">签发资料要求</div>
          <ol class="signoff-note-list">
            <li>报告附件与合同扫描件都需上传当前有效版本。</li>
            <li>签字评估师与报告出具数量在签发前确认完整。</li>
            <li>签发环节不处理报告送审意见，仅确认签发资料是否可进入文印。</li>
          </ol>
        </aside>
      </div>
    </template>

    <template v-else-if="canSignoff">
      <section class="signoff-stage-card">
        <div class="section-header">
          <div>
            <div class="section-title">首席签发决策</div>
            <div class="section-subtitle">本页只核对签发资料，不再执行送审意见往返。</div>
          </div>
        </div>

        <div class="signoff-stage-strip">
          <div class="stage-pill stage-pill--done">1. 项目负责人补齐签发资料</div>
          <div class="stage-arrow">→</div>
          <div class="stage-pill stage-pill--active">2. 首席评估师签发审核</div>
          <div class="stage-arrow">→</div>
          <div class="stage-pill">3. 转交文印室</div>
        </div>
      </section>

      <div class="signoff-layout">
        <section class="signoff-main-card">
          <div class="section-header">
            <div>
              <div class="section-title">待核签发资料</div>
              <div class="section-subtitle">核对报告包、签发附件和合同扫描件是否完整一致。</div>
            </div>
          </div>

          <div class="signoff-file-board">
            <section class="signoff-file-card signoff-file-card--report">
              <div class="file-card-title">报告包</div>
              <div v-if="reviewPackageFiles.length" class="file-stack">
                <div v-for="file in reviewPackageFiles" :key="file.id" class="file-row">
                  <span>{{ file.origin_file_name }}</span>
                  <el-button type="primary" link @click="download(file)">下载</el-button>
                </div>
              </div>
              <el-empty v-else description="暂无报告包" :image-size="42" />
            </section>

            <section class="signoff-file-card signoff-file-card--formal">
              <div class="file-card-title">报告附件</div>
              <div v-if="formalReportFiles.length" class="file-stack">
                <div v-for="file in formalReportFiles" :key="file.id" class="file-row">
                  <span>{{ file.origin_file_name }}</span>
                  <el-button type="primary" link @click="download(file)">下载</el-button>
                </div>
              </div>
              <el-empty v-else description="暂无报告附件" :image-size="42" />
            </section>

            <section class="signoff-file-card signoff-file-card--contract">
              <div class="file-card-title">合同扫描件</div>
              <div v-if="contractFiles.length" class="file-stack">
                <div v-for="file in contractFiles" :key="file.id" class="file-row">
                  <span>{{ file.origin_file_name }}</span>
                  <el-button type="primary" link @click="download(file)">下载</el-button>
                </div>
              </div>
              <el-empty v-else description="暂无合同扫描件" :image-size="42" />
            </section>
          </div>

          <div class="signoff-actions signoff-actions--left">
            <el-button type="success" @click="onApproveSignoff">同意签发</el-button>
            <el-button type="warning" plain @click="onReturnThird">报告需修改，返回三审</el-button>
            <el-button type="danger" plain @click="onReturnOwnerUpload">附件或合同错误，退回项目负责人</el-button>
          </div>
        </section>

        <aside class="signoff-side-card">
          <div class="section-title">签发判断口径</div>
          <ol class="signoff-note-list">
            <li>确认签发资料齐全，且与当前签发版本一致。</li>
            <li>如报告内容需重做，退回三审；如附件或合同有误，退回项目负责人补传。</li>
            <li>同意签发后，流程直接进入文印室处理，不再回到送审页。</li>
          </ol>
        </aside>
      </div>
    </template>

    <template v-else-if="canAssignPrintRoomAfterSignoff">
      <section class="signoff-main-card">
        <div class="section-header">
          <div>
            <div class="section-title">签发后转交文印室</div>
            <div class="section-subtitle">签发已通过，当前只需补指定文印室人员并完成转交。</div>
          </div>
        </div>
        <el-alert
          type="warning"
          :closable="false"
          title="签发已通过，但尚未指定文印室人员和报告出具数量，请补充后转交报告出具。"
          show-icon
          style="margin-bottom: 14px"
        />
        <div class="signoff-actions signoff-actions--left">
          <el-button type="success" @click="onApproveSignoff">选择文印室并转交</el-button>
        </div>
      </section>
    </template>

    <el-dialog v-model="approveDialogVisible" title="确认签发并转交文印室" width="520px">
      <el-form label-width="120px">
        <el-form-item label="文印室人员" required>
          <el-select v-model="approveDraft.print_room_handler_id" placeholder="请选择文印室人员" style="width: 100%">
            <el-option
              v-for="user in printRoomOptions"
              :key="user.id"
              :label="`${user.real_name || user.username}（${user.username}）`"
              :value="user.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="approveDialogVisible = false">取消</el-button>
        <el-button type="success" :loading="approveSubmitting" @click="submitApproveSignoff">
          确认签发并转交
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage, type UploadFile } from 'element-plus'
import UploadProgressInline from '@/components/common/UploadProgressInline.vue'
import type { ProjectFlowData } from '@/api/projectFlow'
import { downloadWorkOrderFile, listWorkOrderFiles, uploadWorkOrderFile, type WorkOrderFileItem } from '@/api/files'
import {
  approveSignoff,
  enterSignoffReview,
  returnSignoffToOwnerUpload,
  returnSignoffToThird,
} from '@/api/signoff'
import { listUserCandidates, type UserItem } from '@/api/users'
import { useAuthStore } from '@/store/auth'
import type { UploadProgressState } from '@/types/upload'

const props = defineProps<{ workOrderId?: number; flowInfo?: ProjectFlowData; userRoles: string[]; canEdit: boolean }>()
const emit = defineEmits<{ (e: 'changed'): void }>()

const auth = useAuthStore()
const files = ref<WorkOrderFileItem[]>([])
const printRoomOptions = ref<UserItem[]>([])
const formalReportCount = ref(1)
const signerOne = ref('')
const signerTwo = ref('')
const approveDialogVisible = ref(false)
const approveSubmitting = ref(false)
const approveDraft = ref<{ print_room_handler_id?: number }>({
  print_room_handler_id: undefined,
})
const formalReportUploadProgress = ref<UploadProgressState | null>(null)
const contractUploadProgress = ref<UploadProgressState | null>(null)

const currentUserId = computed(() => auth.user?.id)
const canHandleProjectSignoffByRole = computed(() => {
  const undertakingUnit = props.flowInfo?.project.undertaking_unit || ''
  return (
    props.userRoles.includes('ADMIN') ||
    props.userRoles.includes('CHIEF_APPRAISER') ||
    (undertakingUnit === '中勤' && props.userRoles.includes('CHIEF_APPRAISER_ZQ')) ||
    (undertakingUnit === '中立国际' && props.userRoles.includes('CHIEF_APPRAISER_ZLGJ'))
  )
})
const canOwnerUpload = computed(() =>
  props.flowInfo?.current_work_order_status === 'WAIT_OWNER_SIGNOFF_UPLOAD' &&
  ['项目负责人', '项目组成员', '创建人'].includes(props.flowInfo?.user_role_in_project || '')
)
const canSignoff = computed(() =>
  props.flowInfo?.current_work_order_status === 'SIGNOFF_REVIEWING' &&
  canHandleProjectSignoffByRole.value &&
  (!props.flowInfo?.chief_appraiser_user_id || props.flowInfo?.chief_appraiser_user_id === currentUserId.value)
)
const canAssignPrintRoomAfterSignoff = computed(() =>
  props.flowInfo?.current_work_order_status === 'THIRD_APPROVED_WAIT_PRINTROOM' &&
  canHandleProjectSignoffByRole.value &&
  !props.flowInfo?.print_room_handler_id
)
const isUploading = computed(() =>
  formalReportUploadProgress.value?.status === 'uploading' ||
  contractUploadProgress.value?.status === 'uploading'
)

const REVIEW_REPORT_STAGE_PRIORITY = [
  'REVIEW_EXTERNAL_THIRD',
  'REVIEW_THIRD',
  'REVIEW_EXTERNAL_SECOND',
  'REVIEW_SECOND',
  'REVIEW_EXTERNAL_FIRST',
  'REVIEW_FIRST',
]

const reviewPackageFiles = computed(() => {
  const reportFiles = files.value.filter(file => file.file_category === 'REPORT_ZIP' && file.is_current && file.source_type !== 'SIGNOFF_SYNC')
  const stage = REVIEW_REPORT_STAGE_PRIORITY.find(item => reportFiles.some(file => file.business_stage === item))
  if (!stage) return []
  return latestFilesByOriginal(reportFiles.filter(file => file.business_stage === stage))
})
const formalReportFiles = computed(() => latestFileOnly(files.value.filter(file => file.file_category === 'FORMAL_REPORT' && file.is_current && file.source_type !== 'SIGNOFF_SYNC')))
const contractFiles = computed(() => latestFileOnly(files.value.filter(file => file.file_category === 'FINAL_CONTRACT_SCAN' && file.is_current && file.source_type !== 'SIGNOFF_SYNC')))

const signoffStatusText = computed(() => {
  if (props.flowInfo?.current_work_order_status === 'WAIT_OWNER_SIGNOFF_UPLOAD') return '待上传报告附件与合同扫描件'
  if (props.flowInfo?.current_work_order_status === 'SIGNOFF_REVIEWING') return '签发审核中'
  if (props.flowInfo?.current_work_order_status === 'THIRD_APPROVED_WAIT_PRINTROOM') return '待转交文印室'
  return props.flowInfo?.current_work_order_status || '-'
})

const signoffStatusTagType = computed(() => {
  if (props.flowInfo?.current_work_order_status === 'WAIT_OWNER_SIGNOFF_UPLOAD') return 'warning'
  if (props.flowInfo?.current_work_order_status === 'SIGNOFF_REVIEWING') return 'success'
  if (props.flowInfo?.current_work_order_status === 'THIRD_APPROVED_WAIT_PRINTROOM') return 'info'
  return 'info'
})

function fileIdentity(file: WorkOrderFileItem) {
  return [
    file.source_file_id || file.storage_key,
    file.origin_file_name,
    file.file_size || 0,
  ].join('|')
}

function latestFilesByOriginal(fileList: WorkOrderFileItem[]) {
  const sorted = [...fileList].sort((a, b) => {
    const timeDiff = new Date(b.uploaded_at).getTime() - new Date(a.uploaded_at).getTime()
    if (timeDiff !== 0) return timeDiff
    return b.id - a.id
  })
  const result: WorkOrderFileItem[] = []
  const seen = new Set<string>()
  for (const file of sorted) {
    const key = fileIdentity(file)
    if (seen.has(key)) continue
    seen.add(key)
    result.push(file)
  }
  return result
}

function latestFileOnly(fileList: WorkOrderFileItem[]) {
  const latest = [...fileList].sort((a, b) => {
    const timeDiff = new Date(b.uploaded_at).getTime() - new Date(a.uploaded_at).getTime()
    if (timeDiff !== 0) return timeDiff
    return b.id - a.id
  })[0]
  return latest ? [latest] : []
}

async function loadFiles() {
  if (!props.workOrderId) {
    files.value = []
    return
  }
  files.value = (await listWorkOrderFiles(props.workOrderId)).items
}

async function loadPrintRoomOptions() {
  printRoomOptions.value = (await listUserCandidates('PRINT_ROOM')).items
}

async function onFormalReportSelected(file: UploadFile) {
  if (!props.workOrderId || !file.raw) return
  await uploadWorkOrderFile({
    work_order_id: props.workOrderId,
    file_category: 'FORMAL_REPORT',
    business_stage: 'FORMAL_REPORT',
    file: file.raw,
    onProgress: (progress) => {
      formalReportUploadProgress.value = progress
    }
  })
  ElMessage.success('报告附件已上传')
  await loadFiles()
}

async function onFinalContractSelected(file: UploadFile) {
  if (!props.workOrderId || !file.raw) return
  await uploadWorkOrderFile({
    work_order_id: props.workOrderId,
    file_category: 'FINAL_CONTRACT_SCAN',
    business_stage: 'FINAL_CONTRACT_SCAN',
    file: file.raw,
    onProgress: (progress) => {
      contractUploadProgress.value = progress
    }
  })
  ElMessage.success('合同扫描件已上传')
  await loadFiles()
}

async function onEnterSignoff() {
  if (!props.workOrderId) return
  if (!signerOne.value.trim() || !signerTwo.value.trim()) {
    ElMessage.warning('请填写两名签字评估师')
    return
  }
  if (!formalReportCount.value || formalReportCount.value < 1) {
    ElMessage.warning('请填写报告出具数量')
    return
  }
  await enterSignoffReview(props.workOrderId, {
    formal_report_count: formalReportCount.value,
    signer_one: signerOne.value.trim(),
    signer_two: signerTwo.value.trim(),
  })
  ElMessage.success('已进入签发审核')
  emit('changed')
}

async function onApproveSignoff() {
  if (!props.workOrderId) return
  if (!printRoomOptions.value.length) {
    await loadPrintRoomOptions()
  }
  if (!printRoomOptions.value.length) {
    ElMessage.warning('暂无可选文印室人员')
    return
  }
  approveDraft.value.print_room_handler_id = props.flowInfo?.print_room_handler_id || printRoomOptions.value[0]?.id
  approveDialogVisible.value = true
}

async function submitApproveSignoff() {
  if (!props.workOrderId) return
  if (!approveDraft.value.print_room_handler_id) {
    ElMessage.warning('请选择文印室人员')
    return
  }
  approveSubmitting.value = true
  try {
    await approveSignoff(props.workOrderId, {
      print_room_handler_id: approveDraft.value.print_room_handler_id,
    })
    approveDialogVisible.value = false
    ElMessage.success('签发通过，已转交文印室')
    emit('changed')
  } finally {
    approveSubmitting.value = false
  }
}

async function onReturnThird() {
  if (!props.workOrderId) return
  await returnSignoffToThird(props.workOrderId)
  ElMessage.success('已退回三审')
  emit('changed')
}

async function onReturnOwnerUpload() {
  if (!props.workOrderId) return
  await returnSignoffToOwnerUpload(props.workOrderId)
  ElMessage.success('已退回项目负责人上传附件')
  emit('changed')
}

function download(file: WorkOrderFileItem) {
  downloadWorkOrderFile(file.id, file.origin_file_name)
}

onMounted(() => {
  formalReportCount.value = props.flowInfo?.formal_report_count || 1
  signerOne.value = props.flowInfo?.signer_one || ''
  signerTwo.value = props.flowInfo?.signer_two || ''
  loadFiles()
})
watch(
  () => [
    props.workOrderId,
    props.flowInfo?.current_work_order_status,
    props.flowInfo?.formal_report_count,
    props.flowInfo?.signer_one,
    props.flowInfo?.signer_two,
  ],
  () => {
    formalReportCount.value = props.flowInfo?.formal_report_count || formalReportCount.value || 1
    signerOne.value = props.flowInfo?.signer_one || signerOne.value || ''
    signerTwo.value = props.flowInfo?.signer_two || signerTwo.value || ''
    loadFiles()
  }
)
</script>

<style scoped>
.signoff-panel {
  display: grid;
  gap: 16px;
}

.signoff-overview-card,
.signoff-main-card,
.signoff-side-card,
.signoff-stage-card {
  border: 1px solid #d8e5f2;
  border-radius: 10px;
  background: linear-gradient(180deg, #ffffff 0%, #fbfdff 100%);
}

.signoff-overview-card,
.signoff-main-card,
.signoff-stage-card {
  padding: 18px;
}

.signoff-side-card {
  padding: 16px;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
}

.signoff-overview-head,
.section-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.signoff-overview-title,
.section-title,
.file-card-title {
  color: #0c3157;
  font-weight: 700;
}

.signoff-overview-title {
  font-size: 18px;
}

.signoff-overview-subtitle,
.section-subtitle {
  margin-top: 6px;
  color: #64748b;
  font-size: 12px;
  line-height: 1.6;
}

.signoff-meta-grid {
  margin-top: 16px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.signoff-meta-item {
  min-width: 0;
  display: grid;
  gap: 4px;
  padding: 12px 14px;
  border: 1px solid #e3edf7;
  border-radius: 8px;
  background: #f9fbfe;
}

.meta-label {
  color: #6b7d90;
  font-size: 12px;
}

.meta-value {
  color: #153a63;
  font-weight: 600;
  word-break: break-all;
}

.signoff-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 18px;
  align-items: start;
}

.signoff-stage-strip {
  margin-top: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.stage-pill {
  padding: 10px 14px;
  border-radius: 999px;
  border: 1px solid #d8e5f2;
  background: #f8fbff;
  color: #64748b;
  font-size: 13px;
  font-weight: 600;
}

.stage-pill--done {
  border-color: #b9dfc1;
  background: #f3fbf5;
  color: #2f7a3f;
}

.stage-pill--active {
  border-color: #b7d0eb;
  background: #eef5fc;
  color: #153a63;
}

.stage-arrow {
  color: #8aa0b4;
  font-weight: 700;
}

.signoff-file-board {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.signoff-file-card {
  min-width: 0;
  border: 1px solid #dbe7f2;
  border-radius: 10px;
  padding: 16px;
  background: #fff;
}

.signoff-file-card--report {
  border-top: 3px solid #1f5f99;
}

.signoff-file-card--formal {
  border-top: 3px solid #3e8a57;
}

.signoff-file-card--contract {
  border-top: 3px solid #d45b2c;
}

.file-card-title {
  margin-bottom: 12px;
  font-size: 15px;
}

.file-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}

.file-stack {
  display: grid;
  gap: 8px;
}

.file-row {
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border: 1px solid #e7eef6;
  border-radius: 8px;
  background: #f9fbfd;
}

.file-row span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.signoff-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.signoff-actions--left {
  margin-top: 16px;
  justify-content: flex-start;
}

.signoff-note-list {
  margin: 12px 0 0;
  padding-left: 20px;
  color: #475569;
  line-height: 1.75;
}

@media (max-width: 900px) {
  .signoff-meta-grid,
  .signoff-layout,
  .signoff-file-board {
    grid-template-columns: 1fr;
  }

  .signoff-overview-head,
  .section-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .signoff-stage-strip {
    align-items: flex-start;
  }

  .stage-arrow {
    display: none;
  }

  .file-row {
    align-items: stretch;
    flex-direction: column;
  }

  .file-row span {
    white-space: normal;
  }
}
</style>
