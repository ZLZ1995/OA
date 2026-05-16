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
            <el-button type="primary">上传报告附件</el-button>
          </el-upload>
          <div v-if="formalReportFiles.length" class="file-list">
            <el-tag v-for="file in formalReportFiles" :key="file.id" type="info" effect="plain">
              {{ file.origin_file_name }}
            </el-tag>
          </div>
        </el-form-item>
        <el-form-item label="合同扫描件">
          <el-upload :auto-upload="false" :on-change="onFinalContractSelected" :show-file-list="false">
            <el-button type="primary">上传合同扫描件</el-button>
          </el-upload>
          <div v-if="contractFiles.length" class="file-list">
            <el-tag v-for="file in contractFiles" :key="file.id" type="success" effect="plain">
              {{ file.origin_file_name }}
            </el-tag>
          </div>
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
import { useAuthStore } from '@/store/auth'

const props = defineProps<{ workOrderId?: number; flowInfo?: ProjectFlowData; userRoles: string[]; canEdit: boolean }>()
const emit = defineEmits<{ (e: 'changed'): void }>()

const auth = useAuthStore()
const files = ref<WorkOrderFileItem[]>([])

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

const reviewPackageFiles = computed(() => files.value.filter(file => file.file_category === 'REPORT_ZIP'))
const formalReportFiles = computed(() => files.value.filter(file => file.file_category === 'FORMAL_REPORT' && file.is_current))
const contractFiles = computed(() => files.value.filter(file => file.file_category === 'FINAL_CONTRACT_SCAN' && file.is_current))

const signoffStatusText = computed(() => {
  if (props.flowInfo?.current_work_order_status === 'WAIT_OWNER_SIGNOFF_UPLOAD') return '待上传报告附件与合同扫描件'
  if (props.flowInfo?.current_work_order_status === 'SIGNOFF_REVIEWING') return '签发审核中'
  return props.flowInfo?.current_work_order_status || '-'
})

async function loadFiles() {
  if (!props.workOrderId) {
    files.value = []
    return
  }
  files.value = (await listWorkOrderFiles(props.workOrderId)).items
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
  await enterSignoffReview(props.workOrderId)
  ElMessage.success('已进入签发审核')
  emit('changed')
}

async function onApproveSignoff() {
  if (!props.workOrderId) return
  await approveSignoff(props.workOrderId)
  ElMessage.success('签发通过')
  emit('changed')
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

onMounted(loadFiles)
watch(() => [props.workOrderId, props.flowInfo?.current_work_order_status], loadFiles)
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
