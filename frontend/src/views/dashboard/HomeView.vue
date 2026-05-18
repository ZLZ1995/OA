<template>
  <div class="workbench-page">
    <div class="workbench-hero">
      <div>
        <p>中勤资产评估有限公司</p>
        <h1>中勤资产评估项目流程管理系统</h1>
      </div>
      <el-tag effect="plain" type="primary">流程工作台</el-tag>
    </div>

    <div class="workbench-grid">
      <el-card class="create-card" shadow="never">
        <template #header>项目创建区</template>
        <el-form label-width="110px">
          <el-form-item label="承接单位">
            <el-select v-model="form.undertaking_unit">
              <el-option label="中勤" value="中勤" />
              <el-option label="中立国际" value="中立国际" />
              <el-option label="中众" value="中众" />
              <el-option label="其他" value="其他" />
            </el-select>
          </el-form-item>
          <el-form-item label="项目编号">
            <el-input v-model="form.project_code" placeholder="系统自动生成" readonly disabled />
          </el-form-item>
          <el-form-item label="项目名称">
            <el-input v-model="form.project_name" />
          </el-form-item>
          <el-form-item label="客户名称">
            <el-input v-model="form.client_name" />
          </el-form-item>
          <el-form-item label="评估业务性质">
            <el-select v-model="form.evaluation_business_nature" style="width: 100%">
              <el-option v-for="item in evaluationBusinessOptions" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
          <el-form-item label="报告类型">
            <el-select v-model="form.report_type">
              <el-option v-for="item in reportTypeOptions" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
          <el-form-item label="评估基准日">
            <el-date-picker
              v-model="form.valuation_base_date"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="选择评估基准日"
              style="width: 100%"
            />
          </el-form-item>
          <el-form-item label="项目承接业务员">
            <el-input v-model="form.business_salesman" />
          </el-form-item>
          <el-form-item label="项目来源">
            <el-radio-group v-model="form.project_source">
              <el-radio-button value="INTERNAL">评估一部</el-radio-button>
              <el-radio-button value="EXTERNAL">评估二部</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="项目负责人">
            <el-input
              v-if="form.project_source === 'EXTERNAL'"
              v-model="form.external_project_leader_name"
              placeholder="请输入项目负责人姓名"
            />
            <el-input v-else :model-value="currentUserDisplayName" disabled />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="onCreate">创建项目</el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <el-card class="todo-card" shadow="never">
        <template #header>
          <div class="card-header">
            <span>待办项目</span>
            <span class="card-header-tip">点击项目后，下方联动展示该项目消息和办理入口</span>
          </div>
        </template>
        <el-table
          ref="todoTableRef"
          class="wide-table todo-table"
          :data="todoProjects"
          size="small"
          row-key="id"
          highlight-current-row
          table-layout="fixed"
          @current-change="handleTodoCurrentChange"
          @row-click="handleTodoRowClick"
        >
          <el-table-column prop="project_no" label="项目编号" width="126" show-overflow-tooltip />
          <el-table-column prop="project_name" label="项目名称" min-width="108" show-overflow-tooltip />
          <el-table-column prop="client_name" label="客户名称" min-width="124" show-overflow-tooltip />
          <el-table-column prop="current_step" label="当前步骤" width="110" show-overflow-tooltip />
          <el-table-column prop="todo_action" label="待办事项" min-width="126" show-overflow-tooltip />
          <el-table-column label="优先级" width="92">
            <template #default="{ row }">
              <el-tag size="small" :type="todoPriorityTagType(row)">
                {{ todoPriorityText(row) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="200">
            <template #default="{ row }">
              <el-button v-if="row.can_approve_delete" link type="danger" @click.stop="goDeleteApprovals">处理删除审核</el-button>
              <template v-else>
                <el-button link type="primary" @click.stop="goProject(row.id, row)">进入项目</el-button>
                <el-button link type="success" @click.stop="focusTodoProject(row)">查看联动</el-button>
              </template>
              <el-button v-if="row.can_approve_termination" link type="danger" @click.stop="approveTermination(row)">允许终止</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-card class="linkage-card" shadow="never">
        <template #header>
          <div class="card-header">
            <span>待办消息联动</span>
            <span class="card-header-tip">{{ selectedTodo ? '当前联动项目：' + selectedTodo.project_name : '请选择一个待办项目' }}</span>
          </div>
        </template>

        <div class="summary-metrics summary-metrics-compact">
          <div class="summary-metric">
            <span>未读消息</span>
            <strong>{{ selectedTodo ? linkageStats.unread_count : 0 }}</strong>
          </div>
          <div class="summary-metric">
            <span>催办消息</span>
            <strong>{{ selectedTodo ? linkageStats.today_reminder_count : 0 }}</strong>
          </div>
          <div class="summary-metric">
            <span>今日新增</span>
            <strong>{{ selectedTodo ? linkageStats.today_new_count : 0 }}</strong>
          </div>
        </div>

        <el-tabs v-model="activeTab" class="linkage-tabs" @tab-change="loadLinkedNotifications">
          <el-tab-pane label="未读" name="unread" />
          <el-tab-pane label="已读" name="read" />
          <el-tab-pane label="我发起的" name="initiated" />
          <el-tab-pane label="抄送我的" name="cc" />
          <el-tab-pane label="全部" name="all" />
        </el-tabs>

        <div class="linkage-toolbar">
          <NotificationFilterBar
            class="linkage-filter"
            :filters="filters"
            @update:filters="Object.assign(filters, $event)"
            @search="loadLinkedNotifications"
            @reset="resetFilters"
          />
          <div class="linkage-toolbar-actions">
            <el-button :disabled="!selectedNotificationIds.length" @click="batchRead">批量已读</el-button>
            <el-button type="primary" plain @click="openNotificationsPage">查看全部消息</el-button>
          </div>
        </div>

        <div class="linkage-content">
          <div class="linkage-main">
            <el-card class="linkage-section-card message-section-card" shadow="never">
              <template #header>
                <div class="linkage-section-head">
                  <div>
                    <h3>消息动态</h3>
                    <p>围绕当前待办项目集中查看流程消息、催办和处理提醒</p>
                  </div>
                </div>
              </template>
              <NotificationListTable
                :items="selectedTodo ? linkedNotifications : []"
                @selection-change="selectedNotificationIds = $event"
                @open="openNotification"
                @enter-handle="enterHandle"
                @row-click="handleNotificationRowClick"
              />
            </el-card>

            <el-card class="linkage-section-card projects-section-card" shadow="never">
              <template #header>
                <div class="card-header">
                  <span>我的项目</span>
                  <span class="card-header-tip">同时统计我创建的项目和我办理过的项目</span>
                </div>
              </template>
              <el-table class="wide-table" :data="myProjects" size="small" table-layout="fixed">
                <el-table-column prop="project_no" label="项目编号" width="132" show-overflow-tooltip />
                <el-table-column prop="project_name" label="项目名称" min-width="130" show-overflow-tooltip />
                <el-table-column prop="client_name" label="客户名称" min-width="130" show-overflow-tooltip />
                <el-table-column
                  prop="my_project_role"
                  label="我的角色"
                  width="116"
                  column-key="my_project_role"
                  :filters="myProjectRoleFilters"
                  :filter-method="filterMyProjectRole"
                  filter-placement="bottom-end"
                  show-overflow-tooltip
                />
                <el-table-column prop="current_step" label="当前步骤" width="108" show-overflow-tooltip />
                <el-table-column prop="status_display" label="状态" width="110" show-overflow-tooltip />
                <el-table-column label="操作" width="420">
                  <template #default="{ row }">
                    <el-button link type="primary" @click="goProject(row.id)">进入项目</el-button>
                    <el-button link type="success" @click="goNotifications(row.id)">相关消息</el-button>
                    <el-button link type="primary" :disabled="!row.can_edit" @click="editProject(row)">编辑</el-button>
                    <el-button link type="warning" :disabled="!row.can_archive" @click="archive(row.id)">归档</el-button>
                    <el-button link type="danger" :disabled="!row.can_request_termination" @click="requestTermination(row)">项目终止/废止</el-button>
                    <el-button link type="danger" @click="remove(row)">删除</el-button>
                  </template>
                </el-table-column>
              </el-table>
            </el-card>
          </div>

          <div class="linkage-side">
            <div class="side-panel flow-preview-panel">
              <div class="side-panel-head">
                <h3>流程图预览</h3>
                <p>点击消息后，在这里查看业务流程和当前环节位置</p>
              </div>
              <div class="flow-preview-current">
                <div>
                  <span class="flow-preview-label">当前项目</span>
                  <strong>{{ selectedTodo?.project_name || '暂无待办项目' }}</strong>
                </div>
                <div>
                  <span class="flow-preview-label">定位环节</span>
                  <strong>{{ selectedTodo ? previewCurrentStep : '暂无环节定位' }}</strong>
                </div>
                <div>
                  <span class="flow-preview-label">所属阶段</span>
                  <strong>{{ selectedTodo ? previewCurrentGroup : '暂无阶段信息' }}</strong>
                </div>
              </div>

              <div v-if="selectedTodo" class="flow-timeline">
                <div
                  v-for="item in previewFlowTimeline"
                  :key="item.key"
                  class="flow-timeline-item"
                  :class="{
                    'is-done': item.index < previewActiveFlowIndex,
                    'is-active': item.index === previewActiveFlowIndex,
                  }"
                >
                  <div class="flow-timeline-line" />
                  <div class="flow-preview-dot">{{ item.index + 1 }}</div>
                  <div class="flow-timeline-card">
                    <span class="flow-timeline-group">{{ item.group }}</span>
                    <strong>{{ item.label }}</strong>
                    <span v-if="item.index === previewActiveFlowIndex">当前定位</span>
                  </div>
                </div>
              </div>
              <el-empty v-else description="暂无待办项目，流程预览区保持固定结构" />

              <div class="flow-preview-footer">
                <el-button type="primary" :disabled="!selectedTodo" @click="selectedTodo && goProject(selectedTodo.id, selectedTodo)">进入办理</el-button>
                <el-button :disabled="!selectedTodo" @click="openNotificationsPage">查看关联消息</el-button>
              </div>
            </div>

            <div class="side-panel focus-panel">
              <div class="side-panel-head">
                <h3>联动说明</h3>
                <p>帮助使用新工作台结构</p>
              </div>
              <ol class="focus-list">
                <li>上方切换待办项目，下方消息会自动按项目联动刷新。</li>
                <li>点击某条消息后，右侧流程图会自动定位到对应业务环节。</li>
                <li>没有待办时保留固定结构，仅在模块内部显示空态。</li>
              </ol>
            </div>
          </div>
        </div>
      </el-card>

    </div>

    <NotificationDetailDrawer
      v-model:visible="detailVisible"
      :item="currentNotification"
      :timeline-items="timelineItems"
      @goto-target="gotoTarget"
    />

    <el-dialog v-model="editVisible" title="编辑项目" width="560px">
      <el-form label-width="120px">
        <el-form-item label="承接单位">
          <el-select v-model="editForm.undertaking_unit" style="width: 100%">
            <el-option label="中勤" value="中勤" />
            <el-option label="中立国际" value="中立国际" />
            <el-option label="中众" value="中众" />
            <el-option label="其他" value="其他" />
          </el-select>
        </el-form-item>
        <el-form-item label="项目名称">
          <el-input v-model="editForm.project_name" />
        </el-form-item>
        <el-form-item label="客户名称">
          <el-input v-model="editForm.client_name" />
        </el-form-item>
        <el-form-item label="评估业务性质">
          <el-select v-model="editForm.evaluation_business_nature" style="width: 100%">
            <el-option v-for="item in evaluationBusinessOptions" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="报告类型">
          <el-select v-model="editForm.report_type" style="width: 100%">
            <el-option v-for="item in reportTypeOptions" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="评估基准日">
          <el-date-picker
            v-model="editForm.valuation_base_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="选择评估基准日"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="项目承接业务员">
          <el-input v-model="editForm.business_salesman" />
        </el-form-item>
        <el-form-item label="项目来源">
          <el-radio-group v-model="editForm.project_source">
            <el-radio-button value="INTERNAL">评估一部</el-radio-button>
            <el-radio-button value="EXTERNAL">评估二部</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="项目负责人">
          <el-input
            v-if="editForm.project_source === 'EXTERNAL'"
            v-model="editForm.external_project_leader_name"
            placeholder="请输入项目负责人姓名"
          />
          <el-input v-else :model-value="currentUserDisplayName" disabled />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="editLoading" @click="saveProject">确认修改并保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="deleteDialogVisible" title="申请删除项目" width="520px">
      <el-form label-width="120px">
        <el-form-item label="共同认证管理员">
          <el-select v-model="deleteDraft.approver_user_id" style="width: 100%">
            <el-option
              v-for="item in deleteAdminOptions"
              :key="item.id"
              :label="item.real_name"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="删除原因">
          <el-input v-model="deleteDraft.reason" type="textarea" :rows="3" placeholder="可选填写删除原因" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="deleteDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="deleteSubmitting" @click="submitDeleteRequest">提交删除申请</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox, type ElTable } from 'element-plus'
import { useRouter } from 'vue-router'
import NotificationDetailDrawer from '@/components/notifications/NotificationDetailDrawer.vue'
import NotificationFilterBar from '@/components/notifications/NotificationFilterBar.vue'
import NotificationListTable from '@/components/notifications/NotificationListTable.vue'
import {
  batchMarkNotificationRead,
  getNotificationDetail,
  getNotificationStats,
  getNotificationTimeline,
  listMyNotifications,
  markNotificationRead,
  type NotificationItem,
  type NotificationTimelineItem,
} from '@/api/notifications'
import { createProjectDeleteRequest } from '@/api/projectDeleteRequests'
import {
  archiveProject,
  approveProjectTermination,
  createProject,
  deleteProject,
  getProject,
  requestProjectTermination,
  updateProject,
  type EvaluationBusinessNature,
  type ProjectItem,
  type ProjectSource,
  type ProjectUndertakingUnit,
  type ReportType,
} from '@/api/projects'
import { listUserCandidates, type UserItem } from '@/api/users'
import { getWorkbench, type WorkbenchProjectItem } from '@/api/workbench'
import { useAuthStore } from '@/store/auth'
import { useNotificationStore } from '@/store/notification'

type NotificationTab = 'all' | 'unread' | 'read' | 'initiated' | 'cc'
type FlowPreviewNode = { key: string; label: string; keywords: string[]; group: string }

const evaluationBusinessOptions: EvaluationBusinessNature[] = [
  '国有资产评估业务',
  '境外资产评估业务',
  '证券期货评估业务',
  '司法评估业务',
  '金融资产评估业务',
  '珠宝首饰评估业务',
  '其他',
]

const reportTypeOptions: ReportType[] = ['评估报告', '估值报告', '咨询报告', '复核报告', '追溯性报告']

const router = useRouter()
const auth = useAuthStore()
const notifications = useNotificationStore()
const todoTableRef = ref<InstanceType<typeof ElTable>>()
const myProjects = ref<WorkbenchProjectItem[]>([])
const todoProjects = ref<WorkbenchProjectItem[]>([])
const selectedTodoId = ref<number>()
const linkedNotifications = ref<NotificationItem[]>([])
const selectedNotificationIds = ref<number[]>([])
const activeTab = ref<NotificationTab>('unread')
const detailVisible = ref(false)
const currentNotification = ref<NotificationItem | null>(null)
const previewNotification = ref<NotificationItem | null>(null)
const timelineItems = ref<NotificationTimelineItem[]>([])
const editVisible = ref(false)
const editLoading = ref(false)
const editingProjectId = ref<number>()
const deleteDialogVisible = ref(false)
const deleteSubmitting = ref(false)
const deleteTargetProjectId = ref<number>()
const deleteTargetProjectName = ref('')
const deleteAdminOptions = ref<UserItem[]>([])

const linkageStats = reactive({
  today_new_count: 0,
  unread_count: 0,
  today_reminder_count: 0,
  read_rate: 0,
  avg_process_duration_seconds: 0,
  latest_notification_id: null as number | null,
  server_time: '',
})

const filters = reactive({
  keyword: '',
  message_type: '',
  priority: '',
  project_id: undefined as number | undefined,
})

const currentUserDisplayName = computed(() => auth.user?.real_name || auth.user?.username || '当前创建人')

const selectedTodo = computed(() => todoProjects.value.find(item => item.id === selectedTodoId.value) || null)
const myProjectRoleOptions = computed(() =>
  Array.from(new Set(myProjects.value.map(item => item.my_project_role).filter((value): value is string => Boolean(value)))),
)
const myProjectRoleFilters = computed(() =>
  myProjectRoleOptions.value.map(role => ({
    text: role,
    value: role,
  })),
)

const FLOW_PREVIEW_STEPS: FlowPreviewNode[] = [
  { key: 'create', label: '项目创建', keywords: ['项目创建'], group: '立项准备' },
  { key: 'members', label: '项目组成员', keywords: ['项目组成员'], group: '立项准备' },
  { key: 'contractUpload', label: '合同初审上传', keywords: ['合同初审上传'], group: '立项准备' },
  { key: 'contractReview', label: '合同初稿审核', keywords: ['合同初稿审核', '合同审核'], group: '审核流转' },
  { key: 'reviewSubmit', label: '报告送审', keywords: ['报告送审'], group: '审核流转' },
  { key: 'firstReview', label: '一审', keywords: ['一审'], group: '审核流转' },
  { key: 'secondReview', label: '二审', keywords: ['二审'], group: '审核流转' },
  { key: 'thirdReview', label: '三审', keywords: ['三审'], group: '审核流转' },
  { key: 'signoff', label: '签发审核', keywords: ['签发审核'], group: '审核流转' },
  { key: 'reportIssue', label: '报告出具', keywords: ['报告出具'], group: '交付办理' },
  { key: 'reportMailing', label: '报告邮寄', keywords: ['报告邮寄'], group: '交付办理' },
  { key: 'invoice', label: '发票开具', keywords: ['发票开具', '开票'], group: '交付办理' },
  { key: 'archive', label: '报告归档', keywords: ['报告归档', '归档'], group: '归档完成' },
]

const previewFlowSteps = computed(() => FLOW_PREVIEW_STEPS.map(item => item.label))

const previewCurrentStep = computed(() => {
  const notificationTitle = previewNotification.value?.title || ''
  const todoAction = selectedTodo.value?.todo_action || ''
  const currentStep = selectedTodo.value?.current_step || ''
  const lookupText = `${notificationTitle} ${todoAction} ${currentStep}`
  const matched = FLOW_PREVIEW_STEPS.find(item => item.keywords.some(keyword => lookupText.includes(keyword)))
  return matched?.label || currentStep || '待定位'
})

const previewActiveFlowIndex = computed(() => {
  const index = previewFlowSteps.value.findIndex(step => step === previewCurrentStep.value)
  return index >= 0 ? index : 0
})

const previewFlowTimeline = computed(() =>
  FLOW_PREVIEW_STEPS.map(item => ({
    ...item,
    index: previewFlowSteps.value.findIndex(step => step === item.label),
  })),
)

const previewCurrentGroup = computed(() => {
  const current = previewFlowTimeline.value.find(item => item.index === previewActiveFlowIndex.value)
  return current?.group || '流程定位'
})

const form = reactive({
  undertaking_unit: '中勤' as ProjectUndertakingUnit,
  project_code: '',
  project_name: '',
  client_name: '',
  evaluation_business_nature: '国有资产评估业务' as EvaluationBusinessNature,
  report_type: '评估报告' as ReportType,
  valuation_base_date: '',
  business_salesman: '',
  project_source: 'INTERNAL' as ProjectSource,
  external_project_leader_name: '',
})

const editForm = reactive({
  undertaking_unit: '中勤' as ProjectUndertakingUnit,
  project_name: '',
  client_name: '',
  evaluation_business_nature: '国有资产评估业务' as EvaluationBusinessNature,
  report_type: '评估报告' as ReportType,
  valuation_base_date: '',
  business_salesman: '',
  project_source: 'INTERNAL' as ProjectSource,
  external_project_leader_name: '',
})

const deleteDraft = reactive({
  approver_user_id: undefined as number | undefined,
  reason: '',
})

async function load() {
  const data = await getWorkbench()
  myProjects.value = data.my_projects
  todoProjects.value = data.todo_projects

  const preferredId = selectedTodoId.value && todoProjects.value.some(item => item.id === selectedTodoId.value)
    ? selectedTodoId.value
    : todoProjects.value[0]?.id

  if (preferredId) {
    await selectTodoProject(preferredId)
  } else {
    selectedTodoId.value = undefined
    linkedNotifications.value = []
    selectedNotificationIds.value = []
  }
}

async function refreshWorkbenchData(preserveSelection = true) {
  const previousSelectedId = preserveSelection ? selectedTodoId.value : undefined
  const data = await getWorkbench()
  myProjects.value = data.my_projects
  todoProjects.value = data.todo_projects

  const nextSelectedId = previousSelectedId && todoProjects.value.some(item => item.id === previousSelectedId)
    ? previousSelectedId
    : todoProjects.value[0]?.id

  if (nextSelectedId) {
    selectedTodoId.value = nextSelectedId
    await nextTick()
    const current = todoProjects.value.find(item => item.id === nextSelectedId)
    if (current) {
      todoTableRef.value?.setCurrentRow(current)
    }
  } else {
    selectedTodoId.value = undefined
  }
}

async function selectTodoProject(projectId: number) {
  selectedTodoId.value = projectId
  filters.project_id = projectId
  selectedNotificationIds.value = []
  previewNotification.value = null
  await nextTick()
  const current = todoProjects.value.find(item => item.id === projectId)
  if (current) {
    todoTableRef.value?.setCurrentRow(current)
  }
  await loadLinkedNotifications()
}

async function loadLinkedNotifications() {
  if (!selectedTodo.value) return
  filters.project_id = selectedTodo.value.id
  const [listResult, statsResult] = await Promise.all([
    listMyNotifications({
      tab: activeTab.value,
      keyword: filters.keyword || undefined,
      message_type: filters.message_type || undefined,
      priority: filters.priority || undefined,
      project_id: selectedTodo.value.id,
      page: 1,
      page_size: 20,
    }),
    getNotificationStats(),
  ])

  linkedNotifications.value = listResult.items
  previewNotification.value = listResult.items[0] || null
  const projectItems = listResult.items.filter(item => item.project_id === selectedTodo.value?.id)
  const unreadCount = projectItems.filter(item => !item.is_read).length
  const reminderCount = projectItems.filter(item => item.message_type === 'REMINDER').length
  const readCount = projectItems.filter(item => item.is_read).length
  const readRate = projectItems.length ? Number(((readCount / projectItems.length) * 100).toFixed(2)) : 0

  linkageStats.today_new_count = projectItems.length
  linkageStats.unread_count = unreadCount
  linkageStats.today_reminder_count = reminderCount
  linkageStats.read_rate = readRate
  linkageStats.avg_process_duration_seconds = statsResult.avg_process_duration_seconds
  linkageStats.latest_notification_id = statsResult.latest_notification_id
  linkageStats.server_time = statsResult.server_time
}

function handleTodoCurrentChange(row?: WorkbenchProjectItem) {
  if (row && row.id !== selectedTodoId.value) {
    void selectTodoProject(row.id)
  }
}

function handleTodoRowClick(row: WorkbenchProjectItem) {
  if (row.id !== selectedTodoId.value) {
    void selectTodoProject(row.id)
  }
}

function focusTodoProject(row: WorkbenchProjectItem) {
  void selectTodoProject(row.id)
}

async function openNotification(item: NotificationItem) {
  previewNotification.value = item
  if (!item.is_read) {
    await markNotificationRead(item.id)
    notifications.applyReadState([item.id])
  }
  const [detail, timeline] = await Promise.all([
    getNotificationDetail(item.id),
    getNotificationTimeline(item.id),
  ])
  currentNotification.value = { ...detail, is_read: true }
  timelineItems.value = timeline.items
  detailVisible.value = true
  await refreshWorkbenchData()
  await loadLinkedNotifications()
}

async function enterHandle(item: NotificationItem) {
  previewNotification.value = item
  if (item.process_status === 'PROCESSED') {
    ElMessage.warning('该消息对应环节已处理')
    await loadLinkedNotifications()
    return
  }
  if (!item.project_id) return
  if (!item.is_read) {
    await markNotificationRead(item.id)
    notifications.applyReadState([item.id])
  }
  await refreshWorkbenchData()
  await router.push(`/projects/${item.project_id}/flow`)
}

async function batchRead() {
  if (!selectedNotificationIds.value.length) return
  const ids = [...selectedNotificationIds.value]
  await batchMarkNotificationRead(ids)
  notifications.applyReadState(ids)
  ElMessage.success('已批量标记为已读')
  selectedNotificationIds.value = []
  await refreshWorkbenchData()
  await loadLinkedNotifications()
}

async function resetFilters() {
  filters.keyword = ''
  filters.message_type = ''
  filters.priority = ''
  await loadLinkedNotifications()
}

function handleNotificationRowClick(item: NotificationItem) {
  previewNotification.value = item
}

function filterMyProjectRole(value: string, row: WorkbenchProjectItem) {
  return row.my_project_role === value
}

function gotoTarget(item: NotificationItem) {
  if (item.link_type === 'PROJECT' && item.link_target_id) {
    router.push(`/projects/${item.link_target_id}/flow`)
    return
  }
  if (item.link_type === 'WORK_ORDER' && item.link_target_id) {
    router.push(`/workorders/${item.link_target_id}`)
    return
  }
  ElMessage.info('该消息暂无可跳转目标')
}

function openNotificationsPage() {
  if (selectedTodo.value) {
    router.push({
      path: '/notifications',
      query: { project_id: String(selectedTodo.value.id), message_type: filters.message_type || 'REMINDER' },
    })
    return
  }
  router.push('/notifications')
}

async function onCreate() {
  const user = auth.user ?? await auth.ensureUserLoaded()
  if (!user?.id) return
  if (!form.project_name || !form.client_name || !form.business_salesman.trim()) {
    ElMessage.warning('请填写完整项目创建信息')
    return
  }
  if (form.project_source === 'EXTERNAL' && !form.external_project_leader_name.trim()) {
    ElMessage.warning('评估二部项目必须填写项目负责人')
    return
  }

  const created = await createProject({
    undertaking_unit: form.undertaking_unit,
    project_name: form.project_name,
    client_name: form.client_name,
    evaluation_business_nature: form.evaluation_business_nature,
    report_type: form.report_type,
    valuation_base_date: form.valuation_base_date || undefined,
    business_salesman: form.business_salesman.trim(),
    project_source: form.project_source,
    external_project_leader_name: form.project_source === 'EXTERNAL' ? form.external_project_leader_name.trim() : undefined,
    business_user_id: user.id,
    project_leader_id: user.id,
  })
  form.project_code = created.project_code
  form.project_name = ''
  form.client_name = ''
  form.evaluation_business_nature = '国有资产评估业务'
  form.business_salesman = ''
  form.valuation_base_date = ''
  form.project_source = 'INTERNAL'
  form.external_project_leader_name = ''
  ElMessage.success('项目创建成功')
  await load()
}

async function editProject(row: WorkbenchProjectItem) {
  const project = await getProject(row.id)
  fillEditForm(project)
  editingProjectId.value = row.id
  editVisible.value = true
}

async function archive(id: number) {
  await archiveProject(id)
  ElMessage.success('项目已归档')
  await load()
}

async function requestTermination(row: WorkbenchProjectItem) {
  const { value } = await ElMessageBox.prompt(
    '请填写项目终止/废止原因，保存后项目将锁定并发送给管理员审核。',
    '项目终止/废止',
    {
      confirmButtonText: '保存并发送给管理员',
      cancelButtonText: '取消',
      inputType: 'textarea',
      inputPlaceholder: '请输入终止/废止原因',
      inputValidator: value => Boolean(value?.trim()) || '请填写项目终止/废止原因',
    },
  )
  await requestProjectTermination(row.id, value.trim())
  ElMessage.success('终止/废止申请已发送给管理员')
  await load()
}

async function approveTermination(row: WorkbenchProjectItem) {
  await ElMessageBox.alert(row.termination_reason || '未填写原因', '项目终止/废止原因', {
    confirmButtonText: '允许终止/废止',
  })
  await approveProjectTermination(row.id)
  ElMessage.success('已允许终止/废止，项目负责人现在可以归档')
  await load()
}

async function remove(row: WorkbenchProjectItem) {
  if (row.status_display === '待确认删除') {
    ElMessage.warning('已有待确认删除申请')
    return
  }
  if (row.status_display === '已归档') {
    ElMessage.warning('已归档项目不可删除')
    return
  }
  try {
    await deleteProject(row.id)
    ElMessage.success('项目已删除')
    await load()
  } catch (error: any) {
    if (error?.response?.status === 400) {
      await openDeleteDialog(row.id, row.project_name)
      return
    }
    throw error
  }
}

async function openDeleteDialog(projectId: number, projectName: string) {
  const admins = (await listUserCandidates('ADMIN')).items.filter(item => item.id !== auth.user?.id)
  if (!admins.length) {
    ElMessage.warning('暂无可选的共同认证管理员')
    return
  }
  deleteAdminOptions.value = admins
  deleteTargetProjectId.value = projectId
  deleteTargetProjectName.value = projectName
  deleteDraft.approver_user_id = admins[0].id
  deleteDraft.reason = ''
  deleteDialogVisible.value = true
}

async function submitDeleteRequest() {
  if (!deleteTargetProjectId.value || !deleteDraft.approver_user_id) {
    ElMessage.warning('请选择共同认证管理员')
    return
  }
  deleteSubmitting.value = true
  try {
    const approver = deleteAdminOptions.value.find(item => item.id === deleteDraft.approver_user_id)
    await createProjectDeleteRequest(deleteTargetProjectId.value, {
      approver_user_id: deleteDraft.approver_user_id,
      reason: deleteDraft.reason.trim() || undefined,
    })
    deleteDialogVisible.value = false
    ElMessage.success(`已提交项目“${deleteTargetProjectName.value}”删除申请，待管理员 ${approver?.real_name || ''} 确认`)
    await load()
  } finally {
    deleteSubmitting.value = false
  }
}

function fillEditForm(project: ProjectItem) {
  editForm.undertaking_unit = project.undertaking_unit
  editForm.project_name = project.project_name
  editForm.client_name = project.client_name
  editForm.evaluation_business_nature = (project.evaluation_business_nature || '国有资产评估业务') as EvaluationBusinessNature
  editForm.report_type = project.report_type
  editForm.valuation_base_date = project.valuation_base_date || ''
  editForm.business_salesman = project.business_salesman || ''
  editForm.project_source = project.project_source
  editForm.external_project_leader_name = project.external_project_leader_name || ''
}

async function saveProject() {
  if (!editingProjectId.value) return
  if (!editForm.project_name.trim() || !editForm.client_name.trim()) {
    ElMessage.warning('请填写项目名称和客户名称')
    return
  }
  if (!editForm.business_salesman.trim()) {
    ElMessage.warning('请填写项目承接业务员')
    return
  }
  if (editForm.project_source === 'EXTERNAL' && !editForm.external_project_leader_name.trim()) {
    ElMessage.warning('评估二部项目必须填写项目负责人')
    return
  }

  editLoading.value = true
  try {
    await updateProject(editingProjectId.value, {
      undertaking_unit: editForm.undertaking_unit,
      project_name: editForm.project_name.trim(),
      client_name: editForm.client_name.trim(),
      evaluation_business_nature: editForm.evaluation_business_nature,
      report_type: editForm.report_type,
      valuation_base_date: editForm.valuation_base_date || undefined,
      business_salesman: editForm.business_salesman.trim(),
      project_source: editForm.project_source,
      external_project_leader_name: editForm.project_source === 'EXTERNAL' ? editForm.external_project_leader_name.trim() : null,
    })
    ElMessage.success('项目已更新')
    editVisible.value = false
    await load()
  } finally {
    editLoading.value = false
  }
}

const TODO_PANEL_PRIORITY = ['contractReview', 'review', 'signoff', 'issue', 'mailing', 'invoice', 'archive'] as const

function normalizeTodoText(value?: string | null) {
  return (value || '').trim().toUpperCase()
}

function resolveTodoPanel(row: WorkbenchProjectItem) {
  if (row.can_approve_delete || row.can_approve_termination) return 'basic'

  const currentStep = normalizeTodoText(row.current_step)
  const todoAction = normalizeTodoText(row.todo_action)
  const statusDisplay = normalizeTodoText(row.status_display)
  const combined = `${currentStep} ${todoAction} ${statusDisplay}`
  const matched = new Set<string>()

  if (combined.includes('合同') && (combined.includes('审核') || combined.includes('初审'))) matched.add('contractReview')
  if (combined.includes('送审') || combined.includes('一审') || combined.includes('二审') || combined.includes('三审') || combined.includes('评审')) matched.add('review')
  if (combined.includes('签发')) matched.add('signoff')
  if (combined.includes('出具') || combined.includes('文印')) matched.add('issue')
  if (combined.includes('邮寄') || combined.includes('寄送')) matched.add('mailing')
  if (combined.includes('发票') || combined.includes('开票')) matched.add('invoice')
  if (combined.includes('归档') || combined.includes('档案')) matched.add('archive')

  return TODO_PANEL_PRIORITY.find(item => matched.has(item))
}

function resolveTodoLabel(row: WorkbenchProjectItem) {
  return row.todo_action?.trim() || row.current_step?.trim() || ''
}

function todoPriorityText(row: WorkbenchProjectItem) {
  if (row.can_approve_delete || row.can_approve_termination) return '紧急'
  if ((row.remind_count_today || 0) > 0 || row.is_reminded) return '重要'
  return '普通'
}

function todoPriorityTagType(row: WorkbenchProjectItem) {
  if (row.can_approve_delete || row.can_approve_termination) return 'danger'
  if ((row.remind_count_today || 0) > 0 || row.is_reminded) return 'warning'
  return 'info'
}

function formatDateTime(value?: string | null) {
  return value ? new Date(value).toLocaleString() : ''
}

function goProject(id: number, row?: WorkbenchProjectItem) {
  if (!row) {
    router.push(`/projects/${id}/flow`)
    return
  }

  const todoPanel = resolveTodoPanel(row)
  if (!todoPanel) {
    router.push(`/projects/${id}/flow`)
    return
  }

  router.push({
    path: `/projects/${id}/flow`,
    query: {
      todoPanel,
      todoLabel: resolveTodoLabel(row),
      fromTodo: '1',
    },
  })
}

function goDeleteApprovals() {
  router.push('/project-delete-approvals')
}

function goNotifications(projectId?: number) {
  if (projectId) {
    router.push({ path: '/notifications', query: { project_id: String(projectId), message_type: 'REMINDER' } })
    return
  }
  router.push('/notifications')
}

onMounted(() => {
  void load()
})

const stopNotificationRefreshWatch = watch(
  () => notifications.listRefreshToken,
  async () => {
    if (!selectedTodo.value) return
    await refreshWorkbenchData()
    await loadLinkedNotifications()
  },
)

watch(
  () => notifications.stats,
  (value) => {
    if (!selectedTodo.value) return
    linkageStats.server_time = value.server_time
  },
  { deep: true },
)

onUnmounted(() => {
  stopNotificationRefreshWatch()
})
</script>

<style scoped>
.workbench-page {
  display: grid;
  gap: 16px;
}

.workbench-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 86px;
  padding: 22px 24px;
  border: 1px solid var(--zq-border);
  border-radius: 8px;
  background:
    linear-gradient(135deg, rgba(31, 78, 121, 0.94), rgba(23, 63, 99, 0.9)),
    var(--zq-primary);
  color: #fff;
  box-shadow: 0 10px 28px rgba(31, 78, 121, 0.12);
}

