﻿﻿﻿<template>
  <view class="page">
    <view class="card">
      <view class="section-title">我的</view>
      <view class="subtext">账号与门店服务入口。</view>
      <view style="margin-top: 16rpx;">{{ profile?.customerName || '车主用户' }}</view>
      <view class="subtext">{{ profile?.phoneMasked || '--' }}</view>
      <view class="subtext">客户编号：{{ profile?.partnerId || '--' }}</view>
    </view>

    <view class="card">
      <view class="section-title">门店联系</view>
      <view class="subtext">服务电话：400-000-0000</view>
      <view class="subtext">服务时间：09:00 - 20:00</view>
      <button style="margin-top: 16rpx;" @click="goRecommend">查看推荐保养</button>
      <button style="margin-top: 12rpx;" @click="goKnowledge">查看养护科普</button>
      <button style="margin-top: 12rpx;" @click="goPrivacy">隐私政策</button>
      <button style="margin-top: 12rpx;" @click="goAgreement">用户协议</button>
      <button style="margin-top: 12rpx;" @click="logout">退出登录</button>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { api } from '../../utils/api'
import { clearSession, ensureLogin, getProfile } from '../../utils/session'

const profile = ref(null)

onShow(() => {
  if (!ensureLogin()) return
  profile.value = getProfile()
})

function goRecommend() {
  uni.navigateTo({ url: '/subpages/recommendations/index' })
}

function goKnowledge() {
  uni.navigateTo({ url: '/subpages/knowledge/index' })
}

function goPrivacy() {
  uni.navigateTo({ url: '/subpages/privacy/index' })
}

function goAgreement() {
  uni.navigateTo({ url: '/subpages/agreement/index' })
}

async function logout() {
  try {
    await api.logout()
  } catch (_err) {
  } finally {
    clearSession()
    uni.showToast({ title: '已退出登录', icon: 'none' })
    setTimeout(() => {
      uni.redirectTo({ url: '/subpages/auth/login' })
    }, 200)
  }
}
</script>
