<template>
  <el-drawer :model-value="visible" title="消息详情" size="42%" @update:model-value="$emit('update:visible', $event)">
    <template v-if="item">
      <div class="detail-card">
        <div class="detail-head">
          <strong>{{ item.title }}</strong>
          <span>{{ formatDate(item.created_at) }}</span>
        </div>
        <p>{{ item.content }}</p>

        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="消息类型">{{ item.message_type === 'REMINDER' ? '催办消息' : '系统通知' }}</el-descriptions-item>
          <el-descriptions-item label="优先级">{{ priorityText(item.priority) }}</el-descriptions-item>
          <el-descriptions-item label="发起人">{{ item.sender_user_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="接收人">{{ item.receiver_user_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="接收类型">{{ item.cc_flag ? '抄送' : '主接收' }}</el-descriptions-item>
          <el-descriptions-item label="处理状态">{{ processText(item.process_status, item.is_read) }}</el-descriptions-item>
          <el-descriptions-item label="项目">{{ item.project_name || item.project_code || item.project_id || '-' }}</el-descriptions-item>
          <el-descriptions-item label="客户">{{ item.client_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="工单">{{ item.work_order_no || item.work_order_title || item.work_order_id || '-' }}</el-descriptions-item>
          <el-descriptions-item label="当前节点">{{ item.current_status || '-' }}</el-descriptions-item>
          <el-descriptions-item label="当前处理人">{{ item.current_handler_user_name || '-' }}</el-descriptions-item>
        </el-descriptions>

        <div class="detail-actions">
          <el-button link type="primary" @click="$emit('goto-target', item)">进入业务</el-button>
        </div>
      </div>

      <el-divider>同工单时间线</el-divider>
      <NotificationTimeline :items="timelineItems" />
    </template>
  </el-drawer>
</template>

<script setup lang="ts">
import type { NotificationItem, NotificationTimelineItem } from '@/api/notifications'
import NotificationTimeline from './NotificationTimeline.vue'

defineProps<{
  visible: boolean
  item: NotificationItem | null
  timelineItems: NotificationTimelineItem[]
}>()

defineEmits<{
  (event: 'update:visible', value: boolean): void
  (event: 'goto-target', value: NotificationItem): void
}>()

function formatDate(value: string) {
  return value ? new Date(value).toLocaleString() : ''
}

function priorityText(priority: string) {
  if (priority === 'IMPORTANT') return '重要'
  if (priority === 'URGENT') return '紧急'
  return '普通'
}

function processText(processStatus: string, isRead: boolean) {
  if (processStatus === 'PROCESSED') return '已处理'
  if (processStatus === 'READ' || isRead) return '已读未处理'
  return '待查看'
}
</script>

<style scoped>
.detail-card {
  padding: 12px;
  border: 1px solid var(--zq-border);
  border-radius: 8px;
  background: #fff;
}

.detail-head,
.detail-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.detail-card p {
  margin: 12px 0;
  white-space: pre-wrap;
  color: #475569;
}

.detail-actions {
  margin-top: 12px;
}
</style>
