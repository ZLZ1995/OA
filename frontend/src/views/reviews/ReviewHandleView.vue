<template>
  <el-card class="page-card" shadow="never">
    <template #header>审核处理页</template>
    <el-form label-width="110px">
      <el-form-item label="工单">
        <el-select v-model="form.work_order_id" placeholder="选择工单" style="width: 320px" @change="loadRecords">
          <el-option
            v-for="item in workOrderOptions"
            :key="item.id"
            :label="`${item.work_order_no} - ${item.title}`"
            :value="item.id"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="审核轮次">
        <el-select v-model="form.review_round" style="width: 200px">
          <el-option label="一审" value="FIRST" />
          <el-option label="二审" value="SECOND" />
          <el-option label="三审" value="THIRD" />
        </el-select>
      </el-form-item>
      <el-form-item label="审核老师">
        <el-select v-model="form.reviewer_user_id" placeholder="选择审核老师" style="width: 320px">
          <el-option v-for="u in userOptions" :key="u.id" :label="`${u.real_name}(${u.username})`" :value="u.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="审核意见">
        <el-input v-model="form.comment" type="textarea" :rows="4" placeholder="请输入审核意见" />
      </el-form-item>
    </el-form>
    <el-space>
      <el-button type="primary" @click="onSubmit">提交到审核老师</el-button>
      <el-button type="success" @click="onDecision('APPROVE')">通过</el-button>
      <el-button type="danger" plain @click="onDecision('REJECT_RETURN')">退回</el-button>
    </el-space>

    <el-divider>审核记录</el-divider>
    <el-table :data="records" v-loading="loading">
      <el-table-column prop="review_round" label="轮次" width="80" />
      <el-table-column prop="action" label="动作" width="140" />
      <el-table-column prop="reviewer_user_id" label="审核人ID" width="110" />
      <el-table-column prop="comment" label="意见" />
      <el-table-column prop="acted_at" label="时间" width="200" />
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { listWorkOrders, type WorkOrderItem } from '@/api/workorders'
import { listUsers, type UserItem } from '@/api/users'
import { decideReview, listReviews, submitReview, type ReviewRecordItem } from '@/api/reviews'

const loading = ref(false)
const workOrderOptions = ref<WorkOrderItem[]>([])
const userOptions = ref<UserItem[]>([])
const records = ref<ReviewRecordItem[]>([])

const form = reactive({
  work_order_id: undefined as number | undefined,
  review_round: 'FIRST' as 'FIRST' | 'SECOND' | 'THIRD',
  reviewer_user_id: undefined as number | undefined,
  comment: ''
})

async function loadOptions() {
  const [workOrders, users] = await Promise.all([listWorkOrders(), listUsers()])
  workOrderOptions.value = workOrders.items
  userOptions.value = users.items
}

async function loadRecords() {
  if (!form.work_order_id) {
    records.value = []
    return
  }
  loading.value = true
  try {
    const data = await listReviews(form.work_order_id)
    records.value = data.items
  } finally {
    loading.value = false
  }
}

async function onSubmit() {
  if (!form.work_order_id || !form.reviewer_user_id) {
    ElMessage.warning('请选择工单和审核老师')
    return
  }
  await submitReview({
    work_order_id: form.work_order_id,
    review_round: form.review_round,
    reviewer_user_id: form.reviewer_user_id,
    comment: form.comment || undefined
  })
  ElMessage.success('已提交审核')
  await loadRecords()
}

async function onDecision(action: 'APPROVE' | 'REJECT_RETURN') {
  if (!form.work_order_id) {
    ElMessage.warning('请先选择工单')
    return
  }
  await decideReview({
    work_order_id: form.work_order_id,
    review_round: form.review_round,
    action,
    comment: form.comment || undefined
  })
  ElMessage.success(action === 'APPROVE' ? '已通过' : '已退回')
  await loadRecords()
}

onMounted(async () => {
  try {
    await loadOptions()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '审核页数据加载失败')
  }
})
</script>
