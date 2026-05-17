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
      <button
        type="button"
        class="download-button"
        :disabled="downloading"
        @click="handleDownload"
      >
        {{ downloading ? '下载中...' : '下载 OA系统内部培训使用手册.docx' }}
      </button>
    </article>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { downloadHelpManual, getHelpSection, type HelpContentItem } from '@/api/help'

const items = ref<HelpContentItem[]>([])
const downloading = ref(false)

onMounted(async () => {
  items.value = (await getHelpSection('manual')).items || []
})

async function handleDownload() {
  downloading.value = true
  try {
    await downloadHelpManual()
    ElMessage.success('培训手册已开始下载')
  } catch {
    ElMessage.error('培训手册下载失败，请稍后重试')
  } finally {
    downloading.value = false
  }
}
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
  border: 0;
  border-radius: 10px;
  background: #1f4e79;
  color: #fff;
  font-weight: 600;
  text-decoration: none;
  white-space: nowrap;
  cursor: pointer;
}

.download-button:hover:not(:disabled) {
  background: #163a5d;
}

.download-button:disabled {
  cursor: not-allowed;
  opacity: 0.7;
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
