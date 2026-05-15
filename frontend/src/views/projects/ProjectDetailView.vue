<template>
  <el-card class="page-card" shadow="never" v-loading="loading">
    <template #header>&#39033;&#30446;&#35814;&#24773;</template>

    <el-empty v-if="!project" :description="t.empty" />
    <template v-else>
      <el-descriptions :column="2" border>
        <el-descriptions-item :label="t.projectCode">{{ project.project_code }}</el-descriptions-item>
        <el-descriptions-item :label="t.undertakingUnit">{{ project.undertaking_unit }}</el-descriptions-item>
        <el-descriptions-item :label="t.projectName">{{ project.project_name }}</el-descriptions-item>
        <el-descriptions-item :label="t.clientName">{{ project.client_name }}</el-descriptions-item>
        <el-descriptions-item :label="t.evalNature">{{ project.evaluation_business_nature || '-' }}</el-descriptions-item>
        <el-descriptions-item :label="t.reportType">{{ project.report_type }}</el-descriptions-item>
        <el-descriptions-item :label="t.baseDate">{{ project.valuation_base_date || '-' }}</el-descriptions-item>
        <el-descriptions-item :label="t.salesman">{{ project.business_salesman || '-' }}</el-descriptions-item>
        <el-descriptions-item :label="t.projectSource">{{ project.project_source_display }}</el-descriptions-item>
        <el-descriptions-item :label="t.projectLeader">{{ project.display_project_leader_name || project.project_leader_display_name || '-' }}</el-descriptions-item>
        <el-descriptions-item :label="t.textProjectLeader">{{ project.external_project_leader_name || '-' }}</el-descriptions-item>
        <el-descriptions-item :label="t.contractReviewStatus">{{ project.contract_review_status_display || '-' }}</el-descriptions-item>
        <el-descriptions-item :label="t.currentStatus">{{ project.status_display }}</el-descriptions-item>
        <el-descriptions-item :label="t.archivedAt">{{ project.archived_at || '-' }}</el-descriptions-item>
      </el-descriptions>

      <div class="actions">
        <el-button type="primary" @click="goFlow">{{ t.goFlow }}</el-button>
        <el-button @click="router.back()">{{ t.back }}</el-button>
      </div>
    </template>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getProject, type ProjectItem } from '@/api/projects'

const t = {
  empty: '\u6682\u65e0\u9879\u76ee\u6570\u636e',
  projectCode: '\u9879\u76ee\u7f16\u53f7',
  undertakingUnit: '\u627f\u63a5\u5355\u4f4d',
  projectName: '\u9879\u76ee\u540d\u79f0',
  clientName: '\u5ba2\u6237\u540d\u79f0',
  evalNature: '\u8bc4\u4f30\u4e1a\u52a1\u6027\u8d28',
  reportType: '\u62a5\u544a\u7c7b\u578b',
  baseDate: '\u8bc4\u4f30\u57fa\u51c6\u65e5',
  salesman: '\u9879\u76ee\u627f\u63a5\u4e1a\u52a1\u5458',
  projectSource: '\u9879\u76ee\u6765\u6e90',
  projectLeader: '\u9879\u76ee\u8d1f\u8d23\u4eba',
  textProjectLeader: '\u6587\u672c\u9879\u76ee\u8d1f\u8d23\u4eba',
  contractReviewStatus: '\u5408\u540c\u5ba1\u6838\u72b6\u6001',
  currentStatus: '\u9879\u76ee\u72b6\u6001',
  archivedAt: '\u5f52\u6863\u65f6\u95f4',
  goFlow: '\u8fdb\u5165\u6d41\u7a0b\u529e\u7406',
  back: '\u8fd4\u56de',
  loadFailed: '\u9879\u76ee\u8be6\u60c5\u52a0\u8f7d\u5931\u8d25',
}

const route = useRoute()
const router = useRouter()
const project = ref<ProjectItem | null>(null)
const loading = ref(false)

async function loadProject() {
  loading.value = true
  try {
    project.value = await getProject(route.params.id as string)
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || t.loadFailed)
  } finally {
    loading.value = false
  }
}

function goFlow() {
  router.push(`/projects/${route.params.id}/flow`)
}

onMounted(loadProject)
</script>

<style scoped>
.actions {
  margin-top: 16px;
  display: flex;
  gap: 8px;
}
</style>
