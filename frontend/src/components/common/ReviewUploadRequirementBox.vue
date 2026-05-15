<template>
  <aside class="requirement-box">
    <div class="requirement-title">{{ REVIEW_SUBMIT_REQUIREMENTS_TITLE }}</div>
    <ol class="requirement-list">
      <li v-for="item in REVIEW_SUBMIT_REQUIREMENTS_ITEMS" :key="item">
        {{ item }}
      </li>
    </ol>
    <p class="requirement-warning">{{ REVIEW_SUBMIT_REQUIREMENTS_WARNING }}</p>
  </aside>
</template>

<script setup lang="ts">
import {
  REVIEW_SUBMIT_REQUIREMENTS_ITEMS,
  REVIEW_SUBMIT_REQUIREMENTS_TITLE,
  REVIEW_SUBMIT_REQUIREMENTS_WARNING,
} from '@/constants/reviewRequirements'
</script>

<style scoped>
.requirement-box {
  flex: 1;
  min-width: 320px;
  padding: 12px 14px;
  border: 1px solid #dbe7f5;
  border-radius: 10px;
  background: linear-gradient(180deg, #f8fbff 0%, #f3f8ff 100%);
  color: #334155;
}

.requirement-title {
  margin-bottom: 8px;
  font-size: 14px;
  font-weight: 700;
  color: #1e3a5f;
}

.requirement-list {
  margin: 0;
  padding-left: 18px;
  display: grid;
  gap: 4px;
  line-height: 1.6;
}

.requirement-warning {
  margin: 10px 0 0;
  color: #c2410c;
  font-weight: 600;
  line-height: 1.6;
}

@media (max-width: 900px) {
  .requirement-box {
    min-width: 100%;
  }
}
</style>
