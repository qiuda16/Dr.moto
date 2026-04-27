<template>
  <view class="page-shell">
    <view class="page-body">
      <view v-if="error" class="error-state">{{ error }}</view>

      <view class="hero-card">
        <view class="hero-title">{{ profile.customer_name || '车主账号' }}</view>
        <view class="hero-subtitle">{{ profile.phone_masked || '未绑定手机号' }}</view>
      </view>

      <view class="light-card">
        <view class="section-title">账号信息</view>
        <view class="list-item">
          <view class="item-title">Partner ID</view>
          <view class="item-desc">{{ profile.partner_id || '-' }}</view>
        </view>
        <view class="list-item">
          <view class="item-title">服务地址</view>
          <view class="item-desc">{{ apiBaseUrl }}</view>
        </view>
      </view>

      <view class="light-card">
        <view class="section-title">操作</view>
        <view class="btn-row">
          <button class="btn-primary" @click="goToBind">重新绑定</button>
          <button class="btn-secondary" @click="logout">退出登录</button>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { API_BASE } from '../../config/env'
import { api } from '../../utils/api'
import { clearBindTicket, clearSession, getBindTicket } from '../../utils/session'

export default {
  data() {
    return {
      error: '',
      profile: {},
      apiBaseUrl: API_BASE,
    }
  },
  onShow() {
    this.bootstrap()
  },
  methods: {
    async bootstrap() {
      this.error = ''
      try {
        const session = await api.ensureCustomerSession()
        if (!session.bound) {
          uni.redirectTo({ url: `/pages/bind/index?bind_ticket=${encodeURIComponent(session.bindTicket || getBindTicket() || '')}` })
          return
        }
        this.profile = await api.getMe()
      } catch (error) {
        this.error = error?.message || '个人中心加载失败'
      }
    },
    goToBind() {
      uni.navigateTo({ url: `/pages/bind/index?bind_ticket=${encodeURIComponent(getBindTicket() || '')}` })
    },
    async logout() {
      try {
        await api.logoutCustomer()
      } catch (_error) {
      }
      clearSession()
      clearBindTicket()
      uni.reLaunch({ url: '/pages/index/index' })
    },
  },
}
</script>

<style lang="scss">
@import '../../styles/mp-customer.scss';
</style>
