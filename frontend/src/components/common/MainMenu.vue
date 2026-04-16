<template>
  <el-menu :default-active="active" class="menu" router>
    <el-menu-item v-for="item in APP_MENUS" :key="item.key" :index="item.path">{{ item.title }}</el-menu-item>
  </el-menu>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { APP_MENUS } from '@/constants/menus'

defineProps<{ compact?: boolean }>()
const route = useRoute()
const active = computed(() => route.path)
</script>
