<template>
  <div class="mobile-layout">
    <header class="top-bar">
      <el-button text @click="menuOpen = true">菜单</el-button>
      <span class="title">资产评估流程</span>
      <el-button text @click="flowOpen = true">流程</el-button>
    </header>
    <main class="main"><router-view /></main>

    <el-drawer v-model="menuOpen" title="导航" direction="ltr" size="80%">
      <MainMenu compact />
    </el-drawer>
    <el-drawer v-model="flowOpen" title="流程导览" direction="btt" size="70%">
      <WorkflowGuide :active-step="2" />
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import MainMenu from '@/components/common/MainMenu.vue'
import WorkflowGuide from '@/components/workflow/WorkflowGuide.vue'

const menuOpen = ref(false)
const flowOpen = ref(false)
</script>
