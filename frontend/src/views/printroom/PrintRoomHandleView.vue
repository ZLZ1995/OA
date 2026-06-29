<template>
  <el-card class="page-card" shadow="never">
    <template #header>
      <div class="page-header">
        <div>
          <h2>文印室处理页</h2>
          <p>优先完成工单选择、编号录入和纸质出具登记。</p>
        </div>
      </div>
    </template>

    <div class="printroom-layout">
      <div class="printroom-main">
        <el-form label-width="130px">
          <el-form-item label="工单">
            <el-select v-model="form.work_order_id" placeholder="选择工单" style="width: 320px">
              <el-option
                v-for="item in workOrderOptions"
                :key="item.id"
                :label="`${item.work_order_no} - ${item.title}`"
                :value="item.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="正式合同编号">
            <el-input v-model="form.contract_no" placeholder="例如 HT-2026-001" />
          </el-form-item>
          <el-form-item label="纸质报告编号">
            <el-input v-model="form.paper_report_no" placeholder="请输入编号" />
          </el-form-item>
          <el-form-item label="份数">
            <el-input-number v-model="form.copy_count" :min="1" :max="99" />
          </el-form-item>
          <el-form-item label="备注">
            <el-input v-model="form.remark" type="textarea" :rows="3" />
          </el-form-item>
          <el-form-item>
            <el-space wrap>
              <el-button type="primary" @click="onIssueOfficialContract">出具正式合同</el-button>
              <el-button type="success" @click="onIssuePaperReport">登记纸质报告出具</el-button>
            </el-space>
          </el-form-item>
        </el-form>
      </div>

      <aside class="printroom-side">
        <div class="printroom-note-card">
          <div class="printroom-note-title">当前环节所需文件要求</div>
          <ol class="printroom-note-list">
            <li>先确认已选对工单，再录入正式合同编号与纸质报告编号。</li>
            <li>出具前核对份数、备注以及纸质出具信息是否完整。</li>
            <li>处理记录统一在底部查看，避免边录入边翻历史。</li>
          </ol>
        </div>
      </aside>
    </div>

    <el-divider>最近出具记录</el-divider>
    <el-table :data="recentRecords">
      <el-table-column prop="work_order_id" label="工单ID" width="90" />
      <el-table-column prop="paper_report_no" label="纸质报告编号" />
      <el-table-column prop="copy_count" label="份数" width="90" />
      <el-table-column prop="printed_at" label="出具时间" width="200" />
      <el-table-column prop="remark" label="备注" />
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { listWorkOrders, type WorkOrderItem } from '@/api/workorders'
import { issueOfficialContract, issuePaperReport, type PrintRoomRecordItem } from '@/api/printRoom'

const workOrderOptions = ref<WorkOrderItem[]>([])
const recentRecords = ref<PrintRoomRecordItem[]>([])

const form = reactive({
  work_order_id: undefined as number | undefined,
  contract_no: '',
  paper_report_no: '',
  copy_count: 1,
  remark: ''
})

function ensureWorkOrderSelected(): boolean {
  if (!form.work_order_id) {
    ElMessage.warning('请先选择工单')
    return false
  }
  return true
}

async function onIssueOfficialContract() {
  if (!ensureWorkOrderSelected()) {
    return
  }
  if (!form.contract_no) {
    ElMessage.warning('请输入正式合同编号')
    return
  }
  await issueOfficialContract({
    work_order_id: form.work_order_id!,
    contract_no: form.contract_no,
    remark: form.remark || undefined
  })
  ElMessage.success('正式合同出具成功')
}

async function onIssuePaperReport() {
  if (!ensureWorkOrderSelected()) {
    return
  }
  if (!form.paper_report_no) {
    ElMessage.warning('请输入纸质报告编号')
    return
  }
  const row = await issuePaperReport({
    work_order_id: form.work_order_id!,
    paper_report_no: form.paper_report_no,
    copy_count: form.copy_count,
    remark: form.remark || undefined
  })
  recentRecords.value = [row, ...recentRecords.value].slice(0, 20)
  ElMessage.success('纸质报告登记成功')
}

onMounted(async () => {
  try {
    const data = await listWorkOrders()
    workOrderOptions.value = data.items
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '文印室页面加载失败')
  }
})
</script>

<style scoped>
.page-header h2,
.page-header p {
  margin: 0;
}

.page-header h2 {
  font-size: 20px;
  color: #153a63;
}

.page-header p {
  margin-top: 6px;
  color: #64748b;
  font-size: 13px;
}

.printroom-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 18px;
  align-items: start;
}

.printroom-main,
.printroom-side {
  min-width: 0;
}

.printroom-main :deep(.el-form) {
  border: 1px solid #d8e5f2;
  border-radius: 10px;
  padding: 18px;
  background: linear-gradient(180deg, #ffffff 0%, #fbfdff 100%);
}

.printroom-note-card {
  border: 1px solid #d8e5f2;
  border-radius: 10px;
  padding: 16px;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
  position: sticky;
  top: 0;
}

.printroom-note-title {
  color: #0c3157;
  font-size: 15px;
  font-weight: 700;
}

.printroom-note-list {
  margin: 12px 0 0;
  padding-left: 20px;
  color: #475569;
  line-height: 1.7;
}

@media (max-width: 960px) {
  .printroom-layout {
    grid-template-columns: 1fr;
  }

  .printroom-note-card {
    position: static;
  }
}
</style>