.workbench-hero p,
.workbench-hero h1 {
  margin: 0;
}

.workbench-hero p {
  color: rgba(255, 255, 255, 0.72);
  font-size: 13px;
  font-weight: 600;
}

.workbench-hero h1 {
  margin-top: 8px;
  font-size: 24px;
  line-height: 1.3;
}

.workbench-hero :deep(.el-tag) {
  color: #fff;
  border-color: rgba(255, 255, 255, 0.45);
  background: rgba(255, 255, 255, 0.12);
}

.workbench-grid {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  grid-template-areas:
    "create todo"
    "create linkage";
  gap: 14px;
  align-items: start;
}

.create-card {
  grid-area: create;
}

.todo-card {
  grid-area: todo;
}

.linkage-card {
  grid-area: linkage;
  min-height: 386px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.card-header-tip {
  color: #64748b;
  font-size: 12px;
  text-align: right;
}

.wide-table {
  width: 100%;
}

.wide-table :deep(.el-table__inner-wrapper),
.wide-table :deep(.el-scrollbar__view),
.wide-table :deep(table) {
  width: 100% !important;
}

.wide-table :deep(.cell) {
  white-space: nowrap;
  padding-left: 8px;
  padding-right: 8px;
}

.wide-table :deep(th.el-table__cell) {
  height: 42px;
}

.wide-table :deep(td.el-table__cell) {
  height: 44px;
}

.wide-table :deep(.el-button + .el-button) {
  margin-left: 8px;
}

.todo-table :deep(.el-table__body tr.current-row > td.el-table__cell) {
  background: #edf5ff;
}

.linkage-card :deep(.el-empty) {
  padding: 48px 0 56px;
}

.linkage-card :deep(.el-empty__description) {
  color: #64748b;
}

.summary-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.summary-metrics-compact {
  padding: 0;
}

.summary-metric {
  padding: 10px 12px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(31, 78, 121, 0.08);
}

.summary-metric span,
.summary-metric strong {
  display: block;
}

.summary-metric span {
  color: #64748b;
  font-size: 12px;
}

.summary-metric strong {
  margin-top: 8px;
  color: #1f4e79;
  font-size: 18px;
}

.linkage-tabs {
  margin-top: 16px;
}

.linkage-toolbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin: 12px 0 16px;
}

