<template>
  <section class="help-page">
    <h2>使用说明</h2>

    <article v-for="item in items" :key="item.key" class="help-block">
      <h3>{{ item.title }}</h3>
      <p>{{ item.description }}</p>
    </article>

    <article class="download-block">
      <div>
        <h3>文件下载区</h3>
        <p>可下载《OA系统内部培训使用手册》用于内部培训、流程讲解和日常使用参考。</p>
      </div>
      <a
        class="download-button"
        :href="manualDownloadUrl"
        target="_blank"
        rel="noopener noreferrer"
      >
        下载 OA系统内部培训使用手册.docx
      </a>
    </article>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { getHelpManualDownloadUrl, getHelpSection, type HelpContentItem } from '@/api/help'

const items = ref<HelpContentItem[]>([])
const manualDownloadUrl = computed(() => getHelpManualDownloadUrl())

onMounted(async () => {
  items.value = (await getHelpSection('manual')).items || []
})
</script>

<style scoped>
.help-page { padding: 20px; }

.help-block,
.download-block {
  margin-bottom: 20px;
  padding: 16px;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  background: #fff;
}

.download-block {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.download-block p {
  margin: 8px 0 0;
  color: #475569;
  line-height: 1.7;
}

.download-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 280px;
  padding: 12px 18px;
  border-radius: 10px;
  background: #1f4e79;
  color: #fff;
  font-weight: 600;
  text-decoration: none;
  white-space: nowrap;
}

.download-button:hover {
  background: #163a5d;
}

@media (max-width: 900px) {
  .download-block {
    flex-direction: column;
    align-items: flex-start;
  }

  .download-button {
    width: 100%;
    min-width: 0;
  }
}
</style>
