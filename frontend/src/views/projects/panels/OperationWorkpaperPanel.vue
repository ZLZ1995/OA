<template>
  <section v-loading="busy">
    <h3>{{ reviewMode ? '操作类底稿审核' : '操作类底稿提交' }}</h3>
    <el-alert title="本环节与三审独立进行，两项均通过后才能进入签发审核。" :closable="false" />
    <p>当前状态：{{ labels[state?.status || 'NOT_OPEN'] }}</p>
    <el-alert v-if="error" :title="error" type="error" :closable="false" />
    <el-alert v-if="state?.status === 'NOT_OPEN'" title="二审通过后开放底稿提交。" :closable="false" />
    <template v-if="canSubmit">
      <el-form label-width="110px">
        <el-form-item label="底稿审核人员">
          <el-select v-model="reviewerId" placeholder="请选择档案管理员" style="width: 100%">
            <el-option v-for="person in candidates" :key="person.id" :value="person.id" :label="person.name" />
          </el-select>
        </el-form-item>
        <el-form-item label="提交方式">
          <el-radio-group v-model="materialType">
            <el-radio value="ZIP">ZIP文件</el-radio><el-radio value="CLOUD_LINK">网盘信息</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="materialType === 'ZIP'" label="操作类底稿">
          <input type="file" accept=".zip" multiple :disabled="busy" @change="selectFiles" />
          <p>支持一个或多个ZIP文件。文件在点击提交时上传。</p>
          <ul><li v-for="file in selectedFiles" :key="file.name">{{ file.name }}</li></ul>
          <ul><li v-for="file in retainedFiles" :key="file.id">沿用：{{ file.name }} <el-button link type="danger" @click="retainedFiles = retainedFiles.filter(item => item.id !== file.id)">移除</el-button></li></ul>
        </el-form-item>
        <template v-else>
          <el-form-item label="网盘链接" required><el-input v-model="cloudUrl" maxlength="2048" /></el-form-item>
          <el-form-item label="提取码" required><el-input v-model="cloudCode" maxlength="255" /></el-form-item>
        </template>
      </el-form>
      <el-button type="primary" :disabled="busy" @click="submit">提交底稿审核</el-button>
    </template>
    <template v-if="!reviewMode && isLeader && state?.status === 'SUBMITTED'">
      <p>审核人员尚未进入本轮底稿审核页面，可以撤回后修改。</p>
      <el-button :disabled="busy" @click="act('withdraw')">撤回并修改</el-button>
    </template>
    <el-alert v-if="state?.status === 'IN_REVIEW' && !reviewMode" title="审核人员已进入本轮底稿审核页面，不能撤回。" :closable="false" />
    <template v-if="reviewMode && current?.reviewer_id === auth.user?.id && state?.status === 'IN_REVIEW'">
      <el-input v-model="reason" type="textarea" placeholder="审核意见（退回时必填）" maxlength="4000" />
      <div class="actions"><el-button type="success" :disabled="busy" @click="decision('APPROVE')">审核通过</el-button>
        <el-button type="danger" :disabled="busy" @click="decision('REJECT')">退回补充</el-button></div>
    </template>
    <h4>提交与审核记录</h4>
    <el-card v-for="row in state?.history || []" :key="row.id" class="record" shadow="never">
      <p>第{{ row.round_no }}轮 · {{ labels[row.status] }} · 审核人：{{ row.reviewer_name }}</p>
      <p>提交时间（北京时间）：{{ formatTime(row.submitted_at) }}</p>
      <p v-if="row.first_entered_at">进入审核页面：{{ formatTime(row.first_entered_at) }}</p>
      <p v-if="row.reason">审核意见：{{ row.reason }}</p>
      <template v-if="row.cloud_url"><p>网盘链接：<a :href="row.cloud_url" target="_blank" rel="noopener noreferrer">{{ row.cloud_url }}</a></p><p>提取码：{{ row.cloud_code }}</p></template>
      <el-button v-for="file in row.files" :key="file.id" link type="primary" @click="downloadWorkOrderFile(file.id, file.name)">{{ file.name }}</el-button>
    </el-card>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import http from '@/api/http'
