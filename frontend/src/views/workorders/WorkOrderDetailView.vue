<template>
  <el-card class="page-card" shadow="never">
    <template #header>工单详情</template>
    <el-space wrap>
      <el-button type="primary">上传文件</el-button>
      <el-button>查看历史版本</el-button>
      <el-button>查看审核意见</el-button>
      <el-button type="success">提交流程</el-button>
      <el-button type="danger" plain>退回流程</el-button>
    </el-space>
    <el-table :data="files" style="margin-top: 12px">
      <el-table-column prop="name" label="文件名" />
      <el-table-column prop="version" label="版本号" />
      <el-table-column prop="uploader" label="上传人" />
      <el-table-column prop="time" label="上传时间" />
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
const files = [{ name: '评估报告_v1.docx', version: 'v1', uploader: 'zhangsan', time: '2026-04-16 10:00' }]
</script>
