<template>
  <div class="archive-layout">
    <div class="archive-main">
      <el-alert v-if="actionError" :title="actionError" type="error" :closable="false" />
      <el-alert v-if="actionSuccess" :title="actionSuccess" type="success" :closable="false" />
      <el-form label-width="120px">
        <el-form-item label="项目编号"><el-input :model-value="flowInfo?.project.project_no" disabled /></el-form-item>
        <el-form-item label="项目名称"><el-input :model-value="flowInfo?.project.project_name" disabled /></el-form-item>
        <el-form-item label="客户名称"><el-input :model-value="flowInfo?.project.client_name" disabled /></el-form-item>
        <el-form-item label="承接单位"><el-input :model-value="flowInfo?.project.undertaking_unit" disabled /></el-form-item>
        <el-form-item label="项目组人员">
          <el-input :model-value="memberNames" disabled />
        </el-form-item>
        <el-form-item label="签字评估师">
          <el-input :model-value="signerNames" disabled />
        </el-form-item>

        <template v-if="!canArchiveManager">
          <el-form-item label="底稿审核人">
            <el-select v-model="reviewerId" placeholder="选择档案管理员" style="width: 280px">
              <el-option v-for="user in archiveManagers" :key="user.id" :label="`${user.real_name}(${user.username})`" :value="user.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="电子底稿">
            <el-upload :auto-upload="false" :on-change="onDraftSelected" :show-file-list="false">
              <el-button type="primary">上传电子底稿</el-button>
            </el-upload>
            <div v-if="archiveSyncFiles.length" class="download-list archive-group">
              <div class="group-title">签发同步文件</div>
              <div v-for="file in archiveSyncFiles" :key="file.id" class="download-item">
                <span>{{ file.origin_file_name }}</span>
                <el-tag size="small" type="info">{{ file.display_label || '签发同步文件' }}</el-tag>
                <el-button type="primary" link @click="download(file)">下载</el-button>
              </div>
            </div>
            <div v-if="electronicDraftFiles.length" class="download-list archive-group">
              <div class="group-title">电子底稿</div>
              <div v-for="file in electronicDraftFiles" :key="file.id" class="download-item">
                <span>{{ file.origin_file_name }}</span>
                <el-button type="primary" link @click="download(file)">下载</el-button>
                <el-button type="warning" link @click="triggerReplace(file.id)">更改文件</el-button>
                <input
                  :ref="el => setReplaceInput(file.id, el)"
                  class="hidden-file-input"
                  type="file"
                  @change="event => onReplaceInput(file, event)"
                />
              </div>
            </div>
          </el-form-item>
          <el-form-item v-if="flowInfo?.archive_submission_type === 'APPROVED'">
            <el-button type="success" :loading="actionBusy" :disabled="actionDone" @click="onFinalize">归档</el-button>
          </el-form-item>
          <el-form-item v-else>
            <el-button type="primary" :disabled="!reviewerId" @click="submitOnline">发送电子底稿</el-button>
            <el-button type="success" :disabled="!reviewerId" @click="submitOffline">已线下提交纸质底稿</el-button>
          </el-form-item>
        </template>

        <template v-else>
          <el-form-item label="提交方式">
            <el-tag>{{ submissionLabel }}</el-tag>
          </el-form-item>
          <el-form-item label="上一步处理人">
            <el-input :model-value="archiveSubmitterName" disabled />
          </el-form-item>
          <el-form-item label="电子底稿">
            <div v-if="archiveSyncFiles.length" class="download-list archive-group">
              <div class="group-title">签发同步文件</div>
              <div v-for="file in archiveSyncFiles" :key="file.id" class="download-item">
                <span>{{ file.origin_file_name }}</span>
                <el-tag size="small" type="info">{{ file.display_label || '签发同步文件' }}</el-tag>
                <el-button type="primary" link @click="download(file)">下载</el-button>
              </div>
            </div>
            <div v-if="electronicDraftFiles.length" class="download-list archive-group">
              <div class="group-title">电子底稿</div>
              <div v-for="file in electronicDraftFiles" :key="file.id" class="download-item">
                <span>{{ file.origin_file_name }}</span>
                <el-button type="primary" link @click="download(file)">下载</el-button>
              </div>
            </div>
            <span v-else>-</span>
          </el-form-item>
          <el-form-item label="审核意见">
            <el-input v-model="remark" type="textarea" :rows="3" :disabled="!canReview || actionBusy || actionDone" />
          </el-form-item>
          <el-form-item>
            <el-button type="success" :loading="actionBusy" :disabled="!canReview || actionDone" @click="onApprove">审核通过，交回确认归档</el-button>
            <el-button type="danger" plain :disabled="!canReview || actionBusy || actionDone" @click="onReject">审核未通过请返回修改</el-button>
          </el-form-item>
          <el-alert v-if="!canReview" :title="archiveStatusText" :closable="false" />
        </template>
      </el-form>
    </div>

    <aside class="archive-side">
      <div class="archive-note-card">
        <div class="archive-note-title">归档判断</div>
        <div class="archive-note-status">
          {{ archiveStatusText }}
        </div>
        <div class="archive-note-subtitle">首屏先看底稿提交方式、审核责任人和当前是否满足归档条件。</div>
        <ol class="archive-note-list">
          <li>电子底稿与签发同步文件需能直接下载核查。</li>
          <li>提交前先明确线上/线下底稿方式。</li>
          <li>审核通过后才进入最终归档动作。</li>
        </ol>
      </div>
    </aside>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch, type ComponentPublicInstance } from 'vue'
