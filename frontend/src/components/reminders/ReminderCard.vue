<template>
  <el-card shadow="never" class="reminder-card">
    <template #header>
      <div class="card-header">
        <span>催办提醒</span>
        <el-button link type="primary" @click="historyVisible = true">查看记录</el-button>
      </div>
    </template>
    <el-descriptions :column="1" border size="small">
      <el-descriptions-item label="当前处理人">{{ eligibility?.current_handler_name || '暂无' }}</el-descriptions-item>
      <el-descriptions-item label="当前状态">{{ flowStatus || '暂无' }}</el-descriptions-item>
      <el-descriptions-item label="今日催办次数">{{ eligibility?.today_remind_count ?? 0 }}</el-descriptions-item>
    </el-descriptions>
    <p class="reminder-tip" v-if="eligibility?.can_remind">当前满足催办条件，可以发送催办消息。</p>
    <p class="reminder-tip" v-else>{{ eligibility?.reason_message || '正在计算催办资格' }}</p>
    <div class="actions">
      <el-button type="primary" @click="onOpenDialog">催办</el-button>
      <el-button @click="load">刷新</el-button>
    </div>
  </el-card>

  <ReminderDialog
    v-model="dialogVisible"
    v-model:comment="comment"
    :submitting="submitting"
    @submit="submit"
  />
  <ReminderHistoryDrawer v-model="historyVisible" :items="historyItems" />
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { createReminder, getReminderEligibility, listWorkOrderReminders, type ReminderEligibilityData, type ReminderHistoryItem } from '@/api/reminders'
import ReminderDialog from './ReminderDialog.vue'
import ReminderHistoryDrawer from './ReminderHistoryDrawer.vue'

const props = defineProps<{
  workOrderId?: number
  flowStatus?: string | null
}>()

const eligibility = ref<ReminderEligibilityData | null>(null)
const historyItems = ref<ReminderHistoryItem[]>([])
const dialogVisible = ref(false)
const historyVisible = ref(false)
const comment = ref('')
const submitting = ref(false)

async function load() {
  if (!props.workOrderId) return
  eligibility.value = await getReminderEligibility(props.workOrderId)
  historyItems.value = (await listWorkOrderReminders(props.workOrderId)).items
}

function onOpenDialog() {
  if (!eligibility.value?.can_remind) {
    ElMessage.warning(eligibility.value?.reason_message || '当前暂不可催办')
    return
  }
  dialogVisible.value = true
}

async function submit() {
  if (!props.workOrderId) return
  submitting.value = true
  try {
    const result = await createReminder({ work_order_id: props.workOrderId, comment: comment.value.trim() || undefined })
    ElMessage.success(result.message)
    dialogVisible.value = false
    comment.value = ''
    await load()
  } finally {
    submitting.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.reminder-card {
  margin-top: 12px;
}

.card-header,
.actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.reminder-tip {
  margin: 12px 0;
  color: #475569;
}
</style>