.linkage-filter {
  flex: 1;
}

.linkage-filter :deep(.filter-bar) {
  margin-bottom: 0;
}

.linkage-toolbar-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-top: 2px;
}

.linkage-content {
  display: grid;
  grid-template-columns: minmax(0, 1.7fr) 320px;
  gap: 16px;
  align-items: start;
}

.linkage-main,
.side-panel {
  border: 1px solid var(--zq-border-soft);
  border-radius: 10px;
  background: #fff;
}

.linkage-main {
  display: grid;
  gap: 16px;
}

.linkage-section-card {
  border-radius: 10px;
  min-height: 360px;
}

.linkage-section-card :deep(.el-card__body) {
  padding-top: 0;
  min-height: 292px;
  display: flex;
  flex-direction: column;
}

.projects-section-card {
  min-height: 360px;
}

.message-section-card :deep(.el-empty),
.projects-section-card :deep(.el-empty) {
  flex: 1;
  margin: 0;
}

.projects-section-card :deep(.el-table) {
  flex: 1;
}

.linkage-section-head,
.side-panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.linkage-section-head h3,
.side-panel-head h3 {
  margin: 0;
  font-size: 16px;
  color: #153a63;
}

.linkage-section-head p,
.side-panel-head p {
  margin: 6px 0 0;
  color: #64748b;
  font-size: 12px;
}

