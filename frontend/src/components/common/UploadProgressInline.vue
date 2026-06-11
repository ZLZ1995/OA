<template>
  <div v-if="progress" class="upload-progress-inline">
    <div class="upload-progress-inline__header">
      <span class="upload-progress-inline__name">{{ progress.fileName || '当前文件' }}</span>
      <span class="upload-progress-inline__status">{{ statusText }}</span>
    </div>
    <el-progress
      :percentage="progress.percentage"
      :status="progress.status === 'error' ? 'exception' : progress.status === 'success' ? 'success' : undefined"
      :stroke-width="10"
    />
    <div v-if="progress.errorMessage" class="upload-progress-inline__error">
      {{ progress.errorMessage }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { UploadProgressState } from '@/types/upload'

const props = defineProps<{
  progress?: UploadProgressState | null
}>()

const statusText = computed(() => {
  if (!props.progress) return ''
  if (props.progress.status === 'success') return '上传完成'
  if (props.progress.status === 'error') return '上传失败'
  if (props.progress.status === 'uploading') return `上传中 ${props.progress.percentage}%`
  return '等待上传'
})
</script>

<style scoped>
.upload-progress-inline {
  margin-top: 10px;
  padding: 10px 12px;
  border: 1px solid #e4ebf3;
  border-radius: 8px;
  background: #fbfdff;
}

.upload-progress-inline__header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
  font-size: 12px;
}

.upload-progress-inline__name {
  color: #35536b;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.upload-progress-inline__status {
  color: #6f8192;
  white-space: nowrap;
}

.upload-progress-inline__error {
  margin-top: 6px;
  color: #d03050;
  font-size: 12px;
}
</style>
