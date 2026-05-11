<template>
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
        <div v-if="draftFiles.length" class="download-list">
          <div v-for="file in draftFiles" :key="file.id" class="download-item">
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
        <el-button type="success" @click="onFinalize">归档</el-button>
      </el-form-item>
      <el-form-item v-else>
        <el-button type="primary" :disabled="!reviewerId || draftFiles.length === 0" @click="submitOnline">发送电子底稿</el-button>
        <el-button type="success" :disabled="!reviewerId" @click="submitOffline">已线下提交纸质底稿</el-button>
      </el-form-item>
    </template>

    <template v-else>
      <el-form-item label="提交方式">
        <el-tag>{{ flowInfo?.archive_submission_type === 'ONLINE' ? '线上提交电子底稿' : '线下提交纸质底稿' }}</el-tag>
      </el-form-item>
      <el-form-item label="上一步处理人">
        <el-input :model-value="archiveSubmitterName" disabled />
      </el-form-item>
      <el-form-item label="电子底稿">
        <div v-if="draftFiles.length" class="download-list">
          <div v-for="file in draftFiles" :key="file.id" class="download-item">
            <span>{{ file.origin_file_name }}</span>
            <el-button type="primary" link @click="download(file)">下载</el-button>
          </div>
        </div>
        <span v-else>-</span>
      </el-form-item>
      <el-form-item label="审核意见">
        <el-input v-model="remark" type="textarea" :rows="3" />
      </el-form-item>
      <el-form-item>
        <el-button type="success" @click="onApprove">审核通过已归档</el-button>
        <el-button type="danger" plain @click="onReject">审核未通过请返回修改</el-button>
      </el-form-item>
    </template>
  </el-form>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch, type ComponentPublicInstance } from 'vue'
import { ElMessage, type UploadFile } from 'element-plus'
import { approveArchive, finalizeArchive, rejectArchive, submitArchive } from '@/api/archives'
import { getWorkOrderFileDownloadUrl, listWorkOrderFiles, replaceWorkOrderFile, uploadWorkOrderFile, type WorkOrderFileItem } from '@/api/files'
import { listProjectMembers, type ProjectMemberItem } from '@/api/projectMembers'
import type { ProjectFlowData } from '@/api/projectFlow'
import { listUserCandidates, type UserItem } from '@/api/users'

const props = defineProps<{ projectId?: number; workOrderId?: number; canOperate: boolean; userRoles: string[]; flowInfo?: ProjectFlowData }>()
const emit = defineEmits<{ (e: 'changed'): void }>()

const archiveManagers = ref<UserItem[]>([])
const members = ref<ProjectMemberItem[]>([])
const draftFiles = ref<WorkOrderFileItem[]>([])
const reviewerId = ref<number>()
const remark = ref('')
const replaceInputs = new Map<number, HTMLInputElement>()

const canArchiveManager = computed(() => props.userRoles.some(role => ['ARCHIVE_MANAGER', 'ADMIN'].includes(role)))
const memberNames = computed(() => members.value.map(item => item.real_name).join('、') || '-')
const signerNames = computed(() => [props.flowInfo?.signer_one, props.flowInfo?.signer_two].filter(Boolean).join('、') || '-')
const archiveSubmitterName = computed(() => members.value.find(item => item.user_id === props.flowInfo?.archive_submitter_id)?.real_name || '-')

async function load() {
  if (props.projectId) {
    members.value = (await listProjectMembers(props.projectId)).items
  }
  archiveManagers.value = (await listUserCandidates('ARCHIVE_MANAGER')).items
  reviewerId.value = props.flowInfo?.archive_reviewer_id || reviewerId.value
  if (props.workOrderId) {
    draftFiles.value = (await listWorkOrderFiles(props.workOrderId)).items.filter(
      file => file.file_category === 'ELECTRONIC_DRAFT' || file.business_stage === 'ARCHIVE'
    )
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
  if (!draftFiles.value.length) return ElMessage.warning('请先上传电子底稿')
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
  if (!props.workOrderId) return
  await approveArchive({ work_order_id: props.workOrderId, remark: remark.value || undefined })
  ElMessage.success('底稿审核通过，已回到项目人员待办')
  emit('changed')
}

async function onFinalize() {
  if (!props.workOrderId) return
  await finalizeArchive({ work_order_id: props.workOrderId, remark: remark.value || undefined })
  ElMessage.success('项目已归档')
  emit('changed')
}

async function onReject() {
  if (!props.workOrderId) return
  await rejectArchive({ work_order_id: props.workOrderId, remark: remark.value || undefined })
  ElMessage.success('已返回修改')
  emit('changed')
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
  ElMessage.success('电子底稿已更改')
  input.value = ''
  await load()
}

function download(file: WorkOrderFileItem) {
  window.open(getWorkOrderFileDownloadUrl(file.id), '_blank')
}

onMounted(load)
watch(() => [props.projectId, props.workOrderId, props.flowInfo?.archive_reviewer_id], load)
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
