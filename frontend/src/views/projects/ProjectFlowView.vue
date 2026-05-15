<template>
  <el-row class="project-flow-layout" :gutter="12">
    <el-col :span="4">
      <el-card class="flow-nav-card" shadow="never">
        <template #header>项目流程导航</template>
        <el-menu :default-active="activeNode" @select="onSelectNode">
          <el-menu-item v-for="node in visibleFlowNodes" :key="node.key" :index="node.key">{{ node.label }}</el-menu-item>
        </el-menu>
      </el-card>
    </el-col>

    <el-col :span="17">
      <el-card class="flow-main-card" shadow="never">
        <template #header>
          <div class="panel-header">
            <span>当前环节办理区</span>
            <el-button type="primary" link @click="goHome">返回首页</el-button>
          </div>
        </template>
        <el-empty v-if="!flow" description="暂无项目数据" />
        <template v-else-if="flow.duplicate_delete_required">
          <el-alert
            type="error"
            :closable="false"
            show-icon
            title="该项目已被管理员判定为重复项目，请删除。"
            style="margin-bottom: 16px"
          />
          <el-button type="danger" :loading="duplicateDeleting" @click="deleteDuplicate">删除重复项目</el-button>
        </template>
        <component
          v-else
          :is="activePanel"
          :project-id="projectId"
          :flow-info="flow"
          :work-order-id="workOrderId"
          :can-edit="canProjectOperate"
          :can-operate="canProjectOperate"
          :user-roles="userRoles"
          @changed="onPanelChanged"
          @navigate="onPanelNavigate"
        />
      </el-card>
    </el-col>

    <el-col :span="3">
      <el-card class="flow-step-card" shadow="never">
        <template #header>办理流程图</template>
        <el-steps direction="vertical" :active="activeFlowStep" finish-status="success">
          <el-step v-for="step in stepTimeline" :key="step" :title="step" />
        </el-steps>
      </el-card>
    </el-col>
  </el-row>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getProjectFlow, type ProjectFlowData } from '@/api/projectFlow'
import { deleteDuplicateProject } from '@/api/projects'
import { createWorkOrder, listWorkOrders } from '@/api/workorders'
import { useAuthStore } from '@/store/auth'
import ProjectBasicPanel from './panels/ProjectBasicPanel.vue'
import ProjectMembersPanel from './panels/ProjectMembersPanel.vue'
import ContractUploadPanel from './panels/ContractUploadPanel.vue'
import ReviewSubmitPanel from './panels/ReviewSubmitPanel.vue'
import SignoffPanel from './panels/SignoffPanel.vue'
import ReportIssuePanel from './panels/ReportIssuePanel.vue'
import ReportMailingPanel from './panels/ReportMailingPanel.vue'
import InvoicePanel from './panels/InvoicePanel.vue'
import ArchivePanel from './panels/ArchivePanel.vue'
import ContractReviewPanel from './panels/ContractReviewPanel.vue'

const baseFlowNodes = [
  { key: 'basic', label: '项目基本信息' },
  { key: 'members', label: '项目组成员' },
  { key: 'contract', label: '合同初稿上传' },
  { key: 'contractReview', label: '合同初稿审核' },
  { key: 'review', label: '报告送审' },
  { key: 'signoff', label: '签发审核' },
  { key: 'issue', label: '报告出具' },
  { key: 'mailing', label: '报告邮寄' },
  { key: 'invoice', label: '发票开具' },
  { key: 'archive', label: '报告归档' },
]

const panelMap: Record<string, any> = {
  basic: ProjectBasicPanel,
  members: ProjectMembersPanel,
  contract: ContractUploadPanel,
  contractReview: ContractReviewPanel,
  review: ReviewSubmitPanel,
  signoff: SignoffPanel,
  issue: ReportIssuePanel,
  mailing: ReportMailingPanel,
  invoice: InvoicePanel,
  archive: ArchivePanel,
}

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const projectId = Number(route.params.id)
const flow = ref<ProjectFlowData | null>(null)
const workOrderId = ref<number>()
const activeNode = ref('basic')
const userRoles = computed(() => auth.user?.roles || [])
const duplicateDeleting = ref(false)
const canProjectOperate = computed(() => Boolean(flow.value?.can_operate))
const activePanel = computed(() => panelMap[activeNode.value] || ProjectBasicPanel)

const availableNodes = computed(() => {
  if (flow.value?.project.project_source === 'EXTERNAL') {
    return baseFlowNodes.filter(node => node.key !== 'members')
  }
  return baseFlowNodes
})

const stepTimeline = computed(() => flow.value?.flow_steps || [])
const activeFlowStep = computed(() => {
  const current = flow.value?.project.current_step
  if (!current || !stepTimeline.value.length) return 0
  const idx = stepTimeline.value.indexOf(current)
  return idx >= 0 ? idx : 0
})

