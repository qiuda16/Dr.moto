<template>
  <div class="page-container login-page">
    <div class="hero">
      <p class="eyebrow">车主服务中心</p>
      <h1>车主小程序</h1>
      <p class="tagline">简洁、清晰、随时了解你的车辆状态。</p>
    </div>

    <div class="card login-card">
      <van-field v-model="mockCode" label="微信登录码" placeholder="请输入测试登录码" />
      <van-field v-model="mockPhone" label="手机号" placeholder="请输入手机号" />
      <van-field v-model="mockPlateNo" label="车牌号" placeholder="例如：TEST1234" />
      <van-button type="primary" block :loading="loading" @click="onLogin">进入小程序</van-button>
      <p class="hint">当前为联调环境，后续可直接走微信授权登录。</p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { showSuccessToast } from 'vant'
import { bindCustomer, wechatLogin } from '../api'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const loading = ref(false)
const mockCode = ref('mock-wechat-code')
const mockPhone = ref('13900001111')
const mockPlateNo = ref('TEST1234')

async function onLogin() {
  loading.value = true
  try {
    const loginRes = await wechatLogin(mockCode.value)
    let accessToken = loginRes.access_token
    let partnerId = loginRes.partner_id
    let customerName = loginRes.customer_name
    let phoneMasked = loginRes.phone_masked
    let refreshToken = loginRes.refresh_token

    if (!loginRes.bound) {
      const bindRes = await bindCustomer({
        bind_ticket: loginRes.bind_ticket,
        phone: mockPhone.value,
        plate_no: mockPlateNo.value,
        verify_code: '123456',
      })
      accessToken = bindRes.access_token
      partnerId = bindRes.partner_id
      customerName = bindRes.customer_name
      phoneMasked = bindRes.phone_masked
      refreshToken = bindRes.refresh_token
    }

    auth.setSession({
      accessToken,
      refreshToken,
      partnerId,
      customerName,
      phoneMasked,
    })

    showSuccessToast('登录成功')
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/app/dashboard'
    router.replace(redirect)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  padding-top: 36px;
}

.hero {
  margin: 0 2px 16px;
  padding: 18px 6px;
}

.eyebrow {
  margin: 0 0 8px;
  font-size: 12px;
  letter-spacing: 0.08em;
  color: var(--text-muted);
}

.hero h1 {
  margin: 0;
  font-size: 40px;
  letter-spacing: -0.03em;
}

.tagline {
  margin: 10px 0 0;
  color: var(--text-muted);
  font-size: 15px;
}

.login-card {
  border-radius: 24px;
}

.hint {
  margin: 12px 4px 0;
  color: var(--text-muted);
  font-size: 12px;
}
</style>
