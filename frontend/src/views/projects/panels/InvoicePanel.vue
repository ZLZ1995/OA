<template>
  <el-alert v-if="!canOperate" type="info" :closable="false" title="仅项目成员或财务可操作，当前仅可查看。" show-icon style="margin-bottom:12px"/>
  <el-form inline>
    <el-form-item label="发票号"><el-input v-model="invoiceNo" :disabled="!canOperate" /></el-form-item>
    <el-form-item label="金额"><el-input-number v-model="amount" :min="0" :precision="2" :disabled="!canOperate" /></el-form-item>
    <el-form-item><el-button type="primary" :disabled="!canOperate || !workOrderId" @click="onCreate">提交开票</el-button></el-form-item>
  </el-form>
  <el-table :data="rows" v-loading="loading">
    <el-table-column prop="invoice_no" label="发票号" />
    <el-table-column prop="amount" label="金额" width="120" />
    <el-table-column prop="status" label="状态" width="120" />
    <el-table-column label="操作" width="140">
      <template #default="{ row }">
        <el-button size="small" :disabled="!canFinance" @click="markIssued(row.id)">标记已开票</el-button>
      </template>
    </el-table-column>
  </el-table>
  <el-alert type="warning" :closable="false" title="缺失接口：电子发票文件上传/下载接口未发现，当前仅支持开票登记与状态更新。" show-icon style="margin-top:12px" />
</template>
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { createInvoice, listInvoices, updateInvoice, type InvoiceItem } from '@/api/finance'
const props = defineProps<{ workOrderId?: number; canOperate: boolean; userRoles: string[] }>()
const emit = defineEmits<{ (e: 'changed'): void }>()
const rows = ref<InvoiceItem[]>([])
const loading = ref(false)
const invoiceNo = ref('')
const amount = ref(0)
const canFinance = computed(() => props.userRoles.some(r => ['FINANCE','ADMIN'].includes(r)))

async function load() {
  loading.value = true
  try {
    const all = (await listInvoices()).items
    rows.value = props.workOrderId ? all.filter(i => i.work_order_id === props.workOrderId) : []
  } finally { loading.value = false }
}
async function onCreate() {
  if (!props.workOrderId || !invoiceNo.value) return ElMessage.warning('请填写发票号')
  await createInvoice({ work_order_id: props.workOrderId, invoice_no: invoiceNo.value, amount: amount.value, status: 'PENDING' })
  ElMessage.success('开票申请已提交'); invoiceNo.value=''; amount.value=0; await load(); emit('changed')
}
async function markIssued(id: number) { await updateInvoice(id, { status: 'ISSUED' }); ElMessage.success('已标记已开票'); await load(); emit('changed') }
onMounted(load)
</script>
