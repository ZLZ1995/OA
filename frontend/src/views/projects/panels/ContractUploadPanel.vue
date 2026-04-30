<template>
  <el-alert v-if="!canEdit" type="info" :closable="false" title="当前账号无合同上传权限，仅可查看。" show-icon style="margin-bottom: 12px"/>
  <el-upload :auto-upload="false" :on-change="onSelect" :show-file-list="false" :disabled="!canEdit">
    <el-button type="primary" :disabled="!canEdit">上传合同扫描件</el-button>
  </el-upload>

  <el-table :data="contracts" style="margin-top: 12px" v-loading="loading">
    <el-table-column prop="origin_file_name" label="文件名" />
    <el-table-column prop="uploaded_by" label="上传人ID" width="100" />
    <el-table-column prop="uploaded_at" label="上传时间" width="200" />
    <el-table-column label="操作" width="100">
      <template #default="{ row }">
        <el-button type="primary" link @click="download(row)">下载</el-button>
      </template>
    </el-table-column>
  </el-table>
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, type UploadFile } from 'element-plus'
import { listWorkOrderFiles, uploadWorkOrderFile, type WorkOrderFileItem } from '@/api/files'

const props = defineProps<{ workOrderId?: number; canEdit: boolean }>()
const emit = defineEmits<{ (e: 'changed'): void }>()

const loading = ref(false)
const contracts = ref<WorkOrderFileItem[]>([])

async function load() {
  if (!props.workOrderId) return
  loading.value = true
  try {
    const files = (await listWorkOrderFiles(props.workOrderId)).items
    contracts.value = files.filter(f => f.business_stage === 'CONTRACT' || f.file_category === 'CONTRACT')
  } finally { loading.value = false }
}

async function onSelect(file: UploadFile) {
  if (!props.workOrderId) return ElMessage.warning('当前项目暂无关联工单，无法上传合同')
  if (!file.raw) return
  await uploadWorkOrderFile({ work_order_id: props.workOrderId, file_category: 'CONTRACT', business_stage: 'CONTRACT', file: file.raw })
  ElMessage.success('合同上传成功')
  await load()
  emit('changed')
}

function download(row: WorkOrderFileItem) {
  window.open(`/api/files/download/${row.id}`, '_blank')
}

onMounted(load)
</script>
