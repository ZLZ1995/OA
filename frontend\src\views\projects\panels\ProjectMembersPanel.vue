<template>
  <el-alert
    v-if="!canEdit"
    type="info"
    :closable="false"
    title="当前账号无项目成员管理权限，仅可查看。"
    show-icon
    style="margin-bottom: 12px"
  />

  <el-form inline class="member-form">
    <el-form-item label="成员角色">
      <el-select v-model="memberRole" style="width: 180px" :disabled="!canEdit">
        <el-option v-for="role in memberRoles" :key="role" :label="role" :value="role" />
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
    <el-table-column label="姓名" min-width="140">
      <template #default="{ row }">{{ row.real_name }}（{{ row.username }}）</template>
    </el-table-column>
    <el-table-column label="角色" min-width="180">
      <template #default="{ row }">
        <el-select
          :model-value="row.member_role"
          style="width: 160px"
          :disabled="!canEdit"
          @change="(role: string) => updateRole(row, role)"
        >
          <el-option v-for="role in memberRoles" :key="role" :label="role" :value="role" />
        </el-select>
      </template>
    </el-table-column>
    <el-table-column prop="created_at" label="加入时间" width="200" />
    <el-table-column label="操作" width="120">
      <template #default="{ row }">
        <el-button type="danger" link :disabled="!canEdit" @click="removeMember(row)">移除</el-button>
      </template>
    </el-table-column>
  </el-table>

  <div class="footer-actions">
    <el-button type="primary" :disabled="!canEdit" @click="saveAndNext">保存并进入下一步</el-button>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  batchCreateProjectMembers,
  completeProjectMembers,
  deleteProjectMember,
  listProjectMembers,
  updateProjectMember,
  type ProjectMemberItem
} from '@/api/projectMembers'
import { listUsers, type UserItem } from '@/api/users'

const props = defineProps<{ projectId: number; canEdit: boolean }>()
const emit = defineEmits<{ (e: 'changed'): void }>()

const memberRoles = ['项目负责人', '项目组成员']
const loading = ref(false)
const members = ref<ProjectMemberItem[]>([])
const users = ref<UserItem[]>([])
const memberRole = ref('项目组成员')
const selectedUserIds = ref<number[]>([])
const hasLeader = computed(() => members.value.some((member) => member.member_role === '项目负责人'))

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
  await batchCreateProjectMembers({ project_id: props.projectId, user_ids: selectedUserIds.value, member_role: memberRole.value })
  ElMessage.success('成员添加成功')
  selectedUserIds.value = []
  await loadMembers()
  emit('changed')
}

async function updateRole(row: ProjectMemberItem, memberRole: string) {
  if (row.member_role === memberRole) return
  await updateProjectMember(row.id, { member_role: memberRole })
  ElMessage.success('成员角色已更新')
  await loadMembers()
  emit('changed')
}

async function removeMember(row: ProjectMemberItem) {
  await deleteProjectMember(row.id)
  ElMessage.success('成员已移除')
  await loadMembers()
  emit('changed')
}

async function saveAndNext() {
  if (!hasLeader.value) {
    return ElMessage.warning('每个项目至少需要一名项目负责人')
  }
  await completeProjectMembers(props.projectId)
  ElMessage.success('项目成员已保存，已进入合同上传')
  emit('changed')
}

onMounted(async () => {
  users.value = (await listUsers()).items
  await loadMembers()
})
</script>

<style scoped>
.member-form {
  margin-bottom: 12px;
}

.footer-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
