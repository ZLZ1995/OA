<template>
  <section class="help-page">
    <h2>流程图总览</h2>
    <div v-if="items.length" class="card-grid">
      <article v-for="item in items" :key="item.key" class="help-card">
        <h3>{{ item.title }}</h3>
        <p>{{ item.description }}</p>
      </article>
    </div>
    <p v-else>暂无帮助内容。</p>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getHelpSection, type HelpContentItem } from '@/api/help'

const items = ref<HelpContentItem[]>([])

onMounted(async () => {
  items.value = (await getHelpSection('overview')).items || []
})
</script>

<style scoped>
.help-page { padding: 20px; }
.card-grid { display: grid; gap: 16px; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); }
.help-card { padding: 16px; border: 1px solid #e2e8f0; border-radius: 12px; background: #fff; }
</style>
