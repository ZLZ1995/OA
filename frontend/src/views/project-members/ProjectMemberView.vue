<template>
  <el-card class="page-card" shadow="never">
    <template #header>项目成员管理</template>

    <el-form inline>
      <el-form-item label="项目">
        <el-select v-model="projectId" style="width: 260px" @change="loadMembers">
          <el-option v-for="p in projects" :key="p.id" :label="`${p.project_code} - ${p.project_name}`" :value="p.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="用户">
        <el-select v-model="newUserId" style="width: 220px">
          <el-option v-for="u in users" :key="u.id" :label="`${u.real_name}(${u.username})`" :value="u.id" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="onAdd">添加成员</el-button>
      </el-form-item>
    </el-form>

    <el-table :data="members" v-loading="loading">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="user_id" label="用户ID" width="100" />
      <el-table-column prop="member_role" label="成员角色" width="140" />
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button size="small" type="danger" plain @click="onDelete(row.id)">移除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { listProjects, type ProjectItem } from '@/api/projects'
import { listUsers, type UserItem } from '@/api/users'
import { createProjectMember, deleteProjectMember, listProjectMembers, type ProjectMemberItem } from '@/api/projectMembers'

const loading = ref(false)
const projects = ref<ProjectItem[]>([])
const users = ref<UserItem[]>([])
const members = ref<ProjectMemberItem[]>([])
const projectId = ref<number>()
const newUserId = ref<number>()

async function loadBase() {
  const [p, u] = await Promise.all([listProjects(), listUsers()])
  projects.value = p.items
  users.value = u.items
  projectId.value = p.items[0]?.id
  if (projectId.value) await loadMembers()
}

async function loadMembers() {
  if (!projectId.value) return
  loading.value = true
  try {
    members.value = (await listProjectMembers(projectId.value)).items
  } finally {
    loading.value = false
  }
}

async function onAdd() {
  if (!projectId.value || !newUserId.value) {
    ElMessage.warning('请选择项目和用户')
    return
  }
  await createProjectMember({ project_id: projectId.value, user_id: newUserId.value, member_role: 'MEMBER' })
  ElMessage.success('成员添加成功')
  newUserId.value = undefined
  await loadMembers()
}

async function onDelete(id: number) {
  await deleteProjectMember(id)
  ElMessage.success('成员已移除')
  await loadMembers()
}

onMounted(loadBase)
</script>
