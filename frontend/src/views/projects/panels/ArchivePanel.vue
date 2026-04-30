<template>
  <el-alert v-if="!canOperate" type="info" :closable="false" title="当前账号无归档操作权限，仅可查看。" show-icon style="margin-bottom:12px"/>
  <el-form inline>
    <el-form-item label="档案号"><el-input v-model="archiveNo" :disabled="!canOperate" /></el-form-item>
    <el-form-item label="存放位置"><el-input v-model="archiveLocation" :disabled="!canOperate" /></el-form-item>
    <el-form-item><el-button type="primary" :disabled="!canOperate || !workOrderId" @click="onCreate">确认归档</el-button></el-form-item>
  </el-form>
  <el-table :data="rows" v-loading="loading">
    <el-table-column prop="archive_no" label="档案号" />
    <el-table-column prop="archive_location" label="存放位置" />
    <el-table-column prop="archive_at" label="归档时间" width="200" />
  </el-table>
  <el-alert type="warning" :closable="false" title="缺失接口：归档材料上传/下载接口未发现，当前仅支持归档登记。" show-icon style="margin-top:12px" />
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { createArchive, listArchives, type ArchiveItem } from '@/api/archives'
const props = defineProps<{ workOrderId?: number; canOperate: boolean }>()
const emit = defineEmits<{ (e: 'changed'): void }>()
const rows = ref<ArchiveItem[]>([])
const loading = ref(false)
const archiveNo = ref('')
const archiveLocation = ref('')

async function load() {
  loading.value = true
  try {
    const all = (await listArchives()).items
    rows.value = props.workOrderId ? all.filter(a => a.work_order_id === props.workOrderId) : []
  } finally { loading.value = false }
}
async function onCreate() {
  if (!props.workOrderId || !archiveNo.value) return ElMessage.warning('请填写档案号')
  await createArchive({ work_order_id: props.workOrderId, archive_no: archiveNo.value, archive_location: archiveLocation.value || undefined, archive_at: new Date().toISOString() })
  ElMessage.success('归档成功'); archiveNo.value=''; archiveLocation.value=''; await load(); emit('changed')
}
onMounted(load)
</script>
