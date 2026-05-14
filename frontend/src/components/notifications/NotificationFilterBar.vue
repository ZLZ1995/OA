<template>
  <el-form :inline="true" class="filter-bar">
    <el-form-item>
      <el-input
        :model-value="filters.keyword"
        placeholder="搜索标题/内容"
        clearable
        @update:model-value="update('keyword', $event)"
      />
    </el-form-item>
    <el-form-item>
      <el-select
        :model-value="filters.message_type"
        placeholder="消息类型"
        clearable
        style="width: 160px"
        @update:model-value="update('message_type', $event)"
      >
        <el-option label="催办消息" value="REMINDER" />
        <el-option label="流程消息" value="WORKFLOW" />
        <el-option label="系统通知" value="SYSTEM" />
      </el-select>
    </el-form-item>
    <el-form-item>
      <el-select
        :model-value="filters.priority"
        placeholder="优先级"
        clearable
        style="width: 140px"
        @update:model-value="update('priority', $event)"
      >
        <el-option label="普通" value="NORMAL" />
        <el-option label="重要" value="IMPORTANT" />
        <el-option label="紧急" value="URGENT" />
      </el-select>
    </el-form-item>
    <el-form-item>
      <el-button type="primary" @click="$emit('search')">筛选</el-button>
      <el-button @click="$emit('reset')">重置</el-button>
    </el-form-item>
  </el-form>
</template>

<script setup lang="ts">
type NotificationFilters = {
  keyword: string
  message_type: string
  priority: string
  project_id?: number
}

const props = defineProps<{ filters: NotificationFilters }>()

const emit = defineEmits<{
  (event: 'update:filters', value: NotificationFilters): void
  (event: 'search'): void
  (event: 'reset'): void
}>()

function update(key: keyof NotificationFilters, value: string) {
  emit('update:filters', { ...props.filters, [key]: value })
}
</script>

<style scoped>
.filter-bar {
  margin-bottom: 12px;
}
</style>
