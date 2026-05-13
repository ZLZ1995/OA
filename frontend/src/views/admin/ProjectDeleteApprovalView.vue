<template>
  <el-card shadow="never">
    <template #header>项目删除审核</template>

    <el-form inline class="filter-bar">
      <el-form-item label="状态">
        <el-select v-model="statusFilter" clearable @change="load">
          <el-option label="待确认删除" value="PENDING" />
          <el-option label="已驳回" value="REJECTED" />
          <el-option label="已完成" value="APPROVED" />
        </el-select>
      </el-form-item>
    </el-form>

    <el-table :data="rows" v-loading="loading" size="small" class="wide-table">
      <el-table-column prop="project_no" label="项目编号" min-width="132" />
      <el-table-column prop="project_name" label="项目名称" min-width="160" show-overflow-tooltip />
      <el-table-column prop="client_name" label="客户名称" min-width="160" show-overflow-tooltip />
      <el-table-column prop="current_step" label="当前步骤" min-width="110" />
      <el-table-column prop="requester_user_name" label="申请人" min-width="110" />
      <el-table-column prop="approver_user_name" label="共同认证管理员" min-width="140" />
      <el-table-column prop="requested_at" label="申请时间" min-width="170" />
      <el-table-column prop="reason" label="删除原因" min-width="220" show-overflow-tooltip />
      <el-table-column label="当前状态" min-width="110">
        <template #default="{ row }">{{ statusText(row.status) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="220">
        <template #default="{ row }">
          <el-button v-if="row.status === 'PENDING'" link type="danger" @click="approve(row)">确认删除</el-button>
          <el-button v-if="row.status === 'PENDING'" link type="warning" @click="reject(row)">驳回删除</el-button>
          <span v-else>-</span>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  approveProjectDeleteRequest,
  listProjectDeleteRequests,
  rejectProjectDeleteRequest,
  type ProjectDeleteRequestItem
} from '@/api/projectDeleteRequests'

const loading = ref(false)
const rows = ref<ProjectDeleteRequestItem[]>([])
const statusFilter = ref<string>()

function statusText(status: string) {
  if (status === 'PENDING') return '待确认删除'
  if (status === 'REJECTED') return '已驳回'
  if (status === 'APPROVED') return '已完成'
  return status
}

async function load() {
  loading.value = true
  try {
    rows.value = (await listProjectDeleteRequests(statusFilter.value)).items
  } finally {
    loading.value = false
  }
}

async function approve(row: ProjectDeleteRequestItem) {
  await ElMessageBox.confirm(
    '将删除项目、工单、流程记录、文件、审核记录等全部关联数据，且不可恢复。确认删除吗？',
    '确认删除项目',
    {
      confirmButtonText: '确认删除',
      cancelButtonText: '取消',
      type: 'warning'
    }
  )
  await approveProjectDeleteRequest(row.id)
  ElMessage.success('已确认删除并完成删除')
  await load()
}

async function reject(row: ProjectDeleteRequestItem) {
  await rejectProjectDeleteRequest(row.id)
  ElMessage.success('删除申请已驳回')
  await load()
}

onMounted(load)
</script>

<style scoped>
.filter-bar {
  margin-bottom: 12px;
}

.wide-table {
  width: 100%;
}
</style>
