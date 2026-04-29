<template>
  <div class="login-page">
    <el-card class="login-card">
      <h2>资产评估项目流程管理系统</h2>
      <el-form :model="form" @submit.prevent>
        <el-form-item label="账号">
          <el-input v-model="form.username" placeholder="请输入账号" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" show-password placeholder="请输入密码" />
        </el-form-item>
        <el-button type="primary" :loading="loading" @click="onLogin">登录</el-button>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import { login, me } from '@/api/auth'
import { useAuthStore } from '@/store/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const loading = ref(false)
const form = reactive({ username: 'zhongqin123', password: 'zhongqin123' })

async function onLogin() {
  try {
    loading.value = true
    auth.clearAuth()

    const token = await login(form)
    auth.setToken(token.access_token)
    auth.setUser(await me())

    const redirectTo = typeof route.query.redirect === 'string' ? route.query.redirect : '/dashboard'
    await router.replace(redirectTo)

    // Some production environments may keep the page on /login when route guards run concurrently.
    // If that happens, force a hard navigation so users can still enter the main app.
    if (router.currentRoute.value.path === '/login') {
      window.location.assign(redirectTo)
      return
    }

    ElMessage.success('登录成功')
  } catch {
    auth.clearAuth()
    const status = error?.response?.status
    if (status === 401) {
      ElMessage.error('登录失败，请检查账号密码')
      return
    }
    ElMessage.error('登录接口异常，请检查后端地址与返回格式')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page { min-height: 100vh; display: flex; align-items: center; justify-content: center; background: #f7f8fa; }
.login-card { width: 420px; }
</style>