import { downloadWorkOrderFile } from '@/api/files'
import { useAuthStore } from '@/store/auth'
import { workpaperDraftKey } from '@/utils/workpaperRequest'
import { validWorkpaperUrl, workpaperError } from '@/utils/workpaperFeedback'
const props = defineProps<{ workOrderId?: number; reviewMode?: boolean }>()
const emit = defineEmits(['changed'])
const auth = useAuthStore()
const state = ref<any>(null)
const busy = ref(false)
const error = ref('')
const candidates = ref<{ id: number; name: string }[]>([])
const reviewerId = ref<number>()
const materialType = ref<'ZIP' | 'CLOUD_LINK'>('ZIP')
const selectedFiles = ref<File[]>([])
const retainedFiles = ref<{ id: number; name: string }[]>([])
let loadedDraftRound: number | undefined
const cloudUrl = ref('')
const cloudCode = ref('')
const reason = ref('')
let requestId = crypto.randomUUID()
let draftKey: string | null = null
const uploaded = new Map<File, number>()
const labels: Record<string, string> = { NOT_OPEN: '二审尚未通过', DRAFT: '待提交', SUBMITTED: '已提交，待进入审核', IN_REVIEW: '审核中', WITHDRAWN: '已撤回，待重新提交', REJECTED: '已退回，待补充', APPROVED: '已通过' }
const current = computed(() => state.value?.history.find((row: any) => row.id === state.value.current_submission_id))
const isLeader = computed(() => state.value?.leader_id === auth.user?.id)
const canSubmit = computed(() => !props.reviewMode && isLeader.value && ['DRAFT', 'WITHDRAWN', 'REJECTED'].includes(state.value?.status))
const base = () => `/operation-workpapers/work-orders/${props.workOrderId}`
function selectFiles(event: Event) {
  selectedFiles.value = Array.from((event.target as HTMLInputElement).files || [])
}
const message = workpaperError
function formatTime(value: string) { return new Date(value).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai', hour12: false }) }
async function load(enterPage = false) {
  if (!props.workOrderId) return
  state.value = (await http.get(base())).data
  const nextDraft = workpaperDraftKey(props.workOrderId, state.value.current_submission_id, state.value.status)
  if (nextDraft && nextDraft !== draftKey) {
    requestId = crypto.randomUUID()
    draftKey = nextDraft
  }
  // Only an explicitly opened reviewer panel counts as entering the review page.
  if (enterPage && props.reviewMode && current.value?.reviewer_id === auth.user?.id && state.value.status === 'SUBMITTED') {
    await http.post(`/operation-workpapers/submissions/${current.value.id}/enter`)
    state.value = (await http.get(base())).data
  }
  if (canSubmit.value) {
    candidates.value = (await http.get(`${base()}/candidates`)).data
    if (current.value && loadedDraftRound !== current.value.id) {
      loadedDraftRound = current.value.id
      materialType.value = current.value.material_type
      cloudUrl.value = current.value.cloud_url || ''; cloudCode.value = current.value.cloud_code || ''
      retainedFiles.value = [...current.value.files]
      reviewerId.value = candidates.value.some(person => person.id === current.value.reviewer_id) ? current.value.reviewer_id : undefined
    }
  }
}
async function run(action: () => Promise<void>) {
  busy.value = true; error.value = ''
  try { await action() } catch (e) { error.value = message(e); ElMessage.error(error.value); await load().catch(() => {}) }
  finally { busy.value = false }
}
async function submit() {
  if (!reviewerId.value) return ElMessage.warning('请选择底稿审核人员')
  if (materialType.value === 'ZIP' && ((!selectedFiles.value.length && !retainedFiles.value.length) || selectedFiles.value.some(f => !f.name.toLowerCase().endsWith('.zip')))) return ElMessage.warning('请选择一个或多个ZIP文件')
  if (materialType.value === 'CLOUD_LINK' && (!cloudUrl.value.trim() || !cloudCode.value.trim())) return ElMessage.warning('网盘链接和提取码均为必填项')
  if (materialType.value === 'CLOUD_LINK' && !validWorkpaperUrl(cloudUrl.value)) {
    error.value = '请输入完整的网盘链接，以 http:// 或 https:// 开头，例如 https://pan.baidu.com/s/…'
    return ElMessage.warning(error.value)
  }
  await run(async () => {
    const ids: number[] = materialType.value === 'ZIP' ? retainedFiles.value.map(file => file.id) : []
    if (materialType.value === 'ZIP') for (const file of selectedFiles.value) {
      if (!uploaded.has(file)) {
        const form = new FormData(); form.append('upload', file)
        const { data } = await http.post(`${base()}/files`, form, { timeout: 1800000 })
        uploaded.set(file, data.id)
      }
      ids.push(uploaded.get(file)!)
    }
    await http.post(`${base()}/submit`, { reviewer_id: reviewerId.value, request_id: requestId,
      revision: state.value.revision, material_type: materialType.value, file_ids: ids,
      cloud_url: materialType.value === 'CLOUD_LINK' ? cloudUrl.value : null,
      cloud_code: materialType.value === 'CLOUD_LINK' ? cloudCode.value : null })
    // Submission succeeded even if best-effort temporary cleanup fails.
    for (const id of uploaded.values()) if (!ids.includes(id)) {
      await http.delete(`/operation-workpapers/files/${id}`).catch(() => {})
    }
    requestId = crypto.randomUUID(); selectedFiles.value = []; retainedFiles.value = []; uploaded.clear()
    await load(); emit('changed'); ElMessage.success('底稿已提交')
  })
}
async function act(action: string) {
  await run(async () => { await http.post(`/operation-workpapers/submissions/${current.value.id}/${action}`); await load(); emit('changed') })
}
async function decision(action: string) {
  if (action === 'REJECT' && !reason.value.trim()) return ElMessage.warning('请填写退回理由')
  await run(async () => {
    await http.post(`/operation-workpapers/submissions/${current.value.id}/decision`, { action, reason: reason.value })
    reason.value = ''; await load(); emit('changed')
  })
}
watch(() => [props.workOrderId, props.reviewMode], () => run(() => load(true)), { immediate: true })
</script>
<style scoped>
.record, .actions { margin-top: 16px; }
section { display: grid; gap: 14px; }
a { overflow-wrap: anywhere; }
</style>
