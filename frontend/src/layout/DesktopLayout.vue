<template>
  <div class="desktop-layout">
    <aside class="nav"><MainMenu /></aside>
    <main class="main"><router-view /></main>
    <aside class="workflow" v-if="showWorkflow"><WorkflowGuide :active-step="2" /></aside>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import MainMenu from '@/components/common/MainMenu.vue'
import WorkflowGuide from '@/components/workflow/WorkflowGuide.vue'

const route = useRoute()
const showWorkflow = computed(() => route.path.includes('/workorders/') || route.path.includes('/reviews'))
</script>
