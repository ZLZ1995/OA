<template>
  <section class="help-page">
    <h2>流程图总览</h2>
    <div v-if="items.length" class="overview-layout">
      <div class="card-grid">
        <article v-for="item in items" :key="item.key" class="help-card">
          <h3>{{ item.title }}</h3>
          <p>{{ item.description }}</p>
          <button type="button" class="detail-link" @click="goToDetail(item.key)">
            查看详情
          </button>
        </article>
      </div>

      <aside v-if="previewImageUrl" class="preview-panel">
        <h3>总流程缩略图</h3>
        <img :src="previewImageUrl" alt="总流程缩略图" class="preview-image" />
        <p>用于快速查看项目主流程全貌，方便在总览页先建立整体认知。</p>
      </aside>
    </div>
    <p v-else>暂无帮助内容。</p>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getHelpSection, type HelpContentItem } from '@/api/help'

const router = useRouter()
const items = ref<HelpContentItem[]>([])
const previewImageUrl = computed(() => items.value[0]?.image_url || '')

const detailRouteMap: Record<string, string> = {
  'overview-1': '/help/business-flow',
  'overview-2': '/help/business-flow',
  'overview-3': '/help/role-flow',
}

onMounted(async () => {
  items.value = (await getHelpSection('overview')).items || []
})

function goToDetail(itemKey: string) {
  router.push(detailRouteMap[itemKey] || '/help/business-flow')
}
</script>

<style scoped>
.help-page { padding: 20px; }
.overview-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.7fr) minmax(320px, 1fr);
  gap: 20px;
  align-items: start;
}

.card-grid { display: grid; gap: 16px; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); }
.help-card { padding: 16px; border: 1px solid #e2e8f0; border-radius: 12px; background: #fff; }
.detail-link {
  margin-top: 12px;
  padding: 0;
  border: 0;
  background: none;
  color: #1f4e79;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.detail-link:hover {
  color: #163a5d;
  text-decoration: underline;
}
.preview-panel {
  padding: 18px;
  border: 1px solid #dbe5f0;
  border-radius: 14px;
  background: linear-gradient(180deg, #ffffff 0%, #f7fbff 100%);
  box-shadow: 0 12px 30px rgba(31, 78, 121, 0.08);
}

.preview-panel h3 {
  margin: 0 0 14px;
}

.preview-panel p {
  margin: 14px 0 0;
  color: #475569;
  line-height: 1.7;
}

.preview-image {
  display: block;
  width: 100%;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  background: #fff;
}

@media (max-width: 1100px) {
  .overview-layout {
    grid-template-columns: 1fr;
  }
}
</style>
