<template>
  <el-row :gutter="12">
    <el-col :span="8">
      <el-card shadow="never">
        <template #header>项目创建区</template>
        <el-form label-width="88px">
          <el-form-item label="承接单位">
            <el-select v-model="form.undertaking_unit">
              <el-option label="中勤" value="中勤" />
              <el-option label="中立国际" value="中立国际" />
              <el-option label="中众" value="中众" />
              <el-option label="其他" value="其他" />
            </el-select>
          </el-form-item>
          <el-form-item label="项目名称"><el-input v-model="form.project_name" /></el-form-item>
          <el-form-item label="客户名称"><el-input v-model="form.client_name" /></el-form-item>
          <el-form-item><el-button type="primary" @click="onCreate">创建项目</el-button></el-form-item>
        </el-form>
      </el-card>
    </el-col>
    <el-col :span="8">
      <el-card shadow="never"><template #header>我的项目</template>
        <el-table :data="myProjects" size="small">
          <el-table-column prop="project_no" label="项目编号" />
          <el-table-column prop="project_name" label="项目名称" />
          <el-table-column prop="client_name" label="客户名称" />
          <el-table-column prop="current_step" label="当前步骤" />
          <el-table-column prop="status_display" label="状态" />
          <el-table-column label="操作" width="220">
            <template #default="{ row }">
              <el-button link type="primary" @click="goProject(row.id)">进入项目</el-button>
              <el-button link type="primary" :disabled="!row.can_edit" @click="editProject(row)">编辑</el-button>
              <el-button link type="warning" :disabled="!row.can_archive" @click="archive(row.id)">归档</el-button>
              <el-button link type="danger" :disabled="!row.can_delete" @click="remove(row.id)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </el-col>
    <el-col :span="8">
      <el-card shadow="never"><template #header>待办项目</template>
        <el-table :data="todoProjects" size="small">
          <el-table-column prop="project_no" label="项目编号" />
          <el-table-column prop="project_name" label="项目名称" />
          <el-table-column prop="client_name" label="客户名称" />
          <el-table-column prop="current_step" label="当前步骤" />
          <el-table-column prop="todo_action" label="待办事项" />
          <el-table-column label="操作" width="100"><template #default="{ row }"><el-button link type="primary" @click="goProject(row.id)">进入项目</el-button></template></el-table-column>
        </el-table>
      </el-card>
    </el-col>
  </el-row>
</template>
<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { getWorkbench, type WorkbenchProjectItem } from '@/api/workbench'
import { createProject, updateProject, deleteProject, archiveProject } from '@/api/projects'
import { useAuthStore } from '@/store/auth'
const router = useRouter(); const auth = useAuthStore()
const myProjects = ref<WorkbenchProjectItem[]>([]); const todoProjects = ref<WorkbenchProjectItem[]>([])
const form = reactive({ undertaking_unit:'中勤', project_name:'', client_name:'' })
async function load(){ const d=await getWorkbench(); myProjects.value=d.my_projects; todoProjects.value=d.todo_projects }
async function onCreate(){ const u=auth.user ?? await auth.ensureUserLoaded(); if(!u?.id) return
  await createProject({ undertaking_unit:form.undertaking_unit, project_name:form.project_name, client_name:form.client_name, business_user_id:u.id, project_leader_id:u.id })
  ElMessage.success('项目创建成功'); form.project_name=''; form.client_name=''; await load()
}
async function editProject(row:WorkbenchProjectItem){ await updateProject(row.id,{ project_name: row.project_name, client_name: row.client_name }); ElMessage.success('项目已更新'); await load() }
async function archive(id:number){ await archiveProject(id); ElMessage.success('项目已归档'); await load() }
async function remove(id:number){ await deleteProject(id); ElMessage.success('项目已删除'); await load() }
function goProject(id:number){ router.push(`/projects/${id}`) }
onMounted(load)
</script>
