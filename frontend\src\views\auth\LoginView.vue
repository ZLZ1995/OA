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
const form = reactive({ username: '', password: '' })

function getErrorMessage(err: unknown): string {
  if (typeof err === 'object' && err !== null) {
    const maybeError = err as {
      message?: string
      response?: {
        status?: number
        data?: {
          detail?: string
          message?: string
        }
      }
    }
    return (
      maybeError.response?.data?.detail ||
      maybeError.response?.data?.message ||
      maybeError.message ||
      '登录失败，请稍后重试'
    )
  }
  return '登录失败，请稍后重试'
}

async function onLogin() {
  try {
    loading.value = true
    auth.clearAuth()

    const token = await login(form)
    auth.setToken(token.access_token)
    auth.setUser(await me())

    const profile = await auth.ensureUserLoaded()
    const isAdmin = (profile?.roles || []).includes('ADMIN')
    const redirectTo = typeof route.query.redirect === 'string' ? route.query.redirect : (isAdmin ? '/accounts' : '/dashboard')
    await router.replace(redirectTo)

    // Some production environments may keep the page on /login when route guards run concurrently.
    // If that happens, force a hard navigation so users can still enter the main app.
    if (router.currentRoute.value.path === '/login') {
      window.location.assign(redirectTo)
      return
    }

    ElMessage.success('登录成功')
  } catch (err) {
    auth.clearAuth()
    const status =
      typeof err === 'object' && err !== null
        ? (err as { response?: { status?: number } }).response?.status
        : undefined
    if (status === 401) {
      ElMessage.error(getErrorMessage(err))
      return
    }
    ElMessage.error(getErrorMessage(err))
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page { min-height: 100vh; display: flex; align-items: center; justify-content: center; background: #f7f8fa; }
.login-card { width: 420px; }
</style>
