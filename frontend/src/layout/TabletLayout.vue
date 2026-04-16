<template>
  <div class="tablet-layout">
    <header class="top"><MainMenu compact /></header>
    <main class="main"><router-view /></main>
    <el-drawer v-model="open" title="流程导览" direction="rtl" size="35%">
      <WorkflowGuide :active-step="2" />
    </el-drawer>
    <el-button class="workflow-btn" type="primary" @click="open = true">流程导览</el-button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import MainMenu from '@/components/common/MainMenu.vue'
import WorkflowGuide from '@/components/workflow/WorkflowGuide.vue'

const open = ref(false)
</script>
