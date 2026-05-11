<template>
  <el-row :gutter="12">
    <el-col :span="5">
      <el-card shadow="never">
        <template #header>项目流程导航</template>
        <el-menu :default-active="activeNode" @select="onSelectNode">
          <el-menu-item v-for="node in visibleFlowNodes" :key="node.key" :index="node.key">{{ node.label }}</el-menu-item>
        </el-menu>
      </el-card>
    </el-col>

    <el-col :span="15">
      <el-card shadow="never">
        <template #header>
          <div class="panel-header">
            <span>当前环节办理区</span>
            <el-button type="primary" link @click="goHome">返回首页</el-button>
          </div>
        </template>
        <el-empty v-if="!flow" description="暂无项目数据" />
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
        />
      </el-card>
    </el-col>

    <el-col :span="4">
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
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getProjectFlow, type ProjectFlowData } from '@/api/projectFlow'
import { createWorkOrder, listWorkOrders } from '@/api/workorders'
import { useAuthStore } from '@/store/auth'
import ProjectBasicPanel from './panels/ProjectBasicPanel.vue'
import ProjectMembersPanel from './panels/ProjectMembersPanel.vue'
import ContractUploadPanel from './panels/ContractUploadPanel.vue'
import ReviewSubmitPanel from './panels/ReviewSubmitPanel.vue'
import ReportIssuePanel from './panels/ReportIssuePanel.vue'
import InvoicePanel from './panels/InvoicePanel.vue'
import ArchivePanel from './panels/ArchivePanel.vue'

const flowNodes = [
  { key: 'basic', label: '项目基本信息' },
  { key: 'members', label: '项目组成员' },
  { key: 'contract', label: '合同上传' },
  { key: 'review', label: '报告送审' },
  { key: 'issue', label: '报告出具' },
  { key: 'invoice', label: '发票开具' },
  { key: 'archive', label: '报告归档' }
]

const panelMap: Record<string, any> = {
  basic: ProjectBasicPanel,
  members: ProjectMembersPanel,
  contract: ContractUploadPanel,
  review: ReviewSubmitPanel,
  issue: ReportIssuePanel,
  invoice: InvoicePanel,
  archive: ArchivePanel
}

const stepTimeline = ['项目创建', '项目组成员', '合同上传', '报告送审', '报告出具', '发票开具', '报告归档']
const stepAliasMap: Record<string, string> = {
  项目创建: '项目创建',
  项目组成员管理: '项目组成员',
  项目组成员: '项目组成员',
  合同上传: '合同上传',
  报告送审: '报告送审',
  一审: '报告送审',
  二审: '报告送审',
  三审: '报告送审',
  报告出具: '报告出具',
  开具发票: '发票开具',
  发票开具: '发票开具',
  报告归档: '报告归档',
  已归档: '报告归档'
}

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const projectId = Number(route.params.id)
const flow = ref<ProjectFlowData | null>(null)
const workOrderId = ref<number>()
const activeNode = ref(flowNodes[0].key)
const userRoles = computed(() => auth.user?.roles || [])
const canProjectOperate = computed(() => Boolean(flow.value?.can_operate))
const activePanel = computed(() => panelMap[activeNode.value] || ProjectBasicPanel)
const activeFlowStep = computed(() => {
  const current = flow.value?.project.current_step
  if (!current) return 0
  const normalized = stepAliasMap[current] ?? current
  const idx = stepTimeline.indexOf(normalized)
  return idx >= 0 ? idx : 0
})

const visibleFlowNodes = computed(() => {
  const roleName = flow.value?.user_role_in_project || ''
  const roles = userRoles.value
  const canSeeAll = ['管理员', '项目负责人', '项目组成员', '创建人'].includes(roleName)

  if (canSeeAll) return flowNodes
  if (roleName.includes('审老师') || roles.some(role => ['FIRST_REVIEWER', 'SECOND_REVIEWER', 'THIRD_REVIEWER'].includes(role))) {
    return flowNodes.filter(node => node.key === 'review')
  }
  if (roleName === '文印室' || roles.includes('PRINT_ROOM')) {
    return flowNodes.filter(node => node.key === 'issue')
  }
  if (roleName === '财务' || roles.includes('FINANCE')) {
    return flowNodes.filter(node => node.key === 'invoice')
  }
  if (roles.includes('ARCHIVE_MANAGER')) {
    return flowNodes.filter(node => node.key === 'archive')
  }
  return flowNodes.filter(node => node.key === activeNode.value)
})

function ensureVisibleActiveNode() {
  if (!visibleFlowNodes.value.some(node => node.key === activeNode.value)) {
    activeNode.value = visibleFlowNodes.value[0]?.key || flowNodes[0].key
  }
}

function onSelectNode(key: string) {
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

watch(visibleFlowNodes, ensureVisibleActiveNode)
onMounted(load)
</script>

<style scoped>
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
</style>