import { ElMessage, type UploadFile } from 'element-plus'
import { approveArchive, finalizeArchive, rejectArchive, submitArchive } from '@/api/archives'
import { downloadWorkOrderFile, listWorkOrderFiles, replaceWorkOrderFile, uploadWorkOrderFile, type WorkOrderFileItem } from '@/api/files'
import { listProjectMembers, type ProjectMemberItem } from '@/api/projectMembers'
import type { ProjectFlowData } from '@/api/projectFlow'
import { listUserCandidates, type UserItem } from '@/api/users'
import { useAuthStore } from '@/store/auth'
import { canReviewArchive } from '@/utils/archiveReview'
import { workpaperError } from '@/utils/workpaperFeedback'

const props = defineProps<{ projectId?: number; workOrderId?: number; canOperate: boolean; userRoles: string[]; flowInfo?: ProjectFlowData }>()
const emit = defineEmits<{ (e: 'changed'): void }>()

const archiveManagers = ref<UserItem[]>([])
const members = ref<ProjectMemberItem[]>([])
const archiveSyncFiles = ref<WorkOrderFileItem[]>([])
const electronicDraftFiles = ref<WorkOrderFileItem[]>([])
const reviewerId = ref<number>()
const remark = ref('')
const auth = useAuthStore()
const actionBusy = ref(false)
const actionDone = ref(false)
const actionError = ref('')
const actionSuccess = ref('')
const canReview = computed(() => canReviewArchive(props.flowInfo?.current_work_order_status,
  props.flowInfo?.archive_submission_type, props.flowInfo?.archive_reviewer_id, auth.user?.id, props.userRoles))
const submissionLabel = computed(() => ({ ONLINE: '线上提交电子底稿', OFFLINE: '线下提交纸质底稿', APPROVED: '审核已通过', REJECTED: '已退回补充' }[props.flowInfo?.archive_submission_type || ''] || '尚未提交归档底稿'))
const archiveStatusText = computed(() => {
  if (props.flowInfo?.current_work_order_status === 'ARCHIVED') return '项目已归档'
  if (props.flowInfo?.archive_submission_type === 'APPROVED') return '底稿审核已通过，待项目人员确认归档'
  if (canReview.value) return '待您审核归档底稿'
  if (props.flowInfo?.current_work_order_status === 'ARCHIVE_REVIEWING') return '待指定档案管理员审核'
  return '当前无可审核的归档底稿；操作类底稿请进入“操作类底稿审核”办理'
})
const replaceInputs = new Map<number, HTMLInputElement>()

const canArchiveManager = computed(() => props.userRoles.some(role => ['ARCHIVE_MANAGER', 'ADMIN'].includes(role)))
const memberNames = computed(() => members.value.map(item => item.real_name).join('、') || '-')
const signerNames = computed(() => [props.flowInfo?.signer_one, props.flowInfo?.signer_two].filter(Boolean).join('、') || '-')
const archiveSubmitterName = computed(() => members.value.find(item => item.user_id === props.flowInfo?.archive_submitter_id)?.real_name || '-')
const projectPartyIds = computed(() => {
  const ids = new Set<number>()
  if (props.flowInfo?.project.project_leader_id) ids.add(props.flowInfo.project.project_leader_id)
  members.value.forEach(item => ids.add(item.user_id))
  return ids
})

