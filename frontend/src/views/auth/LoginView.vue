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
        <el-form-item>
          <el-space wrap>
            <el-button type="primary" :loading="loading" @click="onLogin">登录</el-button>
            <el-button @click="openResetDialog">重置密码</el-button>
          </el-space>
        </el-form-item>
      </el-form>
    </el-card>

    <el-dialog v-model="resetVisible" title="重置密码" width="420px">
      <el-form :model="resetForm" label-width="90px" @submit.prevent>
        <el-form-item label="账号">
          <el-input v-model="resetForm.username" placeholder="请输入账号" />
        </el-form-item>
        <el-form-item label="原密码">
          <el-input v-model="resetForm.old_password" type="password" show-password placeholder="请输入原密码" />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="resetForm.new_password" type="password" show-password placeholder="请输入新密码" />
          <div class="password-hint">密码格式：6-8位数字或英文，区分大小写。</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resetVisible = false">取消</el-button>
        <el-button type="primary" :loading="resetLoading" @click="onResetPassword">保存并验证</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import { login, me, resetPassword } from '@/api/auth'
import { useAuthStore } from '@/store/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const loading = ref(false)
const form = reactive({ username: '', password: '' })
const resetVisible = ref(false)
const resetLoading = ref(false)
const resetForm = reactive({ username: '', old_password: '', new_password: '' })
const passwordPattern = /^[A-Za-z0-9]{6,8}$/

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

function getResetErrorMessage(err: unknown): string {
  if (typeof err === 'object' && err !== null) {
    const maybeError = err as {
      message?: string
      response?: {
        data?: {
          detail?: string | Array<{ msg?: string }>
          message?: string
        }
      }
    }
    const detail = maybeError.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) return detail.map(item => item.msg).filter(Boolean).join('；') || '密码更改失败'
    return maybeError.response?.data?.message || maybeError.message || '密码更改失败'
  }
  return '密码更改失败'
}

function openResetDialog() {
  resetForm.username = form.username
  resetForm.old_password = ''
  resetForm.new_password = ''
  resetVisible.value = true
}

async function onResetPassword() {
  if (!resetForm.username) return ElMessage.warning('请先输入账号')
  if (!resetForm.old_password) return ElMessage.warning('请先输入原密码')
  if (!passwordPattern.test(resetForm.new_password)) {
    return ElMessage.warning('新密码必须为6-8位数字或英文，区分大小写')
  }
  resetLoading.value = true
  try {
    await resetPassword(resetForm)
    ElMessage.success('密码更改成功')
    resetVisible.value = false
    form.username = resetForm.username
    form.password = ''
  } catch (err) {
    ElMessage.error(`密码更改失败：${getResetErrorMessage(err)}`)
  } finally {
    resetLoading.value = false
  }
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
    const redirectTo = typeof route.query.redirect === 'string' ? route.query.redirect : (isAdmin ? '/accounts' : '/workbench')
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
.password-hint { margin-top: 6px; color: #909399; font-size: 12px; line-height: 1.4; }
</style>
