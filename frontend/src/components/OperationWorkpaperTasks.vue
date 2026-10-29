<template>
  <section v-if="items.length" class="workpaper-tasks">
    <h4>操作类底稿待办（与三审并行）</h4>
    <el-table :data="items" size="small">
      <el-table-column prop="project_code" label="项目编号" />
      <el-table-column prop="project_name" label="项目名称" show-overflow-tooltip />
      <el-table-column label="操作"><template #default="{ row }">
        <el-button link type="primary" @click="router.push({ path: `/projects/${row.project_id}/flow`, query: { todoPanel: row.panel } })">
          {{ row.panel === 'operationWorkpaperReview' ? '进入底稿审核' : '提交 / 补充底稿' }}
        </el-button>
      </template></el-table-column>
    </el-table>
  </section>
</template>
<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import http from '@/api/http'
import { useNotificationStore } from '@/store/notification'
const router = useRouter()
const notices = useNotificationStore()
const items = ref<any[]>([])
async function load() { items.value = (await http.get('/operation-workpapers/tasks')).data }
onMounted(() => load().catch(() => {}))
watch(() => notices.listRefreshToken, () => load().catch(() => {}))
</script>
<style scoped>.workpaper-tasks { margin: 18px 0; }</style>
