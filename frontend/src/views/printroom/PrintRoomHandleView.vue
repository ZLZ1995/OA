<template>
  <el-card class="page-card" shadow="never">
    <template #header>文印室处理页</template>
    <el-form label-width="120px">
      <el-form-item label="纸质报告编号"><el-input placeholder="请输入编号" /></el-form-item>
      <el-form-item label="份数"><el-input-number :min="1" :max="99" /></el-form-item>
    </el-form>
    <el-button type="primary">登记出具</el-button>
  </el-card>
</template>
