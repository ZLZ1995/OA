<template>
  <el-card class="page-card" shadow="never">
    <template #header>审核处理页</template>
    <el-form label-width="90px">
      <el-form-item label="审核意见">
        <el-input type="textarea" :rows="4" placeholder="请输入审核意见" />
      </el-form-item>
    </el-form>
    <el-space>
      <el-button type="success">通过</el-button>
      <el-button type="danger" plain>退回</el-button>
    </el-space>
  </el-card>
</template>
