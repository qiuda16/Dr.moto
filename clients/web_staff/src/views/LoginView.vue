<template>
  <div class="login-page">
    <div class="login-shell">
      <section class="login-hero">
        <div class="brand-mark">DrMoto</div>
        <h1>门店后台登录</h1>
        <p>先登录，再进入工单、客户、库存和系统设置。</p>
        <ul>
          <li>登录成功后进入完整后台</li>
          <li>token 失效会自动退出</li>
          <li>页面可直接访问，但操作受权限控制</li>
        </ul>
      </section>

      <section class="login-card card">
        <div class="login-card-head">
          <div class="login-title">DrMoto 门店管理系统</div>
          <div class="login-subtitle">请输入员工账号密码</div>
        </div>

        <el-form ref="formRef" :model="form" :rules="rules" label-position="top" class="login-form">
          <el-form-item label="用户名" prop="username">
            <el-input
              v-model="form.username"
              size="large"
              autocomplete="username"
              placeholder="请输入用户名"
              @keyup.enter="submitLogin"
            />
          </el-form-item>

          <el-form-item label="密码" prop="password">
            <el-input
              v-model="form.password"
              size="large"
              type="password"
              show-password
              autocomplete="current-password"
              placeholder="请输入密码"
              @keyup.enter="submitLogin"
            />
          </el-form-item>

          <div class="login-actions">
            <el-button :loading="loading" type="primary" size="large" @click="submitLogin">登录后台</el-button>
            <span class="login-tip">登录后可访问全部后台页面</span>
          </div>
        </el-form>
      </section>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import axios from 'axios'

import { getSavedStaffUsername, setAuthToken, setSavedStaffUsername } from '../utils/auth'

const route = useRoute()
const router = useRouter()
const formRef = ref()
const loading = ref(false)

const form = reactive({
  username: getSavedStaffUsername(),
  password: '',
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function submitLogin() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    const body = new URLSearchParams()
    body.append('username', String(form.username || '').trim())
    body.append('password', String(form.password || ''))

    const resp = await axios.post('/api/auth/token', body, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })

    const token = resp?.data?.access_token || ''
    if (!token) {
      ElMessage.error('登录失败，请检查账号密码')
      return
    }

    setAuthToken(token)
    setSavedStaffUsername(form.username)

    const redirect = typeof route.query.redirect === 'string' && route.query.redirect.trim()
      ? route.query.redirect
      : '/'

    ElMessage.success('登录成功')
    await router.replace(redirect)
  } catch (error) {
    const detail = error?.response?.data?.detail
    const message = typeof detail === 'string' && detail.trim()
      ? detail
      : '登录失败，请检查账号密码'
    ElMessage.error(message)
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
  padding: 24px;
  background:
    radial-gradient(circle at top left, rgba(38, 149, 214, 0.18), transparent 32%),
    radial-gradient(circle at bottom right, rgba(31, 157, 98, 0.12), transparent 24%),
    linear-gradient(180deg, #eef6fb 0%, #e8f0f7 100%);
}

.login-shell {
  width: min(1080px, 100%);
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(360px, 440px);
  gap: 28px;
  align-items: center;
}

.login-hero {
  color: #17324a;
  padding: 32px;
}

.brand-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 88px;
  height: 36px;
  padding: 0 14px;
  border-radius: 999px;
  background: rgba(38, 149, 214, 0.14);
  color: #0f6cbd;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.login-hero h1 {
  margin: 18px 0 10px;
  font-size: 38px;
  line-height: 1.15;
}

.login-hero p {
  margin: 0 0 18px;
  color: #50677c;
  font-size: 16px;
  line-height: 1.8;
}

.login-hero ul {
  margin: 0;
  padding-left: 20px;
  color: #5d7489;
  line-height: 2;
}

.login-card {
  padding: 30px;
  border-radius: 24px;
}

.login-card-head {
  margin-bottom: 20px;
}

.login-title {
  font-size: 24px;
  font-weight: 700;
  color: #0f172a;
}

.login-subtitle {
  margin-top: 6px;
  color: #64748b;
}

.login-form :deep(.el-form-item__label) {
  font-weight: 600;
}

.login-actions {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-top: 10px;
}

.login-tip {
  color: #64748b;
  font-size: 13px;
}

@media (max-width: 900px) {
  .login-shell {
    grid-template-columns: 1fr;
  }

  .login-hero {
    padding: 8px 0 0;
  }
}
</style>
