<template>
  <div class="desktop-layout" :class="{ 'has-workflow': showWorkflow }">
    <aside class="nav"><MainMenu /></aside>
    <section class="content-shell">
      <header class="content-topbar">
        <div class="content-topbar__spacer"></div>
        <UserAccountBar />
      </header>
      <main class="main"><router-view /></main>
    </section>
    <aside class="workflow" v-if="showWorkflow"><WorkflowGuide :active-step="2" /></aside>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import MainMenu from '@/components/common/MainMenu.vue'
import UserAccountBar from '@/components/common/UserAccountBar.vue'
import WorkflowGuide from '@/components/workflow/WorkflowGuide.vue'

const route = useRoute()
const showWorkflow = computed(() => route.path.includes('/workorders/') || route.path.includes('/reviews'))
</script>
