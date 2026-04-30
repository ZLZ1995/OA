<template>
  <el-row :gutter="12">
    <el-col :span="5">
      <el-card shadow="never">
        <template #header>项目流程导航</template>
        <el-menu :default-active="activeNode" @select="onSelectNode">
          <el-menu-item v-for="node in flowNodes" :key="node.key" :index="node.key">{{ node.label }}</el-menu-item>
        </el-menu>
      </el-card>
    </el-col>

    <el-col :span="11">
      <el-card shadow="never">
        <template #header>当前环节办理区</template>
        <el-descriptions :column="2" border v-if="flow">
          <el-descriptions-item label="项目编号">{{ flow.project.project_no }}</el-descriptions-item>
          <el-descriptions-item label="项目名称">{{ flow.project.project_name }}</el-descriptions-item>
          <el-descriptions-item label="客户名称">{{ flow.project.client_name }}</el-descriptions-item>
          <el-descriptions-item label="当前步骤">{{ flow.project.current_step }}</el-descriptions-item>
        </el-descriptions>

        <el-alert v-if="!workOrderId" type="warning" show-icon style="margin-top: 12px" title="当前项目尚未创建工单，部分流程节点暂不可办理" />

        <el-card v-if="selectedNode" shadow="never" style="margin-top: 12px">
          <template #header>{{ selectedNode.label }}</template>
          <p style="margin-bottom: 12px">{{ selectedNode.desc }}</p>

          <template v-if="activeNode === 'members'">
            <el-form inline>
              <el-form-item label="成员角色">
                <el-select v-model="memberRole" :disabled="!canEditMembers" style="width: 180px">
                  <el-option label="项目负责人" value="项目负责人" />
                  <el-option label="项目组成员" value="项目组成员" />
                </el-select>
              </el-form-item>
              <el-form-item label="用户">
                <el-select v-model="newUserIds" multiple collapse-tags :disabled="!canEditMembers" style="width: 320px">
                  <el-option v-for="u in users" :key="u.id" :label="`${u.real_name}（${u.username}）`" :value="u.id" />
                </el-select>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :disabled="!canEditMembers" @click="onAddMembers">添加成员</el-button>
              </el-form-item>
            </el-form>
            <el-table :data="members" size="small" v-loading="membersLoading">
              <el-table-column prop="real_name" label="姓名" width="120" />
              <el-table-column prop="username" label="账号" width="140" />
              <el-table-column prop="member_role" label="角色" width="130" />
              <el-table-column label="操作" width="110">
                <template #default="{ row }">
                  <el-button size="small" type="danger" plain :disabled="!canEditMembers" @click="onDeleteMember(row.id)">移除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </template>

          <template v-else-if="activeNode === 'contract'">
            <el-upload :show-file-list="false" :auto-upload="false" :on-change="onPickContractFile" :disabled="!canUploadFiles || !workOrderId">
              <el-button type="primary" :disabled="!canUploadFiles || !workOrderId">上传合同扫描件</el-button>
            </el-upload>
            <el-table :data="contractFiles" size="small" style="margin-top: 12px">
              <el-table-column prop="origin_file_name" label="文件名" />
              <el-table-column prop="version_no" label="版本" width="80" />
              <el-table-column prop="uploaded_at" label="上传时间" width="200" />
            </el-table>
          </template>

          <template v-else-if="activeNode === 'review'">
            <el-form label-width="100px">
              <el-form-item label="审核轮次">
                <el-select v-model="reviewRound" :disabled="!canSubmitReview" style="width: 160px" @change="loadReviewCandidates">
                  <el-option label="一审" value="FIRST" />
                  <el-option label="二审" value="SECOND" />
                  <el-option label="三审" value="THIRD" />
                </el-select>
              </el-form-item>
              <el-form-item label="审核老师">
                <el-select v-model="reviewerUserId" :disabled="!canSubmitReview" style="width: 280px">
                  <el-option v-for="u in reviewCandidates" :key="u.user_id" :label="`${u.real_name}(${u.username})`" :value="u.user_id" />
                </el-select>
              </el-form-item>
              <el-form-item label="审核备注"><el-input v-model="reviewComment" type="textarea" :rows="3" /></el-form-item>
              <el-form-item>
                <el-upload :show-file-list="false" :auto-upload="false" :on-change="onPickReviewFile" :disabled="!canUploadFiles || !workOrderId">
                  <el-button :disabled="!canUploadFiles || !workOrderId">上传待审报告</el-button>
                </el-upload>
                <el-button type="primary" :disabled="!canSubmitReview || !workOrderId" @click="onSubmitReview" style="margin-left: 8px">提交审核</el-button>
                <el-button type="success" :disabled="!canReviewDecision || !workOrderId" @click="onReviewDecision('APPROVE')">通过</el-button>
                <el-button type="danger" plain :disabled="!canReviewDecision || !workOrderId" @click="onReviewDecision('REJECT_RETURN')">退回</el-button>
              </el-form-item>
            </el-form>
          </template>

          <template v-else-if="activeNode === 'issue'">
            <el-form label-width="120px">
              <el-form-item label="正式合同编号"><el-input v-model="contractNo" :disabled="!canPrintRoom || !workOrderId" /></el-form-item>
              <el-form-item label="报告扫描件编号"><el-input v-model="paperReportNo" :disabled="!canPrintRoom || !workOrderId" /></el-form-item>
              <el-form-item label="份数"><el-input-number v-model="copyCount" :disabled="!canPrintRoom || !workOrderId" :min="1" :max="99" /></el-form-item>
              <el-form-item label="邮寄信息"><el-input v-model="shippingInfo" :disabled="!canBusinessWrite" type="textarea" :rows="2" /></el-form-item>
              <el-form-item>
                <el-button type="primary" :disabled="!canPrintRoom || !workOrderId" @click="onIssueOfficialContract">出具正式合同</el-button>
                <el-button type="success" :disabled="!canPrintRoom || !workOrderId" @click="onIssuePaperReport">上传报告扫描件并出具</el-button>
              </el-form-item>
            </el-form>
          </template>

          <template v-else-if="activeNode === 'invoice'">
            <el-form label-width="110px">
              <el-form-item label="发票号"><el-input v-model="invoiceNo" :disabled="!canFinance || !workOrderId" /></el-form-item>
              <el-form-item label="金额"><el-input-number v-model="invoiceAmount" :disabled="!canFinance || !workOrderId" :min="0" :precision="2" /></el-form-item>
              <el-form-item>
                <el-button type="primary" :disabled="!canFinance || !workOrderId" @click="onCreateInvoice">提交开票</el-button>
                <el-button :disabled="!canFinance || !latestInvoice" @click="onMarkInvoiceDone">标记已开票</el-button>
              </el-form-item>
            </el-form>
          </template>

          <template v-else-if="activeNode === 'archive'">
            <el-form label-width="110px">
              <el-form-item label="档案号"><el-input v-model="archiveNo" :disabled="!canArchive || !workOrderId" /></el-form-item>
              <el-form-item label="存放位置"><el-input v-model="archiveLocation" :disabled="!canArchive || !workOrderId" /></el-form-item>
              <el-form-item label="备注"><el-input v-model="archiveRemark" type="textarea" :rows="2" :disabled="!canArchive || !workOrderId" /></el-form-item>
              <el-form-item><el-button type="primary" :disabled="!canArchive || !workOrderId" @click="onCreateArchive">确认归档</el-button></el-form-item>
            </el-form>
          </template>
        </el-card>
      </el-card>
    </el-col>

    <el-col :span="8">
      <el-card shadow="never">
        <template #header>办理流程图</template>
        <el-steps direction="vertical" :active="activeFlowStep" finish-status="success">
          <el-step v-for="step in stepTimeline" :key="step" :title="step" />
        </el-steps>
      </el-card>
    </el-col>
  </el-row>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, type UploadFile } from 'element-plus'
