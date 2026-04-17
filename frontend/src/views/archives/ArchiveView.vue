<template>
  <el-card class="page-card" shadow="never">
    <template #header>归档登记</template>
    <el-form inline>
      <el-form-item label="工单ID"><el-input-number v-model="form.work_order_id" :min="1" /></el-form-item>
      <el-form-item label="档案号"><el-input v-model="form.archive_no" /></el-form-item>
      <el-form-item label="位置"><el-input v-model="form.archive_location" /></el-form-item>
      <el-form-item><el-button type="primary" @click="onCreate">新增归档</el-button></el-form-item>
    </el-form>

    <el-table :data="rows" v-loading="loading">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="work_order_id" label="工单ID" width="100" />
      <el-table-column prop="archive_no" label="档案号" />
      <el-table-column prop="archive_location" label="存放位置" />
      <el-table-column prop="archive_at" label="归档时间" width="220" />
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { createArchive, listArchives, type ArchiveItem } from '@/api/archives'

const loading = ref(false)
const rows = ref<ArchiveItem[]>([])
const form = reactive({
  work_order_id: 1,
  archive_no: '',
  archive_location: '',
  archive_at: new Date().toISOString(),
  remark: ''
})

async function load() {
  loading.value = true
  try {
    rows.value = (await listArchives()).items
  } finally {
    loading.value = false
  }
}

async function onCreate() {
  if (!form.archive_no || !form.work_order_id) {
    ElMessage.warning('请填写工单ID和档案号')
    return
  }
  await createArchive(form)
  ElMessage.success('归档成功')
  form.archive_no = ''
  form.archive_location = ''
  form.remark = ''
  await load()
}

onMounted(load)
</script>
