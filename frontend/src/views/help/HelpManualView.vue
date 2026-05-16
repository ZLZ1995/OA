<template>
  <section class="help-page">
    <h2>使用说明</h2>
    <article v-for="item in items" :key="item.key" class="help-block">
      <h3>{{ item.title }}</h3>
      <p>{{ item.description }}</p>
    </article>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getHelpSection, type HelpContentItem } from '@/api/help'

const items = ref<HelpContentItem[]>([])

onMounted(async () => {
  items.value = (await getHelpSection('manual')).items || []
})
</script>

<style scoped>
.help-page { padding: 20px; }
.help-block { margin-bottom: 20px; padding: 16px; border: 1px solid #e2e8f0; border-radius: 12px; background: #fff; }
</style>
