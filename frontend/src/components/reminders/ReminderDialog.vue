<template>
  <el-dialog :model-value="modelValue" title="发起催办" width="460px" @close="$emit('update:modelValue', false)">
    <el-form label-position="top">
      <el-form-item label="补充说明">
        <el-input
          :model-value="comment"
          type="textarea"
          :rows="4"
          maxlength="2000"
          show-word-limit
          placeholder="可选填写补充说明"
          @update:model-value="$emit('update:comment', String($event ?? ''))"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="$emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="$emit('submit')">发送催办</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
defineProps<{
  modelValue: boolean
  comment: string
  submitting?: boolean
}>()

defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'update:comment', value: string): void
  (e: 'submit'): void
}>()
</script>