.linkage-side {
  display: grid;
  gap: 14px;
}

.side-panel {
  padding: 14px;
}

.linkage-card :deep(.el-card__body) {
  position: relative;
}

.linkage-card :deep(.el-card__body)::before {
  content: "";
  position: absolute;
  top: 12px;
  right: 18px;
  width: 188px;
  height: 188px;
  border-radius: 999px;
  background: radial-gradient(circle, rgba(31, 78, 121, 0.06), transparent 68%);
  pointer-events: none;
}

.flow-list,
.focus-list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.flow-list {
  display: grid;
  gap: 12px;
}

.flow-list li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 10px;
  border-bottom: 1px dashed var(--zq-border-soft);
}

.flow-list li:last-child {
  padding-bottom: 0;
  border-bottom: 0;
}

.flow-list span {
  color: #64748b;
  font-size: 13px;
}

.flow-list strong {
  color: #153a63;
  text-align: right;
}

.focus-list {
  display: grid;
  gap: 10px;
  padding-left: 18px;
  color: #475569;
  font-size: 13px;
  line-height: 1.6;
}

.flow-preview-panel {
  display: grid;
  gap: 14px;
}

.flow-preview-current {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  padding: 12px;
  border-radius: 10px;
  background: linear-gradient(180deg, #f8fbff 0%, #f4f8fd 100%);
  border: 1px solid rgba(31, 78, 121, 0.08);
}

.flow-preview-label {
  display: block;
  color: #64748b;
  font-size: 12px;
}

.flow-preview-current strong {
  display: block;
  margin-top: 8px;
  color: #153a63;
  font-size: 16px;
}

.flow-timeline {
  display: grid;
  gap: 0;
}

.flow-timeline-item {
  position: relative;
  display: grid;
  grid-template-columns: 22px 34px minmax(0, 1fr);
  gap: 12px;
  align-items: stretch;
  padding-bottom: 12px;
}

.flow-timeline-item:last-child {
  padding-bottom: 0;
}

.flow-timeline-line {
  position: relative;
  justify-self: center;
  width: 2px;
  height: 100%;
  background: rgba(148, 163, 184, 0.26);
}

.flow-timeline-item:last-child .flow-timeline-line {
  display: none;
}

.flow-timeline-card {
  width: 100%;
  min-width: 180px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  padding: 12px 14px;
  border: 1px solid var(--zq-border-soft);
  border-radius: 10px;
  background: #fff;
  transition: all 0.2s ease;
  word-break: normal;
  overflow-wrap: break-word;
  white-space: normal;
}

.flow-timeline-group {
  display: inline-flex !important;
  align-self: flex-start;
  width: auto;
  margin-bottom: 8px;
  padding: 2px 8px;
  border-radius: 999px;
  background: #eef4fb;
  color: #1f4e79;
  font-size: 12px;
  font-weight: 700;
}

.flow-timeline-card strong,
.flow-timeline-card span {
  display: block;
  width: 100%;
  word-break: normal;
  overflow-wrap: break-word;
  white-space: normal;
  line-height: 1.45;
}

.flow-timeline-card strong {
  color: #153a63;
  font-size: 14px;
}

.flow-timeline-card span:last-child {
  margin-top: 6px;
  color: #64748b;
  font-size: 12px;
}

.flow-timeline-item.is-done .flow-timeline-card {
  border-color: rgba(34, 197, 94, 0.18);
  background: #f2fbf5;
}

.flow-timeline-item.is-active .flow-timeline-card {
  border-color: rgba(31, 78, 121, 0.2);
  background: #edf5ff;
  box-shadow: 0 8px 20px rgba(31, 78, 121, 0.08);
}

.flow-timeline-item.is-active .flow-timeline-group {
  background: rgba(31, 78, 121, 0.12);
}

.flow-timeline-item.is-done .flow-timeline-line {
  background: rgba(34, 197, 94, 0.26);
}

.flow-preview-step {
  position: absolute;
  visibility: hidden;
}

.flow-preview-dot {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: 999px;
  background: #e2e8f0;
  color: #475569;
  font-weight: 700;
  font-size: 13px;
}

.flow-preview-step.is-done .flow-preview-dot {
  background: #22c55e;
  color: #fff;
}

.flow-preview-step.is-active .flow-preview-dot {
  background: var(--zq-primary);
  color: #fff;
}

.flow-preview-footer {
  display: grid;
  gap: 10px;
}

@media (max-width: 1200px) {
  .summary-metrics {
    grid-template-columns: repeat(3, minmax(90px, 1fr));
  }

  .linkage-content {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 960px) {
  .workbench-grid {
    grid-template-columns: 1fr;
    grid-template-areas:
      "create"
      "todo"
      "linkage";
  }

  .linkage-toolbar,
  .card-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .card-header-tip {
    text-align: left;
  }

  .summary-metrics {
    width: 100%;
    grid-template-columns: repeat(2, minmax(90px, 1fr));
  }

  .flow-preview-current {
    grid-template-columns: 1fr;
  }

  .flow-timeline-card {
    min-width: 0;
  }

  .linkage-toolbar-actions {
    padding-top: 0;
    flex-wrap: wrap;
  }
}
</style>
