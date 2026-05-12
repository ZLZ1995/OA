<template>
  <el-alert
    v-if="!canEdit"
    type="info"
    :closable="false"
    title="当前账号无合同初稿上传权限，仅可查看。"
    show-icon
    style="margin-bottom: 12px"
  />

  <el-alert
    v-if="isLocked"
    type="success"
    :closable="false"
    title="合同初稿审核已通过，合同初稿文件已锁定。"
    show-icon
    style="margin-bottom: 12px"
  />

  <el-form label-width="120px">
    <el-form-item label="当前审核状态">
      <el-tag :type="statusTagType" effect="plain">{{ flowInfo?.contract_review_status_display || '待上传合同初稿' }}</el-tag>
    </el-form-item>
    <el-form-item label="合同审核人">
      <el-select v-model="reviewerId" placeholder="选择合同审核人" style="width: 320px" :disabled="!canSubmitContract">
        <el-option v-for="user in reviewerOptions" :key="user.id" :label="`${user.real_name}(${user.username})`" :value="user.id" />
      </el-select>
    </el-form-item>
    <el-form-item label="提交说明">
      <el-input v-model="comment" type="textarea" :rows="3" :disabled="!canSubmitContract" />
    </el-form-item>
    <el-form-item label="上传合同初稿">
      <el-upload :auto-upload="false" :on-change="onSelect" :show-file-list="false" :disabled="!canEditContract">
        <el-button type="primary" :disabled="!canEditContract">上传合同初稿扫描件</el-button>
      </el-upload>
    </el-form-item>
  </el-form>

  <el-table :data="contracts" style="margin-top: 12px" v-loading="loading">
    <el-table-column prop="origin_file_name" label="文件名" min-width="220" />
    <el-table-column prop="uploaded_by_name" label="上传人" min-width="120" />
    <el-table-column prop="uploaded_at" label="上传时间" min-width="190" />
    <el-table-column label="操作" width="220">
      <template #default="{ row }">
        <el-space>
          <el-button type="primary" link @click="download(row)">下载</el-button>
          <el-button type="warning" link :disabled="!canEditContract" @click="triggerReplace(row.id)">重新上传</el-button>
        </el-space>
        <input
          :ref="el => setReplaceInput(row.id, el)"
          class="hidden-file-input"
          type="file"
          @change="event => onReplaceInput(row, event)"
        />
      </template>
    </el-table-column>
  </el-table>

  <div class="panel-actions">
    <el-button
      type="primary"
      :disabled="!canSubmitContract || !workOrderId || contracts.length === 0 || !reviewerId"
      :loading="submitting"
      @click="onComplete"
    >
      提交合同初稿审核
    </el-button>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch, type ComponentPublicInstance } from 'vue'
import { ElMessage, type UploadFile } from 'element-plus'
import {
  completeContractUpload,
  getWorkOrderFileDownloadUrl,
  listWorkOrderFiles,
  replaceWorkOrderFile,
  uploadWorkOrderFile,
  type WorkOrderFileItem
} from '@/api/files'
import { submitContractReview } from '@/api/contractReviews'
import { listUserCandidates, type UserItem } from '@/api/users'
import { updateWorkOrder } from '@/api/workorders'
import type { ProjectFlowData } from '@/api/projectFlow'

const props = defineProps<{ workOrderId?: number; canEdit: boolean; flowInfo?: ProjectFlowData; userRoles?: string[] }>()
const emit = defineEmits<{ (e: 'changed'): void }>()

const loading = ref(false)
const submitting = ref(false)
const contracts = ref<WorkOrderFileItem[]>([])
const reviewerOptions = ref<UserItem[]>([])
const reviewerId = ref<number>()
const comment = ref('')
const replaceInputs = new Map<number, HTMLInputElement>()

const statusCode = computed(() => props.flowInfo?.current_work_order_status || '')
const isLocked = computed(() => statusCode.value === 'CONTRACT_APPROVED')
const canEditContract = computed(() => props.canEdit && !isLocked.value && statusCode.value !== 'CONTRACT_REVIEWING')
const canSubmitContract = computed(() => props.canEdit && !isLocked.value)
const statusTagType = computed(() => {
  if (statusCode.value === 'CONTRACT_APPROVED') return 'success'
  if (statusCode.value === 'CONTRACT_REJECTED') return 'warning'
  if (statusCode.value === 'CONTRACT_REVIEWING') return 'primary'
  return 'info'
})

async function load() {
  if (!props.workOrderId) {
    contracts.value = []
    return
  }
  loading.value = true
  try {
    const files = (await listWorkOrderFiles(props.workOrderId)).items
    contracts.value = files.filter(file => file.business_stage === 'CONTRACT_DRAFT' || file.file_category === 'CONTRACT_DRAFT')
    reviewerId.value = props.flowInfo?.contract_reviewer_id || reviewerId.value
    reviewerOptions.value = (await listUserCandidates('CONTRACT_REVIEWER')).items
  } finally {
    loading.value = false
  }
}

async function onSelect(file: UploadFile) {
  if (!props.workOrderId) return ElMessage.warning('当前项目暂无关联工单，无法上传合同初稿')
  if (!file.raw) return
  await uploadWorkOrderFile({
    work_order_id: props.workOrderId,
    file_category: 'CONTRACT_DRAFT',
    business_stage: 'CONTRACT_DRAFT',
    file: file.raw
  })
  ElMessage.success('合同初稿上传成功')
  await load()
  emit('changed')
}

async function onReplace(row: WorkOrderFileItem, file: File) {
  await replaceWorkOrderFile(row.id, file)
  ElMessage.success('合同初稿文件已替换')
  await load()
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
  await onReplace(row, file)
  input.value = ''
}

async function onComplete() {
  if (!props.workOrderId) return ElMessage.warning('当前项目暂无关联工单，无法提交')
  if (!contracts.value.length) return ElMessage.warning('请先上传合同初稿扫描件')
  if (!reviewerId.value) return ElMessage.warning('请选择合同审核人')

  submitting.value = true
  try {
    await updateWorkOrder(props.workOrderId, { contract_reviewer_id: reviewerId.value })
    await completeContractUpload(props.workOrderId)
    await submitContractReview({
      work_order_id: props.workOrderId,
      reviewer_user_id: reviewerId.value,
      comment: comment.value || undefined
    })
    ElMessage.success('合同初稿已提交审核')
    comment.value = ''
    emit('changed')
  } finally {
    submitting.value = false
  }
}

function download(row: WorkOrderFileItem) {
  window.open(getWorkOrderFileDownloadUrl(row.id), '_blank')
}

onMounted(load)
watch(() => [props.workOrderId, props.flowInfo?.contract_reviewer_id, props.flowInfo?.current_work_order_status], load)
</script>

<style scoped>
.panel-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.hidden-file-input {
  display: none;
}
</style>
