<template>
  <div class="notification-center-page">
    <div class="header-bar">
      <h1>消息中心</h1>
      <el-button :disabled="!selectedIds.length" @click="batchRead">批量已读</el-button>
    </div>

    <NotificationStatsCards :stats="stats" />

    <el-card shadow="never">
      <el-tabs v-model="activeTab" @tab-change="load">
        <el-tab-pane label="未读" name="unread" />
        <el-tab-pane label="已读" name="read" />
        <el-tab-pane label="我发起的" name="initiated" />
        <el-tab-pane label="抄送我的" name="cc" />
        <el-tab-pane label="全部" name="all" />
      </el-tabs>

      <NotificationFilterBar
        :filters="filters"
        @update:filters="Object.assign(filters, $event)"
        @search="load"
        @reset="resetFilters"
      />

      <NotificationListTable
        :items="items"
        @selection-change="selectedIds = $event"
        @open="openNotification"
        @enter-handle="enterHandle"
      />
    </el-card>

    <NotificationDetailDrawer
      v-model:visible="detailVisible"
      :item="currentItem"
      :timeline-items="timelineItems"
      @goto-target="gotoTarget"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import NotificationDetailDrawer from '@/components/notifications/NotificationDetailDrawer.vue'
import NotificationFilterBar from '@/components/notifications/NotificationFilterBar.vue'
import NotificationListTable from '@/components/notifications/NotificationListTable.vue'
import NotificationStatsCards from '@/components/notifications/NotificationStatsCards.vue'
import {
  batchMarkNotificationRead,
  getNotificationDetail,
  getNotificationStats,
  getNotificationTimeline,
  listMyNotifications,
  markNotificationRead,
  type NotificationItem,
  type NotificationTimelineItem,
} from '@/api/notifications'
import { useNotificationStore } from '@/store/notification'

const router = useRouter()
const route = useRoute()
const notifications = useNotificationStore()
const activeTab = ref<'all' | 'unread' | 'read' | 'initiated' | 'cc'>('unread')
const items = ref<NotificationItem[]>([])
const selectedIds = ref<number[]>([])
const detailVisible = ref(false)
const currentItem = ref<NotificationItem | null>(null)
const timelineItems = ref<NotificationTimelineItem[]>([])
const filters = reactive({
  keyword: '',
  message_type: typeof route.query.message_type === 'string' ? route.query.message_type : '',
  priority: '',
  project_id: typeof route.query.project_id === 'string' ? Number(route.query.project_id) : undefined as number | undefined,
})
const stats = reactive({
  today_new_count: 0,
  unread_count: 0,
  today_reminder_count: 0,
  read_rate: 0,
  avg_process_duration_seconds: 0,
  latest_notification_id: null as number | null,
  server_time: '',
})

let stopRefreshWatch: (() => void) | null = null

async function load() {
  const [listResult, statsResult] = await Promise.all([
    listMyNotifications({
      tab: activeTab.value,
      keyword: filters.keyword || undefined,
      message_type: filters.message_type || undefined,
      priority: filters.priority || undefined,
      project_id: filters.project_id,
      page: 1,
      page_size: 50,
    }),
    getNotificationStats(),
  ])
  items.value = listResult.items
  Object.assign(stats, statsResult)
}

async function openNotification(item: NotificationItem) {
  if (!item.is_read) {
    await markNotificationRead(item.id)
    notifications.applyReadState([item.id])
  }
  const [detail, timeline] = await Promise.all([
    getNotificationDetail(item.id),
    getNotificationTimeline(item.id),
    load(),
  ])
  currentItem.value = { ...detail, is_read: true }
  timelineItems.value = timeline.items
  detailVisible.value = true
}

async function enterHandle(item: NotificationItem) {
  if (item.process_status === 'PROCESSED') {
    ElMessage.warning('该消息对应环节已处理')
    await load()
    return
  }
  if (!item.project_id) {
    return
  }
  if (!item.is_read) {
    await markNotificationRead(item.id)
    notifications.applyReadState([item.id])
  }
  await router.push(`/projects/${item.project_id}/flow`)
}

async function batchRead() {
  if (!selectedIds.value.length) return
  const readIds = [...selectedIds.value]
  await batchMarkNotificationRead(readIds)
  notifications.applyReadState(readIds)
  ElMessage.success('已批量标记为已读')
  selectedIds.value = []
  await load()
}

async function resetFilters() {
  filters.keyword = ''
  filters.message_type = ''
  filters.priority = ''
  filters.project_id = undefined
  await load()
}

function gotoTarget(item: NotificationItem) {
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

onMounted(() => {
  void load()
  stopRefreshWatch = watch(
    () => notifications.listRefreshToken,
    async () => {
      await load()
    },
  )
})

watch(
  () => notifications.stats,
  (value) => {
    Object.assign(stats, value)
  },
  { deep: true },
)

onUnmounted(() => {
  stopRefreshWatch?.()
})
</script>

<style scoped>
.notification-center-page {
  display: grid;
  gap: 16px;
}

.header-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
</style>
