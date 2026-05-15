<template>
  <el-dialog
    :model-value="modelValue"
    title="切换账号"
    width="420px"
    destroy-on-close
    @close="emit('update:modelValue', false)"
  >
    <div class="switch-account-tip">请输入新账号信息，登录成功后将按账号角色自动进入对应首页。</div>
    <el-form :model="form" label-position="top" @submit.prevent>
      <el-form-item label="账号">
        <el-input v-model="form.username" placeholder="请输入账号" @keyup.enter="onLogin" />
      </el-form-item>
      <el-form-item label="密码">
        <el-input v-model="form.password" type="password" show-password placeholder="请输入密码" @keyup.enter="onLogin" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" :loading="loading" @click="onLogin">登录</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { login, me } from '@/api/auth'
import { useAuthStore } from '@/store/auth'
import { clearSession } from '@/api/authSession'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
}>()

const router = useRouter()
const auth = useAuthStore()
const loading = ref(false)
const form = reactive({ username: '', password: '' })

watch(
  () => props.modelValue,
  (visible) => {
    if (visible) {
      form.username = ''
      form.password = ''
    }
  }
)

function getErrorMessage(err: unknown): string {
  if (typeof err === 'object' && err !== null) {
    const maybeError = err as {
      message?: string
      response?: {
        data?: {
          detail?: string
          message?: string
        }
      }
    }
    return maybeError.response?.data?.detail || maybeError.response?.data?.message || maybeError.message || '登录失败，请稍后重试'
  }
  return '登录失败，请稍后重试'
}

async function onLogin() {
  if (!form.username.trim() || !form.password) {
    ElMessage.warning('请输入账号和密码')
    return
  }

  loading.value = true
  try {
    const token = await login({
      username: form.username.trim(),
      password: form.password,
    })

    await clearSession({ silent: true })
    auth.setToken(token.access_token)

    const profile = await me()
    auth.setUser(profile)
    const isAdmin = (profile.roles || []).includes('ADMIN')
    emit('update:modelValue', false)
    await router.replace(isAdmin ? '/accounts' : '/workbench')
    ElMessage.success('账号切换成功')
  } catch (err) {
    auth.clearAuth()
    ElMessage.error(getErrorMessage(err))
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.switch-account-tip {
  margin-bottom: 16px;
  padding: 10px 12px;
  border-radius: 8px;
  color: var(--zq-muted);
  background: var(--zq-primary-soft);
  line-height: 1.6;
}
</style>
