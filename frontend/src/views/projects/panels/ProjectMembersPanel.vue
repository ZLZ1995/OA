<template>
  <el-alert v-if="!canEdit" type="info" :closable="false" title="当前账号无项目成员管理权限，仅可查看。" show-icon style="margin-bottom: 12px"/>
  <el-form inline style="margin-bottom: 12px">
    <el-form-item label="成员角色">
      <el-select v-model="memberRole" style="width: 180px" :disabled="!canEdit">
        <el-option label="项目负责人" value="项目负责人" />
        <el-option label="项目组成员" value="项目组成员" />
      </el-select>
    </el-form-item>
    <el-form-item label="选择成员">
      <el-select v-model="selectedUserIds" multiple filterable placeholder="请选择成员" style="width: 360px" :disabled="!canEdit">
        <el-option v-for="u in users" :key="u.id" :label="`${u.real_name} (${u.username})`" :value="u.id" />
      </el-select>
    </el-form-item>
    <el-form-item>
      <el-button type="primary" :disabled="!canEdit" @click="addMembers">添加成员</el-button>
    </el-form-item>
  </el-form>

  <el-table :data="members" v-loading="loading">
    <el-table-column label="姓名">
      <template #default="{ row }">{{ row.real_name }}（{{ row.username }}）</template>
    </el-table-column>
    <el-table-column prop="member_role" label="角色" width="140" />
    <el-table-column prop="created_at" label="加入时间" width="200" />
    <el-table-column label="操作" width="120">
      <template #default="{ row }">
        <el-button type="danger" link :disabled="!canEdit" @click="removeMember(row)">移除</el-button>
      </template>
    </el-table-column>
  </el-table>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { batchCreateProjectMembers, deleteProjectMember, listProjectMembers, type ProjectMemberItem } from '@/api/projectMembers'
import { listUsers, type UserItem } from '@/api/users'

const props = defineProps<{ projectId: number; canEdit: boolean }>()
const emit = defineEmits<{ (e: 'changed'): void }>()

const loading = ref(false)
const members = ref<ProjectMemberItem[]>([])
const users = ref<UserItem[]>([])
const memberRole = ref('项目组成员')
const selectedUserIds = ref<number[]>([])

async function loadMembers() {
  loading.value = true
  try {
    members.value = (await listProjectMembers(props.projectId)).items
  } finally {
    loading.value = false
  }
}

async function addMembers() {
  if (!selectedUserIds.value.length) return ElMessage.warning('请选择成员')
  if (memberRole.value === '项目负责人' && members.value.some(m => m.member_role === '项目负责人')) {
    return ElMessage.warning('项目负责人只能有一位，请先移除原负责人')
  }
  await batchCreateProjectMembers({ project_id: props.projectId, user_ids: selectedUserIds.value, member_role: memberRole.value })
  ElMessage.success('成员添加成功')
  selectedUserIds.value = []
  await loadMembers()
  emit('changed')
}

async function removeMember(row: ProjectMemberItem) {
  await deleteProjectMember(row.id)
  ElMessage.success('成员已移除')
  await loadMembers()
  emit('changed')
}

onMounted(async () => {
  users.value = (await listUsers()).items
  await loadMembers()
})
</script>
