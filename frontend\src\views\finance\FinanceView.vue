<template>
  <el-card class="page-card" shadow="never">
    <template #header>财务发票登记</template>
    <el-form inline>
      <el-form-item label="工单ID"><el-input-number v-model="form.work_order_id" :min="1" /></el-form-item>
      <el-form-item label="发票号"><el-input v-model="form.invoice_no" /></el-form-item>
      <el-form-item label="金额"><el-input-number v-model="form.amount" :min="0" :precision="2" /></el-form-item>
      <el-form-item><el-button type="primary" @click="onCreate">新增发票</el-button></el-form-item>
    </el-form>
    <el-table :data="rows" v-loading="loading">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="work_order_id" label="工单ID" width="100" />
      <el-table-column prop="invoice_no" label="发票号" />
      <el-table-column prop="amount" label="金额" width="120" />
      <el-table-column prop="status" label="状态" width="140" />
      <el-table-column label="操作" width="140">
        <template #default="{ row }">
          <el-button size="small" @click="markDone(row.id)">标记已开票</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { createInvoice, listInvoices, updateInvoice, type InvoiceItem } from '@/api/finance'

const loading = ref(false)
const rows = ref<InvoiceItem[]>([])
const form = reactive({ work_order_id: 1, invoice_no: '', amount: 0 })

async function load() {
  loading.value = true
  try {
    rows.value = (await listInvoices()).items
  } finally {
    loading.value = false
  }
}

async function onCreate() {
  if (!form.invoice_no || !form.work_order_id) {
    ElMessage.warning('请填写工单ID和发票号')
    return
  }
  await createInvoice({ ...form, status: 'PENDING' })
  ElMessage.success('创建成功')
  form.invoice_no = ''
  form.amount = 0
  await load()
}

async function markDone(id: number) {
  await updateInvoice(id, { status: 'ISSUED' })
  ElMessage.success('已标记为已开票')
  await load()
}

onMounted(load)
</script>
