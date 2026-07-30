<template>
  <OaAgentChat
    :title="t.title"
    :subtitle="t.subtitle"
    :placeholder="t.placeholder"
    :empty-text="t.empty"
  />
</template>

<script setup lang="ts">
import OaAgentChat from '@/components/oa-agent/OaAgentChat.vue'

const t = {
  title: '\u004f\u0041 \u667a\u80fd\u5ba2\u670d',
  subtitle: '\u67e5\u8be2\u9879\u76ee\u8fdb\u5ea6\uff0c\u83b7\u53d6\u7b80\u6d01\u7684\u4e0b\u4e00\u6b65\u64cd\u4f5c\u6307\u5f15',
  placeholder: '\u8bf7\u8f93\u5165\u9879\u76ee\u540d\u79f0\u3001\u9879\u76ee\u7f16\u53f7\u6216\u5ba2\u6237\u540d\u79f0',
  empty: '\u53ef\u4ee5\u8bf4\uff1a\u67d0\u4e2a\u9879\u76ee\u73b0\u5728\u5230\u54ea\u4e00\u6b65\u4e86',
}
</script>
