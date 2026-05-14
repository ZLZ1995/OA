<template>
  <el-empty v-if="!items.length" description="暂无时间线数据" />
  <div v-else class="timeline-list">
    <div v-for="item in items" :key="`${item.event_type}-${item.created_at}-${item.title}`" class="timeline-item">
      <div class="timeline-head">
        <strong>{{ item.title }}</strong>
        <span>{{ formatDate(item.created_at) }}</span>
      </div>
      <p>{{ item.operator_user_name || '系统' }}<span v-if="item.status"> · {{ item.status }}</span></p>
      <p v-if="item.remark">{{ item.remark }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { NotificationTimelineItem } from '@/api/notifications'

defineProps<{ items: NotificationTimelineItem[] }>()

function formatDate(value: string) {
  return value ? new Date(value).toLocaleString() : ''
}
</script>

<style scoped>
.timeline-list {
  display: grid;
  gap: 10px;
}

.timeline-item {
  padding: 12px;
  border: 1px solid var(--zq-border);
  border-radius: 8px;
  background: #fff;
}

.timeline-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.timeline-item p {
  margin: 12px 0 0;
  white-space: pre-wrap;
  color: #475569;
}
</style>
