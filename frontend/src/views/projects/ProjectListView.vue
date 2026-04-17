<template>
  <el-card class="page-card" shadow="never">
    <template #header>项目列表</template>
    <el-form inline @submit.prevent>
      <el-form-item label="项目编号">
        <el-input v-model="form.project_code" />
      </el-form-item>
      <el-form-item label="项目名称">
        <el-input v-model="form.project_name" />
      </el-form-item>
      <el-form-item label="客户名称">
        <el-input v-model="form.client_name" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="onCreate">新建项目</el-button>
      </el-form-item>
    </el-form>

    <el-table :data="rows" style="margin-top: 12px" v-loading="loading">
      <el-table-column prop="project_code" label="项目编号" />
      <el-table-column prop="project_name" label="项目名称" />
      <el-table-column prop="client_name" label="客户名称" />
      <el-table-column prop="project_leader_id" label="项目负责人ID" />
      <el-table-column prop="status" label="状态" />
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { createProject, listProjects, type ProjectItem } from '@/api/projects'
import { useAuthStore } from '@/store/auth'

const auth = useAuthStore()
const loading = ref(false)
const rows = ref<ProjectItem[]>([])

const form = reactive({
  project_code: '',
  project_name: '',
  client_name: ''
})

async function loadProjects() {
  loading.value = true
  try {
    const data = await listProjects()
    rows.value = data.items
  } finally {
    loading.value = false
  }
}

async function onCreate() {
  if (!auth.user?.id) {
    ElMessage.error('当前用户信息未加载')
    return
  }
  if (!form.project_code || !form.project_name || !form.client_name) {
    ElMessage.warning('请填写完整项目信息')
    return
  }
  await createProject({
    ...form,
    business_user_id: auth.user.id,
    project_leader_id: auth.user.id
  })
  ElMessage.success('项目创建成功')
  form.project_code = ''
  form.project_name = ''
  form.client_name = ''
  await loadProjects()
}

onMounted(loadProjects)
</script>
