<template>
  <el-card class="page-card" shadow="never">
    <template #header>首页工作台</template>
    <el-row :gutter="12">
      <el-col :span="12"><el-statistic title="待我办理" :value="12" /></el-col>
      <el-col :span="12"><el-statistic title="我创建的工单" :value="6" /></el-col>
    </el-row>
  </el-card>
</template>
