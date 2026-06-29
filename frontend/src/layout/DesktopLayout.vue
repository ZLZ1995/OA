<template>
  <div class="desktop-layout" :class="{ 'has-workflow': showWorkflow }">
    <DesktopShellBar v-if="desktopShell" />
    <aside class="nav"><MainMenu /></aside>
    <section class="content-shell">
      <header class="content-topbar">
        <div class="content-topbar__spacer"></div>
        <UserAccountBar v-if="!desktopEmbedded" :desktop-shell="desktopShell" />
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
import DesktopShellBar from '@/components/desktop/DesktopShellBar.vue'
import UserAccountBar from '@/components/common/UserAccountBar.vue'
import WorkflowGuide from '@/components/workflow/WorkflowGuide.vue'
import { isDesktopEmbedded, isDesktopShell } from '@/utils/desktop'

const route = useRoute()
const showWorkflow = computed(() => route.path.includes('/workorders/') || route.path.includes('/reviews'))
const desktopShell = isDesktopShell()
const desktopEmbedded = isDesktopEmbedded()
</script>