import { getProjectFlow, type ProjectFlowData } from '@/api/projectFlow'
import { listWorkOrders } from '@/api/workorders'
import { listUsers } from '@/api/users'
import { batchCreateProjectMembers, deleteProjectMember, listProjectMembers, type ProjectMemberItem } from '@/api/projectMembers'
import { listWorkOrderFiles, uploadWorkOrderFile, type WorkOrderFileItem } from '@/api/files'
import { decideReview, listReviewCandidates, submitReview, type ReviewCandidateItem } from '@/api/reviews'
import { issueOfficialContract, issuePaperReport } from '@/api/printRoom'
import { createInvoice, listInvoices, type InvoiceItem, updateInvoice } from '@/api/finance'
import { createArchive } from '@/api/archives'

const route = useRoute()
const flow = ref<ProjectFlowData | null>(null)
const projectId = computed(() => Number(route.params.id))
const workOrderId = ref<number | null>(null)
const flowNodes = [
  { key: 'basic', label: '项目基本信息', desc: '查看项目基本信息与当前状态。' },
  { key: 'members', label: '项目组成员', desc: '维护项目组成员与职责分工。' },
  { key: 'contract', label: '合同上传', desc: '上传与确认项目合同材料。' },
  { key: 'review', label: '报告送审', desc: '提交报告并推进审核流程。' },
  { key: 'issue', label: '报告出具', desc: '文印室办理报告出具，项目组维护邮寄信息。' },
  { key: 'invoice', label: '发票开具', desc: '提交开票信息并由财务确认开票。' },
  { key: 'archive', label: '报告归档', desc: '上传归档资料并完成归档。' }
]
const activeNode = ref(flowNodes[0].key)
const selectedNode = computed(() => flowNodes.find((n) => n.key === activeNode.value) ?? flowNodes[0])
const stepTimeline = ['项目创建', '项目组成员', '合同上传', '报告送审', '报告出具', '发票开具', '报告归档']
const stepAliasMap: Record<string, string> = { 项目创建: '项目创建', 项目组成员管理: '项目组成员', 项目组成员: '项目组成员', 合同上传: '合同上传', 报告送审: '报告送审', 一审: '报告送审', 二审: '报告送审', 三审: '报告送审', 报告出具: '报告出具', 开具发票: '发票开具', 发票开具: '发票开具', 报告归档: '报告归档', 已归档: '报告归档' }
const activeFlowStep = computed(() => {
  const current = flow.value?.project.current_step
  const normalized = current ? (stepAliasMap[current] ?? current) : stepTimeline[0]
  const idx = stepTimeline.indexOf(normalized)
  return idx >= 0 ? idx : 0
})

