<template>
  <el-drawer :model-value="modelValue" title="催办记录" size="42%" @close="$emit('update:modelValue', false)">
    <el-empty v-if="!items.length" description="暂无催办记录" />
    <div v-else class="history-list">
      <div v-for="item in items" :key="item.reminder_event_id" class="history-item">
        <div class="history-head">
          <strong>{{ item.initiator_user_name || '未知发起人' }} -> {{ item.current_handler_user_name || '未知处理人' }}</strong>
          <span>{{ formatDate(item.created_at) }}</span>
        </div>
        <p>状态：{{ item.current_status }}｜当天第 {{ item.day_remind_seq }} 次｜{{ item.primary_read_status === 'READ' ? '已读' : '未读' }}</p>
        <p v-if="item.comment">说明：{{ item.comment }}</p>
      </div>
    </div>
  </el-drawer>
</template>

<script setup lang="ts">
import type { ReminderHistoryItem } from '@/api/reminders'

defineProps<{
  modelValue: boolean
  items: ReminderHistoryItem[]
}>()

defineEmits<{
  (e: 'update:modelValue', value: boolean): void
}>()

function formatDate(value: string) {
  return value ? new Date(value).toLocaleString() : ''
}
</script>

<style scoped>
.history-list {
  display: grid;
  gap: 12px;
}

.history-item {
  padding: 12px;
  border: 1px solid var(--zq-border);
  border-radius: 10px;
}

.history-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.history-item p {
  margin: 8px 0 0;
  color: #475569;
}
</style>
