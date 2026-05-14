<template>
  <div class="notification-stats">
    <el-card class="stats-item" shadow="never">
      <strong>{{ stats.today_new_count }}</strong>
      <span>今日新增</span>
    </el-card>
    <el-card class="stats-item" shadow="never">
      <strong>{{ stats.unread_count }}</strong>
      <span>未读消息</span>
    </el-card>
    <el-card class="stats-item" shadow="never">
      <strong>{{ stats.today_reminder_count }}</strong>
      <span>今日催办</span>
    </el-card>
    <el-card class="stats-item" shadow="never">
      <strong>{{ stats.read_rate }}%</strong>
      <span>已读率</span>
    </el-card>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  stats: {
    today_new_count: number
    unread_count: number
    today_reminder_count: number
    read_rate: number
    avg_process_duration_seconds: number
  }
}>()
</script>

<style scoped>
.notification-stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.stats-item {
  text-align: center;
}

.stats-item strong,
.stats-item span {
  display: block;
}

.stats-item strong {
  font-size: 24px;
  color: var(--zq-primary);
}

.stats-item span {
  margin-top: 6px;
  color: #64748b;
}

@media (max-width: 900px) {
  .notification-stats {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
