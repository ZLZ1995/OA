<template>
  <el-button v-if="eligible" @click="open">撤回合同并重新审核</el-button>
  <el-dialog v-model="visible" title="撤回合同并重新审核" width="min(520px, 92vw)"
    destroy-on-close :close-on-click-modal="false" :close-on-press-escape="!saving" :show-close="!saving">
    <p>当前合同：{{ snapshot?.name }}</p>
    <p>原合同审核人：{{ snapshot?.reviewer }}</p>
    <p v-if="snapshot?.printStatus === 'WAIT_PRINT_ROOM_PROCESS'">提交成功后将通知文印室停止办理旧版。</p>
    <label>新版合同 <input type="file" :disabled="saving" @change="selectFile" /></label>
    <template #footer>
      <el-button :disabled="saving" @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="saving" :disabled="!file" @click="submit">上传并重新送审</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { isAxiosError } from 'axios'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/store/auth'
import { reviseApprovedContract } from '@/api/contractReviews'
import type { ProjectFlowData } from '@/api/projectFlow'

const props = defineProps<{ flowInfo?: ProjectFlowData; stamped: boolean }>()
const emit = defineEmits<{ (e: 'changed'): void }>()
const auth = useAuthStore()
const approval = computed(() => props.flowInfo?.contract_review_records.find(r =>
  ['APPROVE_CONTRACT', 'APPROVE_AND_TRANSFER_PRINT_ROOM'].includes(r.action_type)))
const eligible = computed(() => !!auth.user?.id && auth.user.id === props.flowInfo?.project.project_leader_id &&
  ['CONTRACT_APPROVED', 'WAIT_PRINT_ROOM_PROCESS'].includes(props.flowInfo?.contract_review_status || '') &&
  ['', 'WAIT_PRINT_ROOM_PROCESS'].includes(props.flowInfo?.contract_print_room_status || '') && !props.stamped)
const snapshot = ref<{ order: number; approval: number; name: string; reviewer: string; printStatus: string }>()
const visible = ref(false)
const saving = ref(false)
const file = ref<File>()

function open() {
  const r = approval.value
  if (!r?.contract_file || !props.flowInfo?.current_work_order_id)
    return ElMessage.warning('无法匹配已通过合同的文件或审核记录，请核对项目资料')
  snapshot.value = { order: props.flowInfo.current_work_order_id, approval: r.id,
    name: r.contract_file.origin_file_name, reviewer: r.reviewer_user_name || String(r.reviewer_user_id),
    printStatus: props.flowInfo.contract_print_room_status || 'NONE' }
  file.value = undefined
  visible.value = true
}
function selectFile(event: Event) {
  file.value = (event.target as HTMLInputElement).files?.[0]
}
async function submit() {
  const current = snapshot.value
  if (!current || !file.value || saving.value) return
  saving.value = true
  try {
    await reviseApprovedContract(current.order, current.approval, current.printStatus, file.value)
    visible.value = false
    ElMessage.success('新版合同已送回原审核人')
    emit('changed')
  } catch (error) {
    // Refresh state before allowing a retry after an ambiguous network response.
    visible.value = false
    emit('changed')
    const detail = isAxiosError(error) && error.response?.data?.detail
    ElMessage.error(typeof detail === 'string' ? detail : '提交结果暂未确认，请刷新查看当前合同版本。')
  } finally {
    saving.value = false
  }
}
</script>
