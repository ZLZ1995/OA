<template>
  <div class="menu-wrapper">
    <div class="menu-brand">
      <div class="brand-badge">中勤</div>
      <div>
        <strong>项目工作台</strong>
        <span>流程管理系统</span>
      </div>
    </div>
    <el-menu :default-active="active" class="menu" router>
      <el-menu-item v-for="item in visibleMenus" :key="item.key" :index="item.path">
        <span>{{ item.title }}</span>
        <el-badge
          v-if="item.key === 'notifications' && unreadCount > 0"
          :value="unreadCount"
          :max="99"
          class="menu-badge"
        />
      </el-menu-item>
    </el-menu>
    <div class="logout-zone">
      <el-button plain class="feedback-btn" @click="feedbackVisible = true">问题反馈</el-button>
      <el-button type="danger" plain class="logout-btn" @click="onLogout">退出登录</el-button>
    </div>
    <el-dialog v-model="feedbackVisible" title="问题反馈" width="520px">
      <el-form label-width="120px">
        <el-form-item label="项目编号">
          <el-input v-model="feedbackForm.project_no" placeholder="请输入项目编号" />
        </el-form-item>
        <el-form-item label="流程环节">
          <el-select v-model="feedbackForm.process_step" placeholder="请选择流程环节" style="width: 100%">
            <el-option v-for="step in processSteps" :key="step" :label="step" :value="step" />
          </el-select>
        </el-form-item>
        <el-form-item label="问题详细情况">
          <el-input v-model="feedbackForm.detail" type="textarea" :rows="5" placeholder="请描述问题详细情况" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="feedbackVisible = false">取消</el-button>
        <el-button type="primary" :loading="feedbackSubmitting" @click="submitFeedback">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import { createIssueFeedback } from '@/api/issueFeedbacks'
import { useNotificationStore } from '@/store/notification'

const BUSINESS_MENUS = [{ key: 'dashboard', title: '项目工作台', path: '/workbench' }]
const SHARED_MENUS = [{ key: 'notifications', title: '消息中心', path: '/notifications' }]
const ADMIN_MENUS = [
  { key: 'accounts', title: '账号管理', path: '/accounts' },
  { key: 'termination-approvals', title: '终止/废止审核', path: '/termination-approvals' },
  { key: 'project-delete-approvals', title: '项目删除审核', path: '/project-delete-approvals' },
  { key: 'project-conflicts', title: '项目冲突提醒', path: '/project-conflicts' },
  { key: 'issue-feedbacks', title: '问题反馈', path: '/issue-feedbacks' },
  { key: 'project-exports', title: '项目清单导出', path: '/project-exports' },
]
const processSteps = ['项目创建', '项目组成员', '合同初稿上传', '合同初稿审核', '报告送审', '一审', '二审', '三审', '报告出具', '报告邮寄', '发票开具', '报告归档', '已归档', '其他']

defineProps<{ compact?: boolean }>()
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const notifications = useNotificationStore()
const isAdmin = computed(() => (auth.user?.roles || []).includes('ADMIN'))
const visibleMenus = computed(() => (isAdmin.value ? [...SHARED_MENUS, ...ADMIN_MENUS] : [...BUSINESS_MENUS, ...SHARED_MENUS]))
const active = computed(() => route.path)
const unreadCount = computed(() => notifications.unreadCount)
const feedbackVisible = ref(false)
const feedbackSubmitting = ref(false)
const feedbackForm = reactive({ project_no: '', process_step: '', detail: '' })

function onLogout() {
  notifications.disconnectSocket()
  notifications.stopPolling()
  auth.clearAuth()
  router.push('/login')
}

async function submitFeedback() {
  if (!feedbackForm.project_no.trim() || !feedbackForm.process_step || !feedbackForm.detail.trim()) {
    ElMessage.warning('请完整填写项目编号、流程环节和问题详细情况')
    return
  }
  feedbackSubmitting.value = true
  try {
    await createIssueFeedback({
      project_no: feedbackForm.project_no.trim(),
      process_step: feedbackForm.process_step,
      detail: feedbackForm.detail.trim(),
    })
    feedbackForm.project_no = ''
    feedbackForm.process_step = ''
    feedbackForm.detail = ''
    feedbackVisible.value = false
    ElMessage.success('提交成功')
  } finally {
    feedbackSubmitting.value = false
  }
}
</script>

<style scoped>
.menu-wrapper {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #fff;
}

.menu-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 76px;
  padding: 14px 12px;
  border-bottom: 1px solid var(--zq-border-soft);
}

.brand-badge {
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  border-radius: 8px;
  color: #fff;
  background: var(--zq-primary);
  font-size: 13px;
  font-weight: 700;
}

.menu-brand strong,
.menu-brand span {
  display: block;
  line-height: 1.4;
}

.menu-brand strong {
  font-size: 14px;
  color: var(--zq-text);
}

.menu-brand span {
  font-size: 12px;
  color: var(--zq-muted);
}

.menu {
  flex: 1;
  overflow: auto;
  border-right: 0;
}

.menu :deep(.el-menu-item) {
  height: 44px;
  margin: 6px 10px;
  border-radius: 6px;
  color: #475569;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.menu :deep(.el-menu-item.is-active) {
  color: var(--zq-primary);
  background: var(--zq-primary-soft);
}

.menu :deep(.el-menu-item.is-active::before) {
  content: "";
  width: 3px;
  height: 20px;
  position: absolute;
  left: 0;
  border-radius: 999px;
  background: var(--zq-primary);
}

.logout-zone {
  padding: 12px;
  border-top: 1px solid var(--zq-border-soft);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.logout-btn,
.feedback-btn {
  width: 100%;
  margin-left: 0;
}

.menu-badge {
  margin-left: 10px;
}
</style>
