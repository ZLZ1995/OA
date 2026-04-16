<template>
  <el-card shadow="never" class="workflow-guide">
    <template #header>
      <div class="title">工单流程导览</div>
    </template>
    <el-steps direction="vertical" :active="activeStep" finish-status="success">
      <el-step v-for="(step, idx) in steps" :key="step" :title="step" :description="descriptions[idx]" />
    </el-steps>
  </el-card>
</template>

<script setup lang="ts">
const props = defineProps<{ activeStep?: number }>()

const steps = ['项目创建', '工单创建', '合同上传', '一审', '二审', '三审', '文印室出具']
const descriptions = ['已发起', '处理中', '待处理', '返回负责人', '返回负责人', '转文印室', '纸质报告']
const activeStep = props.activeStep ?? 1
</script>

<style scoped>
.workflow-guide { height: 100%; overflow: auto; }
.title { font-weight: 600; }
</style>
