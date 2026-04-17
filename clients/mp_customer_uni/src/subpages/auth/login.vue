<template>
  <view class="page">
    <view class="card">
      <view class="section-title">车主登录</view>
      <view class="subtext" style="margin-bottom: 20rpx;">首次登录会自动绑定你在门店登记的手机号与车牌号。</view>
      <input class="input" v-model="phone" maxlength="11" placeholder="请输入手机号" />
      <input class="input" v-model="plateNo" maxlength="12" placeholder="请输入车牌号" />
      <button class="btn-primary" @click="onLogin" :loading="loading">进入小程序</button>
      <view v-if="errorMessage" class="subtext" style="margin-top: 16rpx; color: #bc2f1f;">{{ errorMessage }}</view>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { LOGIN_DEFAULTS } from '../../config/env'
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
      uni.switchTab({ url: '/pages/dashboard/index' })
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
    resolve(`mock-${Date.now()}`)
    // #endif
  })
}
</script>
