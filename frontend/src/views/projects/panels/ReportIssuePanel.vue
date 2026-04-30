<template>
  <el-alert v-if="!canOperate" type="info" :closable="false" title="仅文印室人员可办理该节点。" show-icon style="margin-bottom:12px"/>
  <el-alert v-if="!workOrderId" type="warning" :closable="false" title="当前项目暂无关联工单，无法办理报告出具。" show-icon style="margin-bottom:12px"/>
  <template v-if="workOrderId">
    <el-form label-width="120px">
      <el-form-item label="正式合同编号"><el-input v-model="contractNo" :disabled="!canOperate" /></el-form-item>
      <el-form-item label="纸质报告编号"><el-input v-model="paperReportNo" :disabled="!canOperate" /></el-form-item>
      <el-form-item label="出具数量"><el-input-number v-model="copyCount" :min="1" :disabled="!canOperate" /></el-form-item>
      <el-form-item label="备注"><el-input v-model="remark" type="textarea" :rows="3" :disabled="!canOperate" /></el-form-item>
      <el-form-item>
        <el-button type="primary" :disabled="!canOperate" @click="issueContract">出具正式合同</el-button>
        <el-button type="success" :disabled="!canOperate" @click="issueReport">登记纸质报告出具</el-button>
      </el-form-item>
    </el-form>
  </template>
  <el-alert type="warning" :closable="false" title="缺失接口：报告扫描件上传/查询接口未发现，当前无法实装该能力。" show-icon />
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { issueOfficialContract, issuePaperReport } from '@/api/printRoom'

const props = defineProps<{ workOrderId?: number; canOperate: boolean }>()
const emit = defineEmits<{ (e: 'changed'): void }>()
const contractNo = ref('')
const paperReportNo = ref('')
const copyCount = ref(1)
const remark = ref('')

async function issueContract() {
  if (!props.workOrderId || !contractNo.value) return ElMessage.warning('请填写正式合同编号')
  await issueOfficialContract({ work_order_id: props.workOrderId, contract_no: contractNo.value, remark: remark.value || undefined })
  ElMessage.success('正式合同出具成功'); emit('changed')
}
async function issueReport() {
  if (!props.workOrderId || !paperReportNo.value) return ElMessage.warning('请填写纸质报告编号')
  await issuePaperReport({ work_order_id: props.workOrderId, paper_report_no: paperReportNo.value, copy_count: copyCount.value, remark: remark.value || undefined })
  ElMessage.success('纸质报告登记成功'); emit('changed')
}
</script>
