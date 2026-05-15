<template>
  <DesktopLayout v-if="isDesktop" />
  <TabletLayout v-else-if="isTablet" />
  <MobileLayout v-else />
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import DesktopLayout from './DesktopLayout.vue'
import TabletLayout from './TabletLayout.vue'
import MobileLayout from './MobileLayout.vue'
import { useResponsive } from '@/composables/useResponsive'
import { useNotificationStore } from '@/store/notification'

const { isDesktop, isTablet } = useResponsive()
const notifications = useNotificationStore()

onMounted(() => {
  notifications.startPolling()
  notifications.connectSocket()
})

onUnmounted(() => {
  notifications.disconnectSocket()
  notifications.stopPolling()
})
</script>
