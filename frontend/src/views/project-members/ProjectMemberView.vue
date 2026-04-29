<template>
  <el-card class="page-card" shadow="never">
    <template #header>项目成员管理</template>

    <el-form inline>
      <el-form-item label="项目">
        <el-select v-model="projectId" style="width: 260px" @change="loadMembers">
          <el-option v-for="p in projects" :key="p.id" :label="`${p.project_code} - ${p.project_name}`" :value="p.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="成员角色">
        <el-select v-model="memberRole" style="width: 160px">
          <el-option label="项目负责人" value="项目负责人" />
          <el-option label="项目组成员" value="项目组成员" />
        </el-select>
      </el-form-item>
      <el-form-item label="用户">
        <el-select v-model="newUserIds" multiple collapse-tags style="width: 360px">
          <el-option v-for="u in users" :key="u.id" :label="`${u.real_name}（${u.username}）`" :value="u.id" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="onAdd">批量添加成员</el-button>
      </el-form-item>
    </el-form>

    <el-table :data="members" v-loading="loading">
      <el-table-column prop="real_name" label="姓名" width="140" />
      <el-table-column prop="username" label="账号" width="160" />
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
import { batchCreateProjectMembers, deleteProjectMember, listProjectMembers, type ProjectMemberItem } from '@/api/projectMembers'

const loading = ref(false)
const projects = ref<ProjectItem[]>([])
const users = ref<UserItem[]>([])
const members = ref<ProjectMemberItem[]>([])
const projectId = ref<number>()
const newUserIds = ref<number[]>([])
const memberRole = ref<'项目负责人' | '项目组成员'>('项目组成员')

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
  if (!projectId.value || newUserIds.value.length === 0) {
    ElMessage.warning('请选择项目和用户')
    return
  }
  await batchCreateProjectMembers({ project_id: projectId.value, user_ids: newUserIds.value, member_role: memberRole.value })
  ElMessage.success('成员添加成功')
  newUserIds.value = []
  await loadMembers()
}

async function onDelete(id: number) {
  await deleteProjectMember(id)
  ElMessage.success('成员已移除')
  await loadMembers()
}

onMounted(loadBase)
</script>
