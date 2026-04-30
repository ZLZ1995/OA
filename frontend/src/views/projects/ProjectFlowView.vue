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

        <el-empty v-else description="暂无项目数据" />

        <el-card v-if="selectedNode" shadow="never" style="margin-top: 12px">
          <template #header>{{ selectedNode.label }}</template>
          <p>{{ selectedNode.desc }}</p>
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
import { ElMessage } from 'element-plus'
import { getProjectFlow, type ProjectFlowData } from '@/api/projectFlow'

const flowNodes = [
  { key: 'basic', label: '项目基本信息', desc: '查看项目基本信息与当前状态。' },
  { key: 'members', label: '项目组成员', desc: '维护项目组成员与职责分工。' },
  { key: 'contract', label: '合同上传', desc: '上传与确认项目合同材料。' },
  { key: 'review', label: '报告送审', desc: '提交报告并推进审核流程。' },
  { key: 'issue', label: '报告出具', desc: '完成报告出具与结果确认。' },
  { key: 'invoice', label: '发票开具', desc: '处理发票开具与回传信息。' },
  { key: 'archive', label: '报告归档', desc: '归档项目资料并完成收尾。' }
]

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
const flow = ref<ProjectFlowData | null>(null)
const activeNode = ref(flowNodes[0].key)
const selectedNode = computed(() => flowNodes.find((n) => n.key === activeNode.value) ?? flowNodes[0])
const activeFlowStep = computed(() => {
  const current = flow.value?.project.current_step
  if (!current) return 0
  const normalized = stepAliasMap[current] ?? current
  const idx = stepTimeline.indexOf(normalized)
  return idx >= 0 ? idx : 0
})

function onSelectNode(key: string) {
  activeNode.value = key
}

async function load() {
  try {
    flow.value = await getProjectFlow(Number(route.params.id))
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '无权查看该项目')
  }
}

onMounted(load)
</script>
