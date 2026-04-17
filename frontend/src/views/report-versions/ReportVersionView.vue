<template>
  <el-card class="page-card" shadow="never">
    <template #header>报告版本管理</template>

    <el-form inline>
      <el-form-item label="工单">
        <el-select v-model="workOrderId" style="width: 300px" @change="onWorkOrderChange">
          <el-option v-for="w in workOrders" :key="w.id" :label="`${w.work_order_no} - ${w.title}`" :value="w.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="文件">
        <el-select v-model="fileId" style="width: 260px">
          <el-option v-for="f in files" :key="f.id" :label="`${f.file_category}/${f.business_stage} v${f.version_no}`" :value="f.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="提交阶段"><el-input v-model="submitStage" placeholder="如 FIRST_REVIEW" /></el-form-item>
      <el-form-item><el-button type="primary" @click="onCreate">登记版本</el-button></el-form-item>
    </el-form>

    <el-table :data="rows" v-loading="loading">
      <el-table-column prop="version_no" label="版本号" width="100" />
      <el-table-column prop="file_id" label="文件ID" width="100" />
      <el-table-column prop="submit_stage" label="提交阶段" width="180" />
      <el-table-column prop="submitted_by" label="提交人ID" width="120" />
      <el-table-column prop="created_at" label="时间" width="220" />
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { listWorkOrders, type WorkOrderItem } from '@/api/workorders'
import { listWorkOrderFiles, type WorkOrderFileItem } from '@/api/files'
import { createReportVersion, listReportVersions, type ReportVersionItem } from '@/api/reportVersions'

const loading = ref(false)
const workOrders = ref<WorkOrderItem[]>([])
const files = ref<WorkOrderFileItem[]>([])
const rows = ref<ReportVersionItem[]>([])
const workOrderId = ref<number>()
const fileId = ref<number>()
const submitStage = ref('FIRST_REVIEW')

async function loadBase() {
  const data = await listWorkOrders()
  workOrders.value = data.items
  workOrderId.value = data.items[0]?.id
  if (workOrderId.value) await onWorkOrderChange()
}

async function onWorkOrderChange() {
  if (!workOrderId.value) return
  loading.value = true
  try {
    const [f, r] = await Promise.all([
      listWorkOrderFiles(workOrderId.value),
      listReportVersions(workOrderId.value)
    ])
    files.value = f.items
    rows.value = r.items
    fileId.value = f.items[0]?.id
  } finally {
    loading.value = false
  }
}

async function onCreate() {
  if (!workOrderId.value || !fileId.value || !submitStage.value) {
    ElMessage.warning('请选择工单、文件并填写阶段')
    return
  }
  await createReportVersion({ work_order_id: workOrderId.value, file_id: fileId.value, submit_stage: submitStage.value })
  ElMessage.success('版本登记成功')
  await onWorkOrderChange()
}

onMounted(loadBase)
</script>
