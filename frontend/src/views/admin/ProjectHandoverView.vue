<template>
  <el-card v-loading="loading" shadow="never">
    <template #header>
      <el-space><span>项目接管与交接</span><el-button @click="load">刷新</el-button></el-space>
    </template>
    <el-alert type="info" :closable="false" title="账号停用后，创建人及负责人职责由管理员接管；审核职责需重新分配给合格人员。交接保留当前流程阶段与历史记录。" />
    <h3>历史待接管项目</h3>
    <el-table :data="legacy" empty-text="暂无需要接管的历史项目">
      <el-table-column prop="project_code" label="项目编号" width="160" />
      <el-table-column prop="project_name" label="项目名称" min-width="240" />
      <el-table-column prop="source_name" label="已停用账号" width="130" />
      <el-table-column label="遗留职责" min-width="180"><template #default="{ row }">{{ row.duties.join('、') }}</template></el-table-column>
      <el-table-column label="操作" width="120"><template #default="{ row }"><el-button :disabled="busy" type="primary" link @click="recover(row)">接管项目</el-button></template></el-table-column>
    </el-table>
    <h3>职责分配与交接记录</h3>
    <el-switch v-model="pendingOnly" active-text="只看待分配" />
    <el-table :data="visibleRows" empty-text="暂无交接任务">
      <el-table-column prop="project_code" label="项目编号" width="160" />
      <el-table-column prop="project_name" label="项目名称" min-width="220" />
      <el-table-column prop="duty" label="职责" width="140" />
      <el-table-column prop="source_name" label="原账号" width="110" />
      <el-table-column prop="custodian_name" label="接管管理员" width="130" />
      <el-table-column prop="target_name" label="接任人" width="110" />
      <el-table-column label="状态" width="110"><template #default="{ row }">{{ statusText(row.status) }}</template></el-table-column>
      <el-table-column prop="reason" label="说明" min-width="180" show-overflow-tooltip />
      <el-table-column label="操作" width="190"><template #default="{ row }">
        <el-button v-if="row.status === 'PENDING'" :disabled="busy" type="primary" link @click="openAssign(row)">重新分配</el-button>
        <el-button link @click="router.push(`/projects/${row.project_id}/flow`)">查看项目</el-button>
      </template></el-table-column>
    </el-table>
    <el-dialog v-model="dialog" title="分配项目职责" width="520px">
      <p>{{ current?.project_code }} · {{ current?.duty }}</p>
      <el-form label-width="80px">
        <el-form-item label="接任账号"><el-select v-model="target" filterable placeholder="选择合格的有效账号" style="width:100%"><el-option v-for="u in candidates" :key="u.id" :value="u.id" :label="`${u.name}（${u.username}）`" /></el-select></el-form-item>
        <el-form-item label="交接说明"><el-input v-model="reason" type="textarea" :maxlength="1000" /></el-form-item>
      </el-form>
      <el-alert v-if="!candidates.length" type="warning" :closable="false" title="没有符合角色和回避要求的账号，请先调整账号角色或相关项目职责。" />
      <template #footer><el-button @click="dialog = false">取消</el-button><el-button type="primary" :loading="busy" :disabled="!target || !reason.trim()" @click="submit">确认分配</el-button></template>
    </el-dialog>
  </el-card>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '@/api/http'

interface Task { id: number; project_id: number; project_code: string; project_name: string; duty: string; status: string; source_name: string; custodian_name: string; target_name: string; reason: string }
interface Legacy { project_id: number; project_code: string; project_name: string; source_user_id: number; source_name: string; duties: string[] }
const router = useRouter()
const rows = ref<Task[]>([]), legacy = ref<Legacy[]>([])
const loading = ref(false), busy = ref(false), pendingOnly = ref(true), dialog = ref(false)
const current = ref<Task>(), target = ref<number>(), reason = ref('')
const candidates = ref<Array<{ id: number; name: string; username: string }>>([])
const visibleRows = computed(() => rows.value.filter(r => !pendingOnly.value || r.status === 'PENDING'))
const statusText = (s: string) => ({ PENDING: '待分配', ASSIGNED: '已分配', SUPERSEDED: '已转交' }[s] || s)
const fail = (e: any) => ElMessage.error(e?.response?.data?.detail || '操作失败，请重试')
async function load() {
  loading.value = true
  try { const { data } = await http.get('/project-handovers'); rows.value = data.items; legacy.value = data.legacy } catch (e) { fail(e) } finally { loading.value = false }
}
async function recover(row: Legacy) {
  try {
    await ElMessageBox.confirm(`将 ${row.project_code} 的 ${row.duties.join('、')} 转入您的接管清单？`, '接管项目')
    busy.value = true
    await http.post('/project-handovers/recover', { project_id: row.project_id, source_user_id: row.source_user_id })
    ElMessage.success('已接管，请继续分配职责'); await load()
  } catch (e) { if (e !== 'cancel' && e !== 'close') fail(e) } finally { busy.value = false }
}
async function openAssign(row: Task) {
  busy.value = true
  try {
    const { data } = await http.get(`/project-handovers/${row.id}/candidates`)
    current.value = row; candidates.value = data.items; target.value = undefined; reason.value = ''; dialog.value = true
  } catch (e) { fail(e) } finally { busy.value = false }
}
async function submit() {
  if (!current.value || !target.value || !reason.value.trim()) return
  busy.value = true
  try {
    await http.post(`/project-handovers/${current.value.id}/assign`, { target_user_id: target.value, reason: reason.value.trim() })
    dialog.value = false; ElMessage.success('职责已分配，已通知接任人'); await load()
  } catch (e) { fail(e) } finally { busy.value = false }
}
onMounted(load)
</script>
