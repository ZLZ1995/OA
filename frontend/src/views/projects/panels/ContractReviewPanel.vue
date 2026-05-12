<template>
  <el-alert
    v-if="!workOrderId"
    type="warning"
    :closable="false"
    title="当前项目暂无关联工单，无法办理合同审核。"
    show-icon
    style="margin-bottom: 12px"
  />
  <template v-else>
    <el-descriptions :column="2" border style="margin-bottom: 16px">
      <el-descriptions-item label="项目名称">{{ flowInfo?.project.project_name }}</el-descriptions-item>
      <el-descriptions-item label="客户名称">{{ flowInfo?.project.client_name }}</el-descriptions-item>
      <el-descriptions-item label="报告类型">{{ flowInfo?.project.report_type || '-' }}</el-descriptions-item>
      <el-descriptions-item label="项目来源">{{ flowInfo?.project.project_source_display || '-' }}</el-descriptions-item>
      <el-descriptions-item label="项目负责人">{{ flowInfo?.project.project_leader_display_name || '-' }}</el-descriptions-item>
      <el-descriptions-item label="合同审核状态">{{ flowInfo?.contract_review_status_display || '-' }}</el-descriptions-item>
    </el-descriptions>

    <el-table :data="contractFiles" v-loading="loading" style="margin-bottom: 16px">
      <el-table-column prop="origin_file_name" label="待审核合同文件" min-width="240" />
      <el-table-column prop="uploaded_at" label="上传时间" min-width="190" />
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button type="primary" link @click="download(row)">下载</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-form label-width="120px">
      <el-form-item label="审核意见">
        <el-input v-model="reviewComment" type="textarea" :rows="3" :disabled="!canReview" placeholder="请输入审核意见" />
      </el-form-item>
      <el-form-item label="审核附件">
        <el-upload :auto-upload="false" :on-change="onAttachmentSelected" :show-file-list="false" :disabled="!canReview">
          <el-button :disabled="!canReview">上传审核附件</el-button>
        </el-upload>
        <div v-if="reviewAttachment" class="attachment-preview">
          <span>{{ reviewAttachment.origin_file_name }}</span>
          <el-button type="primary" link @click="download(reviewAttachment)">下载</el-button>
        </div>
      </el-form-item>
      <el-form-item v-if="canReview">
        <el-space>
          <el-button type="success" @click="onApprove">审核通过</el-button>
          <el-button type="danger" plain @click="onReject">退回修改</el-button>
        </el-space>
      </el-form-item>
    </el-form>

    <el-divider>合同审核记录</el-divider>
    <el-table :data="records">
      <el-table-column prop="actionLabel" label="动作" width="120" />
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
import { ElMessage, type UploadFile } from 'element-plus'
import type { ProjectFlowData } from '@/api/projectFlow'
import type { WorkOrderFileItem } from '@/api/files'
import { getWorkOrderFileDownloadUrl, listWorkOrderFiles, uploadWorkOrderFile } from '@/api/files'
import {
  approveContractReview,
  rejectContractReview,
  listContractReviewRecords,
  type ContractReviewRecordItem
} from '@/api/contractReviews'
import { useAuthStore } from '@/store/auth'

const props = defineProps<{ workOrderId?: number; flowInfo?: ProjectFlowData; userRoles?: string[] }>()
const emit = defineEmits<{ (e: 'changed'): void }>()
const auth = useAuthStore()

const loading = ref(false)
const records = ref<(ContractReviewRecordItem & { actionLabel: string })[]>([])
const contractFiles = ref<WorkOrderFileItem[]>([])
const reviewAttachment = ref<WorkOrderFileItem | null>(null)
const reviewComment = ref('')

const canReview = computed(() => {
  const currentUserId = auth.user?.id
  return Boolean(
    currentUserId &&
    props.flowInfo?.current_work_order_status === 'CONTRACT_REVIEWING' &&
    props.flowInfo?.contract_reviewer_id === currentUserId &&
    props.userRoles?.some(role => ['CONTRACT_REVIEWER', 'ADMIN'].includes(role))
  )
})

function actionLabel(actionType: ContractReviewRecordItem['action_type']) {
  if (actionType === 'SUBMIT_CONTRACT') return '提交审核'
  if (actionType === 'APPROVE_CONTRACT') return '审核通过'
  return '退回修改'
}

async function load() {
  if (!props.workOrderId) {
    records.value = []
    contractFiles.value = []
    reviewAttachment.value = null
    return
  }
  loading.value = true
  try {
    await auth.ensureUserLoaded()
    const [recordData, fileData] = await Promise.all([
      listContractReviewRecords(props.workOrderId),
      listWorkOrderFiles(props.workOrderId)
    ])
    records.value = recordData.items.map(item => ({ ...item, actionLabel: actionLabel(item.action_type) }))
    contractFiles.value = fileData.items.filter(file => file.file_category === 'CONTRACT' && file.is_current)
    const latestReviewAttachment = fileData.items
      .filter(file => file.file_category === 'CONTRACT_REVIEW_ATTACHMENT')
      .sort((a, b) => b.id - a.id)[0]
    reviewAttachment.value = latestReviewAttachment || null
  } finally {
    loading.value = false
  }
}

async function onAttachmentSelected(file: UploadFile) {
  if (!props.workOrderId || !file.raw) return
  const uploaded = await uploadWorkOrderFile({
    work_order_id: props.workOrderId,
    file_category: 'CONTRACT_REVIEW_ATTACHMENT',
    business_stage: 'CONTRACT_REVIEW',
    file: file.raw
  })
  reviewAttachment.value = uploaded
  ElMessage.success('审核附件已上传')
}

async function onApprove() {
  const submitRecord = records.value.find(item => item.action_type === 'SUBMIT_CONTRACT')
  if (!submitRecord) return ElMessage.warning('未找到待处理的合同提交记录')
  await approveContractReview(submitRecord.id, {
    comment: reviewComment.value || undefined,
    review_attachment_file_id: reviewAttachment.value?.id
  })
  ElMessage.success('合同审核通过')
  reviewComment.value = ''
  reviewAttachment.value = null
  emit('changed')
}

async function onReject() {
  const submitRecord = records.value.find(item => item.action_type === 'SUBMIT_CONTRACT')
  if (!submitRecord) return ElMessage.warning('未找到待处理的合同提交记录')
  await rejectContractReview(submitRecord.id, {
    comment: reviewComment.value || undefined,
    review_attachment_file_id: reviewAttachment.value?.id
  })
  ElMessage.success('合同已退回修改')
  reviewComment.value = ''
  reviewAttachment.value = null
  emit('changed')
}

function download(file: Pick<WorkOrderFileItem, 'id'>) {
  window.open(getWorkOrderFileDownloadUrl(file.id), '_blank')
}

onMounted(load)
watch(() => [props.workOrderId, props.flowInfo?.current_work_order_status], load)
</script>

<style scoped>
.attachment-preview {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: 12px;
}
</style>