async function load() {
  if (props.projectId) {
    members.value = (await listProjectMembers(props.projectId)).items
  }
  archiveManagers.value = (await listUserCandidates('ARCHIVE_MANAGER')).items.filter(user => !projectPartyIds.value.has(user.id))
  reviewerId.value = props.flowInfo?.archive_reviewer_id || reviewerId.value
  if (props.workOrderId) {
    const files = (await listWorkOrderFiles(props.workOrderId)).items.filter(file => file.business_stage === 'ARCHIVE')
    archiveSyncFiles.value = files.filter(file => file.source_type === 'SIGNOFF_SYNC')
    electronicDraftFiles.value = files.filter(file => file.file_category === 'ELECTRONIC_DRAFT' && file.source_type !== 'SIGNOFF_SYNC')
  }
}

async function onDraftSelected(file: UploadFile) {
  if (!props.workOrderId || !file.raw) return
  await uploadWorkOrderFile({ work_order_id: props.workOrderId, file_category: 'ELECTRONIC_DRAFT', business_stage: 'ARCHIVE', file: file.raw })
  ElMessage.success('电子底稿已上传')
  await load()
}

async function submitOnline() {
  if (!props.workOrderId || !reviewerId.value) return
  try {
    await submitArchive({ work_order_id: props.workOrderId, reviewer_user_id: reviewerId.value, submission_type: 'ONLINE' })
    ElMessage.success('已提交底稿，待审查')
    emit('changed')
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '提交电子底稿失败')
  }
}

async function submitOffline() {
  if (!props.workOrderId || !reviewerId.value) return
  try {
    await submitArchive({ work_order_id: props.workOrderId, reviewer_user_id: reviewerId.value, submission_type: 'OFFLINE' })
    ElMessage.success('已提交底稿，待审查')
    emit('changed')
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '提交纸质底稿失败')
  }
}

async function onApprove() {
  if (!canReview.value) return ElMessage.warning(archiveStatusText.value)
  await runArchiveAction(approveArchive)
}

async function onFinalize() {
  await runArchiveAction(finalizeArchive)
}

async function onReject() {
  if (!canReview.value) return ElMessage.warning(archiveStatusText.value)
  await runArchiveAction(rejectArchive)
}

async function runArchiveAction(action: typeof approveArchive) {
  if (actionBusy.value || actionDone.value) return
  actionError.value = ''; actionSuccess.value = ''
  if (!props.workOrderId) {
    actionError.value = '工单尚未加载，请刷新后重试'
    ElMessage.error(actionError.value)
    return
  }
  actionBusy.value = true
  try {
    const result = await action({ work_order_id: props.workOrderId, remark: remark.value || undefined })
    actionSuccess.value = result.message
    actionDone.value = true
    ElMessage.success(result.message)
    emit('changed')
  } catch (error) {
    actionError.value = workpaperError(error)
    ElMessage.error(actionError.value)
  } finally { actionBusy.value = false }
}

watch(() => [props.workOrderId, props.flowInfo?.archive_submission_type], () => { actionDone.value = false })

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
  ElMessage.success('电子底稿已更改')
  input.value = ''
  await load()
}

function download(file: WorkOrderFileItem) {
  downloadWorkOrderFile(file.id, file.origin_file_name)
}

onMounted(load)
watch(() => [props.projectId, props.workOrderId, props.flowInfo?.archive_reviewer_id], load)
</script>

<style scoped>
.download-list {
  display: grid;
  gap: 6px;
}

.archive-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 18px;
  align-items: start;
}

.archive-main,
.archive-side {
  min-width: 0;
}

.archive-group {
  margin-top: 8px;
}

.group-title {
  font-size: 13px;
  color: #64748b;
}

.download-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.hidden-file-input {
  display: none;
}

.archive-main :deep(.el-form) {
  border: 1px solid #d8e5f2;
  border-radius: 10px;
  padding: 18px;
  background: linear-gradient(180deg, #ffffff 0%, #fbfdff 100%);
}

.archive-note-card {
  border: 1px solid #d8e5f2;
  border-radius: 10px;
  padding: 16px;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
  position: sticky;
  top: 0;
}

.archive-note-title {
  color: #0c3157;
  font-size: 15px;
  font-weight: 700;
}

.archive-note-status {
  margin-top: 12px;
  color: #153a63;
  font-size: 16px;
  font-weight: 700;
}

.archive-note-subtitle {
  margin-top: 8px;
  color: #64748b;
  font-size: 12px;
  line-height: 1.6;
}

.archive-note-list {
  margin: 12px 0 0;
  padding-left: 20px;
  color: #475569;
  line-height: 1.7;
}

@media (max-width: 960px) {
  .archive-layout {
    grid-template-columns: 1fr;
  }

  .archive-note-card {
    position: static;
  }
}
</style>
