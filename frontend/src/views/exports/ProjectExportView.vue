<template>
  <el-card shadow="never">
    <template #header>项目清单导出</template>

    <el-form :model="filters" label-width="116px" class="filter-form">
      <el-row :gutter="12">
        <el-col :span="6"><el-form-item label="项目编号"><el-input v-model="filters.project_no" clearable /></el-form-item></el-col>
        <el-col :span="6"><el-form-item label="项目名称"><el-input v-model="filters.project_name" clearable /></el-form-item></el-col>
        <el-col :span="6"><el-form-item label="报告编号"><el-input v-model="filters.report_no" clearable /></el-form-item></el-col>
        <el-col :span="6"><el-form-item label="负责人姓名"><el-input v-model="filters.project_leader_name" clearable /></el-form-item></el-col>
        <el-col :span="6">
          <el-form-item label="承接单位">
            <el-select v-model="filters.undertaking_unit" clearable>
              <el-option label="中勤" value="中勤" />
              <el-option label="中立国际" value="中立国际" />
              <el-option label="中众" value="中众" />
              <el-option label="其他" value="其他" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="6"><el-form-item label="签字评估师"><el-input v-model="filters.signer_name" clearable /></el-form-item></el-col>
        <el-col :span="6"><el-form-item label="收费金额下限"><el-input-number v-model="filters.amount_min" :min="0" :precision="2" style="width:100%" /></el-form-item></el-col>
        <el-col :span="6"><el-form-item label="收费金额上限"><el-input-number v-model="filters.amount_max" :min="0" :precision="2" style="width:100%" /></el-form-item></el-col>
        <el-col :span="6"><el-form-item label="归档开始日期"><el-date-picker v-model="filters.archive_date_from" value-format="YYYY-MM-DD" type="date" style="width:100%" /></el-form-item></el-col>
        <el-col :span="6"><el-form-item label="归档结束日期"><el-date-picker v-model="filters.archive_date_to" value-format="YYYY-MM-DD" type="date" style="width:100%" /></el-form-item></el-col>
        <el-col :span="12">
          <el-form-item>
            <el-button type="primary" @click="load">筛选</el-button>
            <el-button @click="reset">重置</el-button>
            <el-button type="success" @click="onExport">导出Excel</el-button>
          </el-form-item>
        </el-col>
      </el-row>
    </el-form>

    <el-table :data="rows" size="small" v-loading="loading" class="wide-table">
      <el-table-column prop="project_no" label="项目编号" min-width="140" />
      <el-table-column prop="project_name" label="项目名称" min-width="180" show-overflow-tooltip />
      <el-table-column prop="project_progress" label="项目进度" min-width="100" />
      <el-table-column prop="report_no" label="报告编号" min-width="140" />
      <el-table-column prop="project_leader_name" label="项目负责人姓名" min-width="130" />
      <el-table-column prop="undertaking_unit" label="承接单位" min-width="100" />
      <el-table-column prop="amount" label="收费金额" min-width="110" />
      <el-table-column prop="signer_names" label="签字评估师姓名" min-width="160" show-overflow-tooltip />
      <el-table-column prop="archive_date" label="归档日期" min-width="120" />
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { exportProjectRowsExcel, listProjectExportRows, type ProjectExportFilters, type ProjectExportItem } from '@/api/projectExports'

const loading = ref(false)
const rows = ref<ProjectExportItem[]>([])
const filters = reactive<ProjectExportFilters>({})

async function load() {
  loading.value = true
  try {
    rows.value = (await listProjectExportRows(filters)).items
  } finally {
    loading.value = false
  }
}

function reset() {
  Object.keys(filters).forEach(key => delete filters[key as keyof ProjectExportFilters])
  load()
}

async function onExport() {
  await exportProjectRowsExcel(filters)
  ElMessage.success('Excel已生成')
}

onMounted(load)
</script>

<style scoped>
.filter-form {
  margin-bottom: 12px;
}

.wide-table {
  width: 100%;
}
</style>
