<template>
  <el-alert v-if="!workOrderId" type="warning" :closable="false" title="当前项目尚未创建工单，无法送审。" show-icon />
  <template v-else>
    <el-form label-width="110px">
      <el-form-item label="审核轮次">
        <el-select v-model="reviewRound" style="width: 180px" @change="onRoundChange">
          <el-option label="一审" value="FIRST" />
          <el-option label="二审" value="SECOND" />
          <el-option label="三审" value="THIRD" />
        </el-select>
      </el-form-item>
      <el-form-item label="审核老师">
        <el-select v-model="reviewerUserId" placeholder="选择审核老师" style="width: 320px" :disabled="!canEdit" no-data-text="当前工单暂无可选审核老师，请检查审核轮次、工单状态、审核角色配置或用户权限。">
          <el-option v-for="u in userOptions" :key="u.user_id" :label="`${u.real_name}(${u.username})`" :value="u.user_id" />
        </el-select>
      </el-form-item>
      <el-form-item label="待审报告包">
        <el-upload :auto-upload="false" :on-change="onReportSelected" :show-file-list="true" :disabled="!canEdit">
          <el-button :disabled="!canEdit">上传待审报告</el-button>
        </el-upload>
      </el-form-item>
      <el-form-item label="送审备注">
        <el-input v-model="comment" type="textarea" :rows="3" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :disabled="!canEdit" @click="onSubmit">提交审核</el-button>
      </el-form-item>
    </el-form>

    <el-divider>已上传待审文件</el-divider>
    <el-table :data="reviewFiles" v-loading="filesLoading" empty-text="暂无待审报告文件">
      <el-table-column prop="origin_file_name" label="文件名" min-width="220" />
      <el-table-column label="审核轮次" width="120"><template #default> {{ roundLabel }} </template></el-table-column>
      <el-table-column prop="uploaded_by" label="上传人" width="100" />
      <el-table-column prop="uploaded_at" label="上传时间" width="190" />
      <el-table-column label="当前文件" width="90"><template #default="{ row }">{{ row.is_current ? '是' : '否' }}</template></el-table-column>
      <el-table-column label="操作" width="100"><template #default="{ row }"><el-button type="primary" link @click="downloadFile(row.id)">下载</el-button></template></el-table-column>
    </el-table>

    <el-divider>审核处理</el-divider>
    <el-space>
      <el-button type="success" :disabled="!canReview" @click="onDecision('APPROVE')">审核通过</el-button>
      <el-button type="danger" plain :disabled="!canReview" @click="onDecision('REJECT_RETURN')">返回修改</el-button>
    </el-space>

    <el-divider>审核记录</el-divider>
    <el-table :data="records" v-loading="loading">
      <el-table-column prop="review_round" label="轮次" width="100" />
      <el-table-column prop="action" label="动作" width="140" />
      <el-table-column prop="comment" label="意见" />
      <el-table-column prop="acted_at" label="时间" width="200" />
    </el-table>
  </template>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, type UploadFile } from 'element-plus'
import { decideReview, listReviewCandidates, listReviews, submitReview, type ReviewCandidateItem, type ReviewRecordItem } from '@/api/reviews'
import { getWorkOrderFileDownloadUrl, listWorkOrderFiles, uploadWorkOrderFile, type WorkOrderFileItem } from '@/api/files'

const props = defineProps<{ projectId: number; workOrderId?: number; canEdit: boolean; userRoles: string[] }>()
const emit = defineEmits<{ (e: 'changed'): void }>()

const reviewRound = ref<'FIRST'|'SECOND'|'THIRD'>('FIRST')
const reviewerUserId = ref<number>()
const comment = ref('')
const records = ref<ReviewRecordItem[]>([])
const userOptions = ref<ReviewCandidateItem[]>([])
const reviewFiles = ref<WorkOrderFileItem[]>([])
const loading = ref(false)
const filesLoading = ref(false)
const canReview = computed(() => props.userRoles.some(r => ['REVIEWER_L1','REVIEWER_L2','REVIEWER_L3','ADMIN','FIRST_REVIEWER','SECOND_REVIEWER','THIRD_REVIEWER'].includes(r)))
const stageMap = { FIRST: 'FIRST_REVIEW', SECOND: 'SECOND_REVIEW', THIRD: 'THIRD_REVIEW' } as const
const roundLabel = computed(() => ({ FIRST: '一审', SECOND: '二审', THIRD: '三审' }[reviewRound.value]))

async function loadCandidates() {
  if (!props.workOrderId) return
  const items = (await listReviewCandidates(props.workOrderId, reviewRound.value)).items
  userOptions.value = items
  if (import.meta.env.DEV) {
    console.info('[ReviewCandidates]', { projectId: props.projectId, workOrderId: props.workOrderId, reviewRound: reviewRound.value, candidatesLength: items.length })
  }
}

async function loadReviewFiles() {
  if (!props.workOrderId) return
  filesLoading.value = true
  try {
    const stage = stageMap[reviewRound.value]
    const files = (await listWorkOrderFiles(props.workOrderId)).items
    reviewFiles.value = files.filter(f => f.file_category === 'REPORT' && f.business_stage === stage)
  } finally { filesLoading.value = false }
}

async function loadRecords() {
  if (!props.workOrderId) return
  loading.value = true
  try { records.value = (await listReviews(props.workOrderId)).items } finally { loading.value = false }
}

async function onReportSelected(file: UploadFile) {
  if (!props.workOrderId || !file.raw) return
  await uploadWorkOrderFile({ work_order_id: props.workOrderId, file_category: 'REPORT', business_stage: stageMap[reviewRound.value], file: file.raw })
  ElMessage.success('待审报告已上传')
  await loadReviewFiles()
  emit('changed')
}

function downloadFile(fileId: number) { window.open(getWorkOrderFileDownloadUrl(fileId), '_blank') }

async function onSubmit() {
  if (!props.workOrderId || !reviewerUserId.value) return ElMessage.warning('请选择审核老师')
  await submitReview({ work_order_id: props.workOrderId, review_round: reviewRound.value, reviewer_user_id: reviewerUserId.value, comment: comment.value || undefined })
  ElMessage.success('提交审核成功')
  await loadRecords(); emit('changed')
}

async function onDecision(action: 'APPROVE'|'REJECT_RETURN') {
  if (!props.workOrderId) return
  await decideReview({ work_order_id: props.workOrderId, review_round: reviewRound.value, action, comment: comment.value || undefined })
  ElMessage.success(action === 'APPROVE' ? '审核通过' : '已返回修改')
  await loadRecords(); emit('changed')
}

async function onRoundChange() {
  reviewerUserId.value = undefined
  await Promise.all([loadCandidates(), loadReviewFiles()])
}

onMounted(async () => { await Promise.all([loadCandidates(), loadRecords(), loadReviewFiles()]) })
</script>
