<template>
  <el-card class="page-card" shadow="never">
    <template #header>工单详情</template>
    <el-form inline @submit.prevent>
      <el-form-item label="文件类型">
        <el-select v-model="uploadForm.file_category" style="width: 180px">
          <el-option label="合同" value="CONTRACT" />
          <el-option label="报告" value="REPORT" />
          <el-option label="附件" value="ATTACHMENT" />
        </el-select>
      </el-form-item>
      <el-form-item label="业务阶段">
        <el-select v-model="uploadForm.business_stage" style="width: 180px">
          <el-option label="初稿" value="DRAFT" />
          <el-option label="一审" value="FIRST_REVIEW" />
          <el-option label="二审" value="SECOND_REVIEW" />
          <el-option label="三审" value="THIRD_REVIEW" />
          <el-option label="终稿" value="FINAL" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <input type="file" @change="onFileChange" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="onUpload">上传文件</el-button>
      </el-form-item>
      <el-form-item>
        <el-button @click="loadData">刷新</el-button>
      </el-form-item>
    </el-form>

    <el-divider>文件版本</el-divider>
    <el-table :data="files" v-loading="loading">
      <el-table-column prop="file_category" label="类型" width="100" />
      <el-table-column prop="business_stage" label="阶段" width="130" />
      <el-table-column prop="version_no" label="版本" width="80" />
      <el-table-column prop="origin_file_name" label="文件名" min-width="220" />
      <el-table-column prop="uploaded_by" label="上传人ID" width="100" />
      <el-table-column prop="uploaded_at" label="上传时间" width="200" />
      <el-table-column label="当前" width="80">
        <template #default="scope">{{ scope.row.is_current ? '是' : '否' }}</template>
      </el-table-column>
    </el-table>

    <el-divider>流程日志</el-divider>
    <el-table :data="logs" v-loading="loading">
      <el-table-column prop="from_status" label="从状态" min-width="160" />
      <el-table-column prop="to_status" label="到状态" min-width="160" />
      <el-table-column prop="action_type" label="动作" width="180" />
      <el-table-column prop="operator_user_id" label="操作人ID" width="100" />
      <el-table-column prop="remark" label="备注" min-width="160" />
      <el-table-column prop="created_at" label="时间" width="200" />
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { listWorkOrderFiles, uploadWorkOrderFile, type WorkOrderFileItem } from '@/api/files'
import { listWorkflowLogs, type WorkflowLogItem } from '@/api/workflowLogs'

const route = useRoute()
const workOrderId = Number(route.params.id)

const loading = ref(false)
const files = ref<WorkOrderFileItem[]>([])
const logs = ref<WorkflowLogItem[]>([])
const pickedFile = ref<File | null>(null)

const uploadForm = reactive({
  file_category: 'REPORT',
  business_stage: 'DRAFT'
})

function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  pickedFile.value = input.files?.[0] || null
}

async function loadData() {
  if (!workOrderId) {
    return
  }
  loading.value = true
  try {
    const [fileData, logData] = await Promise.all([listWorkOrderFiles(workOrderId), listWorkflowLogs(workOrderId)])
    files.value = fileData.items
    logs.value = logData.items
  } finally {
    loading.value = false
  }
}

async function onUpload() {
  if (!workOrderId) {
    ElMessage.error('无效的工单ID')
    return
  }
  if (!pickedFile.value) {
    ElMessage.warning('请先选择文件')
    return
  }
  await uploadWorkOrderFile({
    work_order_id: workOrderId,
    file_category: uploadForm.file_category,
    business_stage: uploadForm.business_stage,
    file: pickedFile.value
  })
  ElMessage.success('文件上传成功')
  pickedFile.value = null
  await loadData()
}

onMounted(async () => {
  try {
    await loadData()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '工单详情加载失败')
  }
})
</script>
