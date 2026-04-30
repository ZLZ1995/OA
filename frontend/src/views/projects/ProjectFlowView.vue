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
        <el-empty v-if="!flow" description="暂无项目数据" />
        <template v-else>
          <el-form v-if="projectWorkOrders.length > 1" inline style="margin-bottom: 10px">
            <el-form-item label="工单选择">
              <el-select v-model="workOrderId" placeholder="请选择工单" style="width: 320px">
                <el-option v-for="w in projectWorkOrders" :key="w.id" :label="`${w.work_order_no || '工单'} - ${w.title || ''}`" :value="w.id" />
              </el-select>
            </el-form-item>
          </el-form>
          <component
            :is="activePanel"
            :project-id="projectId"
            :flow-info="flow"
            :work-order-id="workOrderId"
            :can-edit="canProjectOperate"
            :can-operate="canProjectOperate"
            :user-roles="userRoles"
            @changed="onPanelChanged"
          />
        </template>
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
import { ElMessage } from 'element-plus'
import { getProjectFlow, type ProjectFlowData } from '@/api/projectFlow'
import { listWorkOrders, type WorkOrderItem } from '@/api/workorders'
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
const panelMap: Record<string, any> = { basic: ProjectBasicPanel, members: ProjectMembersPanel, contract: ContractUploadPanel, review: ReviewSubmitPanel, issue: ReportIssuePanel, invoice: InvoicePanel, archive: ArchivePanel }
const stepTimeline = ['项目创建', '项目组成员', '合同上传', '报告送审', '报告出具', '发票开具', '报告归档']
const stepAliasMap: Record<string, string> = { 项目创建: '项目创建', 项目组成员管理: '项目组成员', 项目组成员: '项目组成员', 合同上传: '合同上传', 报告送审: '报告送审', 一审: '报告送审', 二审: '报告送审', 三审: '报告送审', 报告出具: '报告出具', 开具发票: '发票开具', 发票开具: '发票开具', 报告归档: '报告归档', 已归档: '报告归档' }

const route = useRoute()
const auth = useAuthStore()
const projectId = Number(route.params.id)
const flow = ref<ProjectFlowData | null>(null)
const workOrderId = ref<number>()
const projectWorkOrders = ref<WorkOrderItem[]>([])
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

function onSelectNode(key: string) { activeNode.value = key }

async function loadWorkOrders() {
  const data = await listWorkOrders()
  projectWorkOrders.value = data.items.filter(w => w.project_id === projectId)
  if (flow.value?.current_work_order_id && projectWorkOrders.value.some(w => w.id === flow.value?.current_work_order_id)) {
    workOrderId.value = flow.value.current_work_order_id
    return
  }
  if (projectWorkOrders.value.length === 1) {
    workOrderId.value = projectWorkOrders.value[0].id
    return
  }
  if (!workOrderId.value && projectWorkOrders.value.length > 1) {
    workOrderId.value = projectWorkOrders.value[0].id
  }
}

async function load() {
  try {
    flow.value = await getProjectFlow(projectId)
    await loadWorkOrders()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '无权查看该项目')
  }
}

async function onPanelChanged() { await load() }

onMounted(load)
</script>
