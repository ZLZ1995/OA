<template>
  <div class="login-page">
    <section class="login-shell">
      <div class="brand-panel">
        <div class="brand-content">
          <div class="brand-mark">
            <img src="/zhongqin-logo.png" alt="中勤" />
          </div>
          <div class="company-name">中勤资产评估有限公司</div>
          <h1>中勤资产评估项目流程管理系统</h1>
          <p>项目立项、合同流转、报告审核、文印开票、底稿归档的一体化流程管理平台。</p>
          <div class="brand-metrics">
            <span>项目全流程</span>
            <span>审核留痕</span>
            <span>数据归档</span>
          </div>
        </div>
      </div>

      <el-card class="login-card" shadow="never">
        <div class="login-card-title">
          <span>账号登录</span>
          <small>内部系统，仅限授权人员使用</small>
        </div>
        <el-form :model="form" label-position="top" @submit.prevent>
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
    </section>

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
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 56px;
  background:
    radial-gradient(circle at 18% 16%, rgba(31, 78, 121, 0.16), transparent 28%),
    radial-gradient(circle at 82% 76%, rgba(15, 118, 110, 0.10), transparent 26%),
    linear-gradient(135deg, #eef3f8 0%, #f8fafc 100%);
}

.login-shell {
  width: min(1120px, 100%);
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) 430px;
  overflow: hidden;
  border: 1px solid rgba(217, 227, 238, 0.9);
  border-radius: 18px;
  background: #fff;
  box-shadow: 0 28px 70px rgba(31, 78, 121, 0.18);
}

.brand-panel {
  min-height: 560px;
  padding: 64px 58px;
  color: #fff;
  background:
    linear-gradient(135deg, rgba(31, 78, 121, 0.98), rgba(14, 82, 90, 0.92)),
    #1f4e79;
  position: relative;
  overflow: hidden;
}

.brand-panel::before,
.brand-panel::after {
  content: "";
  position: absolute;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.10);
}

.brand-panel::before {
  width: 260px;
  height: 260px;
  right: -92px;
  top: -84px;
}

.brand-panel::after {
  width: 180px;
  height: 180px;
  left: -72px;
  bottom: -60px;
}

.brand-content {
  position: relative;
  z-index: 1;
}

.brand-mark {
  width: 88px;
  height: 88px;
  display: grid;
  place-items: center;
  border-radius: 14px;
  background: #e60012;
  box-shadow: 0 14px 34px rgba(0, 0, 0, 0.18);
  overflow: hidden;
}

.brand-mark img {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: contain;
}

.company-name {
  margin-top: 36px;
  margin-bottom: 18px;
  color: rgba(255, 255, 255, 0.78);
  font-size: 16px;
  font-weight: 600;
}

.brand-panel h1 {
  margin: 0;
  max-width: none;
  font-size: 34px;
  line-height: 1.2;
  letter-spacing: 0;
  white-space: nowrap;
}

.brand-panel p {
  margin: 24px 0 0;
  max-width: none;
  color: rgba(255, 255, 255, 0.78);
  font-size: 14px;
  line-height: 1.8;
  white-space: nowrap;
}

.brand-metrics {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 46px;
}

.brand-metrics span {
  padding: 9px 14px;
  border: 1px solid rgba(255, 255, 255, 0.24);
  border-radius: 999px;
  color: rgba(255, 255, 255, 0.88);
  background: rgba(255, 255, 255, 0.10);
  font-size: 13px;
}

.login-card {
  display: flex;
  align-items: center;
  width: 100%;
  border: 0;
  box-shadow: none;
}

.login-card :deep(.el-card__body) {
  width: 100%;
  padding: 56px 46px;
}

.login-card-title {
  display: grid;
  gap: 8px;
  margin-bottom: 28px;
}

.login-card-title span {
  color: #1f2937;
  font-size: 24px;
  font-weight: 700;
}

.login-card-title small {
  color: #64748b;
  font-size: 13px;
}

.login-card :deep(.el-button) {
  min-width: 104px;
  height: 38px;
}

.login-card :deep(.el-input__wrapper) {
  min-height: 40px;
}

.password-hint { margin-top: 6px; color: #909399; font-size: 12px; line-height: 1.4; }

@media (max-width: 860px) {
  .login-page { padding: 24px; }
  .login-shell { grid-template-columns: 1fr; }
  .brand-panel { min-height: auto; padding: 32px; }
  .brand-panel h1,
  .brand-panel p {
    white-space: normal;
  }
}
</style>
