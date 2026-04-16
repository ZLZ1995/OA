<template>
  <DesktopLayout v-if="isDesktop" />
  <TabletLayout v-else-if="isTablet" />
  <MobileLayout v-else />
</template>

<script setup lang="ts">
import DesktopLayout from './DesktopLayout.vue'
import TabletLayout from './TabletLayout.vue'
import MobileLayout from './MobileLayout.vue'
import { useResponsive } from '@/composables/useResponsive'

const { isDesktop, isTablet } = useResponsive()
</script>
