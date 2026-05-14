<template>
  <el-card shadow="never">
    <template #header>
      <div class="header-row">
        <span>问题反馈</span>
        <el-button type="success" @click="onExport">导出Excel</el-button>
      </div>
    </template>

    <el-table :data="rows" v-loading="loading" size="small">
      <el-table-column prop="submitter_user_name" label="提交人" min-width="120" />
      <el-table-column prop="created_at" label="提交时间" min-width="180" />
      <el-table-column prop="status" label="状态" min-width="120">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)">{{ statusText(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="查看详情" min-width="120">
        <template #default="{ row }">
          <el-button link type="primary" @click="openDetail(row)">查看详情</el-button>
        </template>
      </el-table-column>
      <el-table-column label="操作" min-width="180" fixed="right">
        <template #default="{ row }">
          <el-space v-if="row.status === 'PENDING'" wrap>
            <el-button link type="success" @click="resolve(row)">已处理</el-button>
            <el-button link type="warning" @click="openSuspend(row)">挂起</el-button>
          </el-space>
          <span v-else>-</span>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="detailVisible" title="问题反馈详情" width="560px">
      <el-descriptions v-if="current" :column="1" border>
        <el-descriptions-item label="提交人姓名">{{ current.submitter_user_name }}</el-descriptions-item>
        <el-descriptions-item label="提交账号">{{ current.submitter_username }}</el-descriptions-item>
        <el-descriptions-item label="提交时间">{{ current.created_at }}</el-descriptions-item>
        <el-descriptions-item label="项目编号">{{ current.project_no }}</el-descriptions-item>
        <el-descriptions-item label="流程环节">{{ current.process_step }}</el-descriptions-item>
        <el-descriptions-item label="问题详情">
          <div class="detail-text">{{ current.detail }}</div>
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  exportTechSupportFeedbacksExcel,
  listIssueFeedbacks,
  resolveIssueFeedback,
  suspendIssueFeedback,
  type IssueFeedbackItem,
  type IssueFeedbackStatus
} from '@/api/issueFeedbacks'

const rows = ref<IssueFeedbackItem[]>([])
const loading = ref(false)
const detailVisible = ref(false)
const current = ref<IssueFeedbackItem>()

function statusText(value: IssueFeedbackStatus) {
  return ({ PENDING: '待处理', RESOLVED: '已处理', TECH_SUPPORT: '需技术支持' } as Record<IssueFeedbackStatus, string>)[value] || value
}

function statusType(value: IssueFeedbackStatus) {
  return ({ PENDING: 'warning', RESOLVED: 'success', TECH_SUPPORT: 'danger' } as Record<IssueFeedbackStatus, 'warning' | 'success' | 'danger'>)[value]
}

async function load() {
  loading.value = true
  try {
    rows.value = (await listIssueFeedbacks()).items
  } finally {
    loading.value = false
  }
}

function openDetail(row: IssueFeedbackItem) {
  current.value = row
  detailVisible.value = true
}

async function resolve(row: IssueFeedbackItem) {
  await resolveIssueFeedback(row.id)
  ElMessage.success('已标记处理完成')
  await load()
}

async function openSuspend(row: IssueFeedbackItem) {
  const result = await ElMessageBox.prompt('请输入挂起说明（选填）', '确认挂起', {
    confirmButtonText: '挂起',
    cancelButtonText: '取消',
    inputType: 'textarea',
    type: 'warning'
  })
  await suspendIssueFeedback(row.id, result.value)
  ElMessage.success('已转入需技术支持')
  await load()
}

async function onExport() {
  await exportTechSupportFeedbacksExcel()
  ElMessage.success('Excel已生成')
}

onMounted(load)
</script>

<style scoped>
.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.detail-text {
  white-space: pre-wrap;
  line-height: 1.7;
}
</style>
