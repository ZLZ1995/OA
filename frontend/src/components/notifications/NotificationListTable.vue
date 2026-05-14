<template>
  <el-empty v-if="!items.length" description="暂无消息" />
  <el-table v-else :data="items" @selection-change="onSelectionChange">
    <el-table-column type="selection" width="48" />
    <el-table-column prop="title" label="标题" min-width="220" show-overflow-tooltip />
    <el-table-column label="类型" width="120">
      <template #default="{ row }">
        <el-tag size="small" :type="row.message_type === 'REMINDER' ? 'warning' : 'info'">
          {{ row.message_type === 'REMINDER' ? '催办消息' : '系统通知' }}
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column label="优先级" width="100">
      <template #default="{ row }">
        <el-tag size="small" :type="priorityTagType(row.priority)">
          {{ priorityText(row.priority) }}
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column label="项目" min-width="160" show-overflow-tooltip>
      <template #default="{ row }">
        {{ row.project_name || row.project_code || row.project_id || '-' }}
      </template>
    </el-table-column>
    <el-table-column label="工单" min-width="150" show-overflow-tooltip>
      <template #default="{ row }">
        {{ row.work_order_no || row.work_order_title || row.work_order_id || '-' }}
      </template>
    </el-table-column>
    <el-table-column label="处理状态" width="110">
      <template #default="{ row }">
        <el-tag size="small" :type="processTagType(row.process_status, row.is_read)">
          {{ processText(row.process_status, row.is_read) }}
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column label="接收类型" width="100">
      <template #default="{ row }">
        <el-tag size="small" :type="row.cc_flag ? 'info' : 'success'">
          {{ row.cc_flag ? '抄送' : '主接收' }}
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column label="时间" width="180">
      <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
    </el-table-column>
    <el-table-column label="已读" width="90">
      <template #default="{ row }">
        <el-tag size="small" :type="row.is_read ? 'info' : 'danger'">
          {{ row.is_read ? '已读' : '未读' }}
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column label="操作" width="120">
      <template #default="{ row }">
        <el-button link type="primary" @click="$emit('open', row)">查看</el-button>
      </template>
    </el-table-column>
  </el-table>
</template>

<script setup lang="ts">
import type { NotificationItem } from '@/api/notifications'

defineProps<{ items: NotificationItem[] }>()

const emit = defineEmits<{
  (event: 'selection-change', value: number[]): void
  (event: 'open', value: NotificationItem): void
}>()

function formatDate(value: string) {
  return value ? new Date(value).toLocaleString() : ''
}

function priorityText(priority: string) {
  if (priority === 'IMPORTANT') return '重要'
  if (priority === 'URGENT') return '紧急'
  return '普通'
}

function priorityTagType(priority: string) {
  if (priority === 'IMPORTANT') return 'warning'
  if (priority === 'URGENT') return 'danger'
  return 'info'
}

function processText(processStatus: string, isRead: boolean) {
  if (processStatus === 'PROCESSED') return '已处理'
  if (processStatus === 'READ' || isRead) return '已读未处理'
  return '待查看'
}

function processTagType(processStatus: string, isRead: boolean) {
  if (processStatus === 'PROCESSED') return 'success'
  if (processStatus === 'READ' || isRead) return 'warning'
  return 'danger'
}

function onSelectionChange(rows: NotificationItem[]) {
  emit('selection-change', rows.map(row => row.id))
}
</script>