const visibleFlowNodes = computed(() => {
  const roleName = flow.value?.user_role_in_project || ''
  const roles = userRoles.value
  const currentStatus = flow.value?.current_work_order_status || ''
  const canSeeAll = ['管理员', '项目负责人', '项目组成员', '创建人'].includes(roleName)

  if (canSeeAll) return availableNodes.value
  if (roleName === '合同审核人' || (roles.includes('CONTRACT_REVIEWER') && ['WAIT_CONTRACT_REVIEW_SUBMIT', 'CONTRACT_REVIEWING', 'CONTRACT_REJECTED'].includes(currentStatus))) {
    return availableNodes.value.filter(node => ['basic', 'contractReview'].includes(node.key))
  }
  if (roleName.includes('审老师') || roles.some(role => ['FIRST_REVIEWER', 'SECOND_REVIEWER', 'THIRD_REVIEWER'].includes(role))) {
    return availableNodes.value.filter(node => node.key === 'review')
  }
  if (roleName === '文印室' || roles.includes('PRINT_ROOM')) {
    return availableNodes.value.filter(node => ['issue', 'mailing'].includes(node.key))
  }
  if (roleName === '财务' || roles.includes('FINANCE')) {
    return availableNodes.value.filter(node => node.key === 'invoice')
  }
  if (roleName === '首席评估师' || roles.includes('CHIEF_APPRAISER')) {
    return availableNodes.value.filter(node => node.key === 'signoff')
  }
  if (roles.includes('ARCHIVE_MANAGER')) {
    return availableNodes.value.filter(node => node.key === 'archive')
  }
  return availableNodes.value.filter(node => node.key === activeNode.value)
})

function ensureVisibleActiveNode() {
  if (!visibleFlowNodes.value.some(node => node.key === activeNode.value)) {
    activeNode.value = visibleFlowNodes.value[0]?.key || availableNodes.value[0]?.key || 'basic'
  }
}

function onSelectNode(key: string) {
  if (key === 'invoice' && flow.value?.project.project_amount == null) {
    ElMessage.warning('请先在项目基本信息模块中录入项目金额')
    return
  }
  activeNode.value = key
}

function goHome() {
  router.push('/dashboard')
}

async function loadWorkOrder() {
  if (flow.value?.current_work_order_id) {
    workOrderId.value = flow.value.current_work_order_id
    return
  }

  const data = await listWorkOrders()
  const item = data.items.find(w => w.project_id === projectId)
  if (item) {
    workOrderId.value = item.id
    return
  }

  if (!flow.value?.can_operate) {
    workOrderId.value = undefined
    return
  }

  try {
    const created = await createWorkOrder({ project_id: projectId })
    workOrderId.value = created.id
  } catch (error: any) {
    const detail = error?.response?.data?.detail
    if (error?.response?.status === 400 && typeof detail === 'string' && detail.includes('工单号')) {
      const refreshed = await listWorkOrders()
      workOrderId.value = refreshed.items.find(w => w.project_id === projectId)?.id
      return
    }
    throw error
  }
}

async function load() {
  try {
    await auth.ensureUserLoaded()
    flow.value = await getProjectFlow(projectId)
    await loadWorkOrder()
    ensureVisibleActiveNode()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '无权查看该项目')
  }
}

async function onPanelChanged() {
  await load()
}

function onPanelNavigate(key: string) {
  if (key === 'invoice' && flow.value?.project.project_amount == null) {
    ElMessage.warning('请先在项目基本信息模块中录入项目金额')
    return
  }
  activeNode.value = key
}

async function deleteDuplicate() {
  duplicateDeleting.value = true
  try {
    await deleteDuplicateProject(projectId)
    ElMessage.success('重复项目已删除')
    router.push('/dashboard')
  } finally {
    duplicateDeleting.value = false
  }
}

watch(visibleFlowNodes, ensureVisibleActiveNode)
onMounted(load)
</script>

<style scoped>
.project-flow-layout {
  align-items: flex-start;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.flow-nav-card,
.flow-main-card,
.flow-step-card {
  min-height: 280px;
}

.flow-nav-card :deep(.el-menu) {
  border-right: 0;
}

.flow-nav-card :deep(.el-menu-item) {
  height: 44px;
  margin: 6px 0;
  border-radius: 6px;
  color: #475569;
  font-weight: 600;
}

.flow-nav-card :deep(.el-menu-item.is-active) {
  color: var(--zq-primary);
  background: var(--zq-primary-soft);
}

.flow-step-card :deep(.el-card__body) {
  padding: 18px 14px;
}

.flow-step-card :deep(.el-step__title) {
  font-size: 14px;
  line-height: 1.35;
}
</style>
