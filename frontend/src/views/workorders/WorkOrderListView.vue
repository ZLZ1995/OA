<template>
  <el-card class="page-card" shadow="never">
    <template #header>工单列表</template>
    <el-form inline @submit.prevent>
      <el-form-item label="工单号">
        <el-input v-model="form.work_order_no" />
      </el-form-item>
      <el-form-item label="标题">
        <el-input v-model="form.title" />
      </el-form-item>
      <el-form-item label="项目">
        <el-select v-model="form.project_id" placeholder="选择项目" style="width: 220px">
          <el-option
            v-for="project in projectOptions"
            :key="project.id"
            :label="`${project.project_code} - ${project.project_name}`"
            :value="project.id"
          />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="onCreate">创建工单</el-button>
      </el-form-item>
    </el-form>

    <el-table :data="rows" style="margin-top: 12px" v-loading="loading">
      <el-table-column prop="work_order_no" label="工单号" />
      <el-table-column prop="title" label="标题" />
      <el-table-column prop="project_id" label="项目ID" />
      <el-table-column prop="current_status" label="状态" />
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { listProjects, type ProjectItem } from '@/api/projects'
import { createWorkOrder, listWorkOrders, type WorkOrderItem } from '@/api/workorders'

const loading = ref(false)
const rows = ref<WorkOrderItem[]>([])
const projectOptions = ref<ProjectItem[]>([])

const form = reactive({
  work_order_no: '',
  title: '',
  project_id: undefined as number | undefined
})

async function loadData() {
  loading.value = true
  try {
    const [woData, projectData] = await Promise.all([listWorkOrders(), listProjects()])
    rows.value = woData.items
    projectOptions.value = projectData.items
  } finally {
    loading.value = false
  }
}

async function onCreate() {
  if (!form.work_order_no || !form.title || !form.project_id) {
    ElMessage.warning('请填写完整工单信息')
    return
  }
  await createWorkOrder({
    work_order_no: form.work_order_no,
    title: form.title,
    project_id: form.project_id
  })
  ElMessage.success('工单创建成功')
  form.work_order_no = ''
  form.title = ''
  form.project_id = undefined
  await loadData()
}

onMounted(loadData)
</script>
