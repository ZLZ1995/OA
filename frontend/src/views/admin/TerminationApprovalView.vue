<template>
  <el-card shadow="never">
    <template #header>项目终止/废止审核</template>
    <el-table :data="rows" v-loading="loading" size="small" class="wide-table">
      <el-table-column prop="project_no" label="项目编号" min-width="132" show-overflow-tooltip />
      <el-table-column prop="project_name" label="项目名称" min-width="160" show-overflow-tooltip />
      <el-table-column prop="client_name" label="客户名称" min-width="150" show-overflow-tooltip />
      <el-table-column prop="project_leader_name" label="项目负责人" min-width="110" show-overflow-tooltip />
      <el-table-column prop="termination_reason" label="终止/废止原因" min-width="260" show-overflow-tooltip />
      <el-table-column label="操作" width="180">
        <template #default="{ row }">
          <el-button link type="primary" @click="goProject(row.id)">进入项目</el-button>
          <el-button link type="danger" @click="approve(row)">允许终止/废止</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import { getWorkbench, type WorkbenchProjectItem } from '@/api/workbench'
import { approveProjectTermination } from '@/api/projects'

const router = useRouter()
const loading = ref(false)
const allTodos = ref<WorkbenchProjectItem[]>([])
const rows = computed(() => allTodos.value.filter(item => item.can_approve_termination))

async function load() {
  loading.value = true
  try {
    allTodos.value = (await getWorkbench()).todo_projects
  } finally {
    loading.value = false
  }
}

async function approve(row: WorkbenchProjectItem) {
  await ElMessageBox.confirm(row.termination_reason || '未填写原因', '确认允许项目终止/废止', {
    confirmButtonText: '允许终止/废止',
    cancelButtonText: '取消',
    type: 'warning'
  })
  await approveProjectTermination(row.id)
  ElMessage.success('已允许终止/废止')
  await load()
}

function goProject(id: number) {
  router.push(`/projects/${id}/flow`)
}

onMounted(load)
</script>

<style scoped>
.wide-table {
  width: 100%;
}
</style>
