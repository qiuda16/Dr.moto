<template>
  <view class="page-shell">
    <view class="page-body">
      <view class="hero-card">
        <view class="hero-kicker">车主入口 · 门店同步</view>
        <view class="hero-title">欢迎回来</view>
        <view class="hero-subtitle">手机号和车牌号绑定后，就能进入驾驶舱查看车况、工单和建议。</view>
        <view class="summary-band">
          <view class="summary-band__item">
            <view class="summary-band__value">1</view>
            <view class="summary-band__label">快速登录</view>
          </view>
          <view class="summary-band__item">
            <view class="summary-band__value">2</view>
            <view class="summary-band__label">自动绑定</view>
          </view>
          <view class="summary-band__item">
            <view class="summary-band__value">3</view>
            <view class="summary-band__label">进入驾驶舱</view>
          </view>
        </view>
        <view class="hero-note">请使用门店登记的手机号与车牌号，系统会把你的账户和车辆档案同步到驾驶舱。</view>
      </view>

      <view v-if="errorMessage" class="error-state">{{ errorMessage }}</view>

      <view class="light-card">
        <view class="section-head">
          <view class="section-title">登录信息</view>
          <view class="section-head__sub">数据只用于车主身份校验</view>
        </view>
        <view class="form-panel">
          <view class="field-label">手机号</view>
          <input class="field-input" v-model="phone" maxlength="11" placeholder="请输入手机号" />
          <view class="field-label">车牌号</view>
          <input class="field-input" v-model="plateNo" maxlength="12" placeholder="请输入车牌号" />
        </view>
        <view class="btn-row">
          <button class="btn-primary" @click="onLogin" :loading="loading">进入小程序</button>
        </view>
      </view>

      <view class="light-card">
        <view class="section-head">
          <view class="section-title">登录说明</view>
          <view class="section-head__sub">先绑定，再看车况</view>
        </view>
        <view class="muted">首次登录后，系统会自动绑定你的手机号与车牌号，后续无需重复输入。</view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { ALLOW_DEMO_FALLBACK, LOGIN_DEFAULTS } from '../../config/env'
import { api } from '../../utils/api'
import { setSession } from '../../utils/session'

const phone = ref(LOGIN_DEFAULTS.phone)
const plateNo = ref(LOGIN_DEFAULTS.plateNo)
const loading = ref(false)
const errorMessage = ref('')

function validateInput() {
  const rawPhone = String(phone.value || '').trim()
  const rawPlate = String(plateNo.value || '').trim().toUpperCase()

  if (!/^1\d{10}$/.test(rawPhone)) {
    return '请输入正确的11位手机号'
  }
  if (rawPlate.length < 5) {
    return '请输入正确的车牌号'
  }
  phone.value = rawPhone
  plateNo.value = rawPlate
  return ''
}

async function onLogin() {
  if (loading.value) return
  const bad = validateInput()
  if (bad) {
    errorMessage.value = bad
    uni.showToast({ title: bad, icon: 'none' })
    return
  }

  loading.value = true
  errorMessage.value = ''
  try {
    const wxCode = await getWechatCode()
    const loginRes = await api.wechatLogin(wxCode)

    let accessToken = loginRes.access_token
    let refreshToken = loginRes.refresh_token
    let partnerId = loginRes.partner_id
    let customerName = loginRes.customer_name
    let phoneMasked = loginRes.phone_masked

    if (!loginRes.bound) {
      const bindRes = await api.bindCustomer({
        bind_ticket: loginRes.bind_ticket,
        phone: phone.value,
        plate_no: plateNo.value,
        verify_code: '123456',
      })
      accessToken = bindRes.access_token
      refreshToken = bindRes.refresh_token
      partnerId = bindRes.partner_id
      customerName = bindRes.customer_name
      phoneMasked = bindRes.phone_masked
    }

    setSession({
      accessToken,
      refreshToken,
      profile: {
        partnerId,
        customerName,
        phoneMasked,
      },
    })

    uni.showToast({ title: '登录成功', icon: 'success' })
    setTimeout(() => {
      uni.reLaunch({ url: '/pages/index/index' })
    }, 200)
  } catch (err) {
    const msg = err?.message || '登录失败，请稍后重试'
    errorMessage.value = msg
    uni.showToast({ title: msg, icon: 'none' })
  } finally {
    loading.value = false
  }
}

function getWechatCode() {
  return new Promise((resolve, reject) => {
    // #ifdef MP-WEIXIN
    uni.login({
      provider: 'weixin',
      success: (res) => {
        if (res?.code) {
          resolve(res.code)
          return
        }
        reject(new Error('获取微信登录凭证失败'))
      },
      fail: () => reject(new Error('微信登录初始化失败')),
    })
    // #endif

    // #ifndef MP-WEIXIN
    if (ALLOW_DEMO_FALLBACK) {
      resolve(`mock-${Date.now()}`)
      return
    }
    reject(new Error('请在微信小程序中登录'))
    // #endif
  })
}
</script>