const userRole = computed(() => flow.value?.user_role_in_project || '')
const canBusinessWrite = computed(() => ['创建人', '项目负责人', '项目组成员'].includes(userRole.value))
const canEditMembers = canBusinessWrite
const canUploadFiles = canBusinessWrite
const canSubmitReview = computed(() => ['项目负责人', '创建人'].includes(userRole.value))
const canReviewDecision = computed(() => ['一审老师', '二审老师', '三审老师'].includes(userRole.value))
const canPrintRoom = computed(() => userRole.value === '文印室')
const canFinance = computed(() => userRole.value === '财务')
const canArchive = canBusinessWrite

const users = ref<any[]>([])
const members = ref<ProjectMemberItem[]>([])
const membersLoading = ref(false)
const newUserIds = ref<number[]>([])
const memberRole = ref<'项目负责人' | '项目组成员'>('项目组成员')
const contractFiles = ref<WorkOrderFileItem[]>([])
const reviewCandidates = ref<ReviewCandidateItem[]>([])
const reviewRound = ref<'FIRST' | 'SECOND' | 'THIRD'>('FIRST')
const reviewerUserId = ref<number>()
const reviewComment = ref('')
const contractNo = ref('')
const paperReportNo = ref('')
const copyCount = ref(1)
const shippingInfo = ref('')
const invoiceNo = ref('')
const invoiceAmount = ref(0)
const latestInvoice = ref<InvoiceItem | null>(null)
const archiveNo = ref('')
const archiveLocation = ref('')
const archiveRemark = ref('')

function onSelectNode(key: string) { activeNode.value = key }

async function refreshFlow() {
  flow.value = await getProjectFlow(projectId.value)
}

async function resolveWorkOrder() {
  const rows = (await listWorkOrders()).items.filter((w) => w.project_id === projectId.value)
  workOrderId.value = rows[0]?.id ?? null
}

async function loadMembers() {
  membersLoading.value = true
  try { members.value = (await listProjectMembers(projectId.value)).items } finally { membersLoading.value = false }
}

async function onAddMembers() {
  if (!newUserIds.value.length) return ElMessage.warning('请选择用户')
  await batchCreateProjectMembers({ project_id: projectId.value, user_ids: newUserIds.value, member_role: memberRole.value })
  ElMessage.success('成员添加成功'); newUserIds.value = []; await loadMembers(); await refreshFlow()
}
async function onDeleteMember(id: number) {
  await deleteProjectMember(id); ElMessage.success('成员已移除'); await loadMembers(); await refreshFlow()
}

