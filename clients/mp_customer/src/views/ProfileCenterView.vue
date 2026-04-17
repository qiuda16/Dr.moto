<template>
  <div class="page-container">
    <van-nav-bar title="我的" />
    <p class="page-subtitle">账户、联系信息和常用功能。</p>

    <div class="card profile-top">
      <div class="avatar">{{ initials }}</div>
      <div>
        <div class="name">{{ auth.customerName || '车主用户' }}</div>
        <div class="meta">手机号：{{ auth.phoneMasked || '--' }}</div>
        <div class="meta">客户编号：{{ auth.partnerId || '--' }}</div>
      </div>
    </div>

    <div class="card support-info">
      <div class="list-title">门店联系</div>
      <div class="list-meta">服务电话：400-000-0000</div>
      <div class="list-meta">服务时间：09:00 - 20:00</div>
    </div>

    <div class="card actions">
      <van-space direction="vertical" fill>
        <van-button plain type="primary" @click="goTo('/app/recommendations')">查看推荐保养</van-button>
        <van-button plain type="primary" @click="goTo('/app/knowledge')">查看养护科普</van-button>
        <van-button plain @click="onRefreshSession">刷新登录状态</van-button>
        <van-button type="danger" @click="onLogout">退出登录</van-button>
      </van-space>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { showSuccessToast } from 'vant'
import { logoutCustomer, refreshToken } from '../api'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()

const initials = computed(() => {
  const name = (auth.customerName || '车主用户').trim()
  return name.slice(0, 1).toUpperCase()
})

function goTo(path) {
  router.push(path)
}

async function onRefreshSession() {
  if (!auth.refreshToken) {
    showSuccessToast('当前无需刷新')
    return
  }
  const res = await refreshToken(auth.refreshToken)
  auth.setSession({
    accessToken: res.access_token,
    refreshToken: auth.refreshToken,
    partnerId: auth.partnerId,
    customerName: auth.customerName,
    phoneMasked: auth.phoneMasked,
  })
  showSuccessToast('登录状态已刷新')
}

async function onLogout() {
  try {
    await logoutCustomer()
  } finally {
    auth.clearSession()
    showSuccessToast('已退出登录')
    router.replace('/login')
  }
}
</script>

<style scoped>
.profile-top {
  display: grid;
  grid-template-columns: 58px 1fr;
  gap: 14px;
  align-items: center;
}

.avatar {
  width: 58px;
  height: 58px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: #eef2f7;
  color: #2b3648;
  font-weight: 700;
  font-size: 20px;
}

.name {
  font-size: 20px;
  font-weight: 600;
}

.meta {
  margin-top: 4px;
  color: var(--text-muted);
  font-size: 13px;
}

.support-info {
  margin-top: 12px;
}
</style>
