<template>
  <el-card class="page-card" shadow="never">
    <template #header>消息中心</template>
    <el-empty v-if="!items.length" description="暂无消息" />
    <div v-else class="notification-list">
      <div v-for="item in items" :key="item.id" class="notification-item" :class="{ unread: !item.is_read }">
        <div class="notification-head">
          <strong>{{ item.title }}</strong>
          <span>{{ formatDate(item.created_at) }}</span>
        </div>
        <p>{{ item.content }}</p>
        <div class="notification-actions">
          <el-tag size="small" :type="item.is_read ? 'info' : 'danger'">{{ item.is_read ? '已读' : '未读' }}</el-tag>
          <el-button link type="primary" @click="openNotification(item)">查看</el-button>
        </div>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { listMyNotifications, markNotificationRead, type NotificationItem } from '@/api/notifications'

const router = useRouter()
const items = ref<NotificationItem[]>([])

function formatDate(value: string) {
  return value ? new Date(value).toLocaleString() : ''
}

async function load() {
  items.value = (await listMyNotifications()).items
}

async function openNotification(item: NotificationItem) {
  if (!item.is_read) {
    await markNotificationRead(item.id)
  }
  await load()
  if (item.link_type === 'PROJECT' && item.link_target_id) {
    router.push(`/projects/${item.link_target_id}/flow`)
    return
  }
  if (item.link_type === 'WORK_ORDER' && item.link_target_id) {
    router.push(`/workorders/${item.link_target_id}`)
    return
  }
  ElMessage.info('该消息暂无可跳转目标')
}

onMounted(load)
</script>

<style scoped>
.notification-list {
  display: grid;
  gap: 12px;
}

.notification-item {
  padding: 14px;
  border: 1px solid var(--zq-border);
  border-radius: 10px;
  background: #fff;
}

.notification-item.unread {
  border-color: #f59e0b;
  background: #fffaf0;
}

.notification-head,
.notification-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.notification-item p {
  margin: 10px 0;
  white-space: pre-wrap;
  color: #475569;
}
</style>