async function loadContractFiles() {
  if (!workOrderId.value) return
  const rows = (await listWorkOrderFiles(workOrderId.value)).items
  contractFiles.value = rows.filter((r) => r.file_category === 'CONTRACT' || r.business_stage === 'CONTRACT')
}
async function onPickContractFile(file: UploadFile) {
  if (!workOrderId.value || !file.raw) return
  await uploadWorkOrderFile({ work_order_id: workOrderId.value, file_category: 'CONTRACT', business_stage: 'CONTRACT', file: file.raw })
  ElMessage.success('合同文件上传成功'); await loadContractFiles(); await refreshFlow()
}
async function onPickReviewFile(file: UploadFile) {
  if (!workOrderId.value || !file.raw) return
  await uploadWorkOrderFile({ work_order_id: workOrderId.value, file_category: 'REPORT', business_stage: 'REVIEW', file: file.raw })
  ElMessage.success('待审报告上传成功')
}

async function loadReviewCandidates() {
  if (!workOrderId.value) return
  reviewCandidates.value = (await listReviewCandidates(workOrderId.value, reviewRound.value)).items
}
async function onSubmitReview() {
  if (!workOrderId.value || !reviewerUserId.value) return ElMessage.warning('请选择审核老师')
  await submitReview({ work_order_id: workOrderId.value, review_round: reviewRound.value, reviewer_user_id: reviewerUserId.value, comment: reviewComment.value || undefined })
  ElMessage.success('已提交审核'); await refreshFlow()
}
async function onReviewDecision(action: 'APPROVE' | 'REJECT_RETURN') {
  if (!workOrderId.value) return
  await decideReview({ work_order_id: workOrderId.value, review_round: reviewRound.value, action, comment: reviewComment.value || undefined })
  ElMessage.success(action === 'APPROVE' ? '已通过' : '已退回'); await refreshFlow()
}

async function onIssueOfficialContract() {
  if (!workOrderId.value || !contractNo.value) return ElMessage.warning('请填写正式合同编号')
  await issueOfficialContract({ work_order_id: workOrderId.value, contract_no: contractNo.value, remark: shippingInfo.value || undefined })
  ElMessage.success('正式合同出具成功'); await refreshFlow()
}
async function onIssuePaperReport() {
  if (!workOrderId.value || !paperReportNo.value) return ElMessage.warning('请填写报告扫描件编号')
  await issuePaperReport({ work_order_id: workOrderId.value, paper_report_no: paperReportNo.value, copy_count: copyCount.value, remark: shippingInfo.value || undefined })
  ElMessage.success('报告出具成功'); await refreshFlow()
}

async function loadInvoices() {
  if (!workOrderId.value) return
  const rows = (await listInvoices()).items.filter((i) => i.work_order_id === workOrderId.value)
  latestInvoice.value = rows[0] ?? null
}
async function onCreateInvoice() {
  if (!workOrderId.value || !invoiceNo.value) return ElMessage.warning('请填写发票号')
  latestInvoice.value = await createInvoice({ work_order_id: workOrderId.value, invoice_no: invoiceNo.value, amount: invoiceAmount.value, status: 'PENDING' })
  ElMessage.success('开票信息已提交'); await refreshFlow()
}
async function onMarkInvoiceDone() {
  if (!latestInvoice.value) return
  latestInvoice.value = await updateInvoice(latestInvoice.value.id, { status: 'ISSUED' })
  ElMessage.success('已标记开票'); await refreshFlow()
}
async function onCreateArchive() {
  if (!workOrderId.value || !archiveNo.value) return ElMessage.warning('请填写档案号')
  await createArchive({ work_order_id: workOrderId.value, archive_no: archiveNo.value, archive_location: archiveLocation.value || undefined, archive_at: new Date().toISOString(), remark: archiveRemark.value || undefined })
  ElMessage.success('归档成功'); await refreshFlow()
}

onMounted(async () => {
  try {
    await refreshFlow()
    await resolveWorkOrder()
    users.value = (await listUsers()).items
    await Promise.all([loadMembers(), loadContractFiles(), loadInvoices()])
    if (workOrderId.value) await loadReviewCandidates()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '项目流程页加载失败')
  }
})
</script>
