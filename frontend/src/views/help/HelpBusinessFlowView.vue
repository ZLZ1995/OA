<template>
  <section class="help-page">
    <h2>整体业务流程</h2>
    <article v-for="item in items" :key="item.key" class="help-block">
      <h3>{{ item.title }}</h3>
      <img v-if="item.image_url" :src="item.image_url" :alt="item.title" class="help-image" />
      <p>{{ item.description }}</p>
    </article>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getHelpSection, type HelpContentItem } from '@/api/help'

const items = ref<HelpContentItem[]>([])

onMounted(async () => {
  items.value = (await getHelpSection('business-flow')).items || []
})
</script>

<style scoped>
.help-page { padding: 20px; }
.help-block { margin-bottom: 20px; padding: 16px; border: 1px solid #e2e8f0; border-radius: 12px; background: #fff; }
.help-image { width: 100%; border-radius: 8px; margin: 12px 0; object-fit: contain; }
</style>
