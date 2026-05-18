<template>
  <div class="signoff-panel">
    <el-alert
      v-if="!canSignoff && !canOwnerUpload"
      type="info"
      :closable="false"
      title="当前账号仅可查看签发流程信息。"
      show-icon
      style="margin-bottom: 12px"
    />

    <el-descriptions :column="2" border style="margin-bottom: 16px">
      <el-descriptions-item label="项目名称">{{ flowInfo?.project.project_name || '-' }}</el-descriptions-item>
      <el-descriptions-item label="客户名称">{{ flowInfo?.project.client_name || '-' }}</el-descriptions-item>
      <el-descriptions-item label="当前状态">{{ signoffStatusText }}</el-descriptions-item>
      <el-descriptions-item label="项目负责人">{{ flowInfo?.project.project_leader_display_name || '-' }}</el-descriptions-item>
    </el-descriptions>

    <template v-if="canOwnerUpload">
      <el-divider>上传签发资料</el-divider>
      <el-form label-width="120px">
        <el-form-item label="报告附件">
          <el-upload :auto-upload="false" :on-change="onFormalReportSelected" :show-file-list="false">
            <el-button type="primary">{{ formalReportFiles.length ? '重新上传报告附件' : '上传报告附件' }}</el-button>
          </el-upload>
          <div v-if="formalReportFiles.length" class="file-list">
            <el-tag v-for="file in formalReportFiles" :key="file.id" type="info" effect="plain">
              {{ file.origin_file_name }}
            </el-tag>
          </div>
        </el-form-item>
        <el-form-item label="合同扫描件">
          <el-upload :auto-upload="false" :on-change="onFinalContractSelected" :show-file-list="false">
            <el-button type="primary">{{ contractFiles.length ? '重新上传合同扫描件' : '上传合同扫描件' }}</el-button>
          </el-upload>
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
          <el-button type="success" :disabled="!formalReportFiles.length || !contractFiles.length" @click="onEnterSignoff">
            进入签发审核
          </el-button>
        </el-form-item>
      </el-form>
    </template>

    <template v-if="canSignoff">
      <el-divider>签发审核</el-divider>
      <div class="signoff-grid">
        <el-card shadow="never">
          <template #header>报告文件</template>
          <div v-if="reviewPackageFiles.length" class="file-stack">
            <div v-for="file in reviewPackageFiles" :key="file.id" class="file-row">
              <span>{{ file.origin_file_name }}</span>
              <el-button type="primary" link @click="download(file)">下载</el-button>
            </div>
          </div>
          <span v-else>-</span>
        </el-card>
        <el-card shadow="never">
          <template #header>报告附件</template>
          <div v-if="formalReportFiles.length" class="file-stack">
            <div v-for="file in formalReportFiles" :key="file.id" class="file-row">
              <span>{{ file.origin_file_name }}</span>
              <el-button type="primary" link @click="download(file)">下载</el-button>
            </div>
          </div>
          <span v-else>-</span>
        </el-card>
        <el-card shadow="never">
          <template #header>合同扫描件</template>
          <div v-if="contractFiles.length" class="file-stack">
            <div v-for="file in contractFiles" :key="file.id" class="file-row">
              <span>{{ file.origin_file_name }}</span>
              <el-button type="primary" link @click="download(file)">下载</el-button>
            </div>
          </div>
          <span v-else>-</span>
        </el-card>
      </div>
      <div class="signoff-actions">
        <el-button type="success" @click="onApproveSignoff">同意签发</el-button>
        <el-button type="warning" plain @click="onReturnThird">报告需修改，返回三审</el-button>
        <el-button type="danger" plain @click="onReturnOwnerUpload">附件/合同错误，返回项目负责人</el-button>
      </div>
    </template>

    <template v-else-if="canAssignPrintRoomAfterSignoff">
      <el-alert
        type="warning"
        :closable="false"
        title="签发已通过，但尚未指定文印室人员和报告出具数量，请补充后转交报告出具。"
        show-icon
        style="margin-bottom: 12px"
      />
      <div class="signoff-actions">
        <el-button type="success" @click="onApproveSignoff">选择文印室并转交</el-button>
      </div>
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

const currentUserId = computed(() => auth.user?.id)
const canOwnerUpload = computed(() =>
  props.flowInfo?.current_work_order_status === 'WAIT_OWNER_SIGNOFF_UPLOAD' &&
  ['项目负责人', '项目组成员', '创建人'].includes(props.flowInfo?.user_role_in_project || '')
)
const canSignoff = computed(() =>
  props.flowInfo?.current_work_order_status === 'SIGNOFF_REVIEWING' &&
  (props.userRoles.includes('CHIEF_APPRAISER') || props.userRoles.includes('ADMIN')) &&
  (!props.flowInfo?.chief_appraiser_user_id || props.flowInfo?.chief_appraiser_user_id === currentUserId.value)
)
const canAssignPrintRoomAfterSignoff = computed(() =>
  props.flowInfo?.current_work_order_status === 'THIRD_APPROVED_WAIT_PRINTROOM' &&
  (props.userRoles.includes('CHIEF_APPRAISER') || props.userRoles.includes('ADMIN')) &&
  !props.flowInfo?.print_room_handler_id
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
  return props.flowInfo?.current_work_order_status || '-'
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
.file-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}

.signoff-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.file-stack {
  display: grid;
  gap: 8px;
}

.file-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.signoff-actions {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
}

@media (max-width: 900px) {
  .signoff-grid {
    grid-template-columns: 1fr;
  }
}
</style>
