<template>
  <el-alert
    v-if="!canEdit"
    type="info"
    :closable="false"
    title="当前账号无合同上传权限，仅可查看。"
    show-icon
    style="margin-bottom: 12px"
  />

  <el-upload :auto-upload="false" :on-change="onSelect" :show-file-list="false" :disabled="!canEdit">
    <el-button type="primary" :disabled="!canEdit">上传合同扫描件</el-button>
  </el-upload>

  <el-table :data="contracts" style="margin-top: 12px" v-loading="loading">
    <el-table-column prop="origin_file_name" label="文件名" min-width="180" />
    <el-table-column prop="uploaded_by" label="上传人ID" width="100" />
    <el-table-column prop="uploaded_at" label="上传时间" min-width="190" />
    <el-table-column label="操作" width="190">
      <template #default="{ row }">
        <el-space>
          <el-button type="primary" link @click="download(row)">下载</el-button>
          <el-button type="warning" link :disabled="!canEdit" @click="triggerReplace(row.id)">重新上传</el-button>
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
      :disabled="!canEdit || !workOrderId || contracts.length === 0"
      :loading="submitting"
      @click="onComplete"
    >
      提交并进入下一步
    </el-button>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch, type ComponentPublicInstance } from 'vue'
import { ElMessage, type UploadFile } from 'element-plus'
import {
  completeContractUpload,
  getWorkOrderFileDownloadUrl,
  listWorkOrderFiles,
  replaceWorkOrderFile,
  uploadWorkOrderFile,
  type WorkOrderFileItem
} from '@/api/files'

const props = defineProps<{ workOrderId?: number; canEdit: boolean }>()
const emit = defineEmits<{ (e: 'changed'): void }>()

const loading = ref(false)
const submitting = ref(false)
const contracts = ref<WorkOrderFileItem[]>([])
const replaceInputs = new Map<number, HTMLInputElement>()

async function load() {
  if (!props.workOrderId) {
    contracts.value = []
    return
  }
  loading.value = true
  try {
    const files = (await listWorkOrderFiles(props.workOrderId)).items
    contracts.value = files.filter(file => file.business_stage === 'CONTRACT' || file.file_category === 'CONTRACT')
  } finally {
    loading.value = false
  }
}

async function onSelect(file: UploadFile) {
  if (!props.workOrderId) return ElMessage.warning('当前项目暂无关联工单，无法上传合同')
  if (!file.raw) return
  await uploadWorkOrderFile({
    work_order_id: props.workOrderId,
    file_category: 'CONTRACT',
    business_stage: 'CONTRACT',
    file: file.raw
  })
  ElMessage.success('合同上传成功')
  await load()
  emit('changed')
}

async function onReplace(row: WorkOrderFileItem, file: File) {
  await replaceWorkOrderFile(row.id, file)
  ElMessage.success('合同扫描件已替换')
  await load()
  emit('changed')
}

function setReplaceInput(fileId: number, el: Element | ComponentPublicInstance | null) {
  if (el instanceof HTMLInputElement) {
    replaceInputs.set(fileId, el)
  }
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
  if (contracts.value.length === 0) return ElMessage.warning('请先上传合同扫描件')

  submitting.value = true
  try {
    await completeContractUpload(props.workOrderId)
    ElMessage.success('合同上传已提交，已进入报告送审')
    emit('changed')
  } finally {
    submitting.value = false
  }
}

function download(row: WorkOrderFileItem) {
  window.open(getWorkOrderFileDownloadUrl(row.id), '_blank')
}

onMounted(load)
watch(() => props.workOrderId, load)
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
