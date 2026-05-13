<template>
  <el-card shadow="never">
    <template #header>项目冲突提醒</template>
    <el-space style="margin-bottom: 12px">
      <el-select v-model="status" clearable placeholder="全部状态" style="width: 180px" @change="load">
        <el-option label="待确认" value="PENDING" />
        <el-option label="已确认冲突待删除" value="CONFIRMED" />
        <el-option label="已处理" value="RESOLVED" />
      </el-select>
      <el-button type="primary" @click="load">刷新</el-button>
      <el-button type="success" @click="onExport">导出Excel</el-button>
    </el-space>
    <el-table :data="rows" v-loading="loading" size="small">
      <el-table-column prop="status" label="状态" width="130">
        <template #default="{ row }">{{ statusText(row.status) }}</template>
      </el-table-column>
      <el-table-column label="项目A" min-width="260">
        <template #default="{ row }">
          <div>{{ row.project_a.project_no }} {{ row.project_a.project_name }}</div>
          <div class="muted">客户：{{ row.project_a.client_name }}；负责人：{{ row.project_a.project_leader_display_name }}</div>
          <div class="muted">金额：{{ row.project_a.project_amount }}；基准日：{{ row.project_a.valuation_base_date }}</div>
          <div class="muted">合同初稿上传：{{ row.project_a.contract_uploaded_at }}</div>
        </template>
      </el-table-column>
      <el-table-column label="项目B" min-width="260">
        <template #default="{ row }">
          <div>{{ row.project_b.project_no }} {{ row.project_b.project_name }}</div>
          <div class="muted">客户：{{ row.project_b.client_name }}；负责人：{{ row.project_b.project_leader_display_name }}</div>
          <div class="muted">金额：{{ row.project_b.project_amount }}；基准日：{{ row.project_b.valuation_base_date }}</div>
          <div class="muted">合同初稿上传：{{ row.project_b.contract_uploaded_at }}</div>
        </template>
      </el-table-column>
      <el-table-column label="处理说明" min-width="180" prop="resolve_comment" show-overflow-tooltip />
      <el-table-column label="操作" width="230" fixed="right">
        <template #default="{ row }">
          <el-space v-if="row.status === 'PENDING'" wrap>
            <el-button link type="success" @click="markNotConflict(row)">不构成冲突</el-button>
            <el-button link type="danger" @click="openConfirm(row)">确认冲突</el-button>
          </el-space>
          <span v-else>-</span>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" title="确认构成项目冲突" width="560px">
      <el-form label-width="110px">
        <el-form-item label="保留项目">
          <el-radio-group v-model="decision.kept_project_id">
            <el-radio v-if="current" :label="current.project_a.project_id">{{ current.project_a.project_no }} {{ current.project_a.project_name }}</el-radio>
            <el-radio v-if="current" :label="current.project_b.project_id">{{ current.project_b.project_no }} {{ current.project_b.project_name }}</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="处理说明">
          <el-input v-model="decision.comment" type="textarea" :rows="3" placeholder="必填" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="danger" :loading="submitting" @click="submitConfirm">确认冲突</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  confirmProjectConflict,
  exportProjectConflictsExcel,
  listProjectConflicts,
  markProjectConflictNotConflict,
  type ProjectConflictItem
} from '@/api/projectConflicts'

const rows = ref<ProjectConflictItem[]>([])
const loading = ref(false)
const submitting = ref(false)
const status = ref<string>()
const dialogVisible = ref(false)
const current = ref<ProjectConflictItem>()
const decision = reactive({ kept_project_id: undefined as number | undefined, comment: '' })

function statusText(value: string) {
  return ({ PENDING: '待确认', CONFIRMED: '已确认冲突待删除', RESOLVED: '已处理' } as Record<string, string>)[value] || value
}

async function load() {
  loading.value = true
  try {
    rows.value = (await listProjectConflicts(status.value)).items
  } finally {
    loading.value = false
  }
}

async function markNotConflict(row: ProjectConflictItem) {
  await ElMessageBox.confirm('确认这两个项目不构成项目冲突，并解除锁定吗？', '确认处理', { type: 'warning' })
  await markProjectConflictNotConflict(row.id)
  ElMessage.success('已解除项目冲突提醒')
  await load()
}

function openConfirm(row: ProjectConflictItem) {
  current.value = row
  decision.kept_project_id = row.project_a.project_id
  decision.comment = ''
  dialogVisible.value = true
}

async function submitConfirm() {
  if (!current.value || !decision.kept_project_id || !decision.comment.trim()) {
    ElMessage.warning('请选择保留项目并填写处理说明')
    return
  }
  submitting.value = true
  try {
    await confirmProjectConflict(current.value.id, {
      kept_project_id: decision.kept_project_id,
      comment: decision.comment.trim()
    })
    dialogVisible.value = false
    ElMessage.success('已确认项目冲突，未保留项目将进入重复项目待删除状态')
    await load()
  } finally {
    submitting.value = false
  }
}

async function onExport() {
  await exportProjectConflictsExcel(status.value)
  ElMessage.success('Excel已生成')
}

onMounted(load)
</script>

<style scoped>
.muted {
  color: #64748b;
  font-size: 12px;
  line-height: 1.8;
}
</style>
