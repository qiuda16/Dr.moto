<template>
  <view class="page-shell">
    <view class="page-body">
      <view class="hero-card">
        <view class="hero-title">绑定车主身份</view>
        <view class="hero-subtitle">登录后把微信会话和手机号、车牌绑定起来。</view>
      </view>

      <view v-if="error" class="error-state">{{ error }}</view>

      <view class="light-card">
        <view class="section-title">绑定信息</view>
        <view class="field-label">绑定票据</view>
        <input v-model="form.bind_ticket" class="field-input" placeholder="bind_ticket" />
        <view class="field-label">手机号</view>
        <input v-model="form.phone" class="field-input" placeholder="手机号" />
        <view class="field-label">车牌号</view>
        <input v-model="form.plate_no" class="field-input" placeholder="车牌号" />
        <view class="field-label">验证码</view>
        <input v-model="form.verify_code" class="field-input" placeholder="验证码" />
        <view class="btn-row">
          <button class="btn-primary" :disabled="loading" @click="submit">{{ loading ? '绑定中...' : '提交绑定' }}</button>
          <button class="btn-secondary" @click="backHome">返回首页</button>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { api } from '../../utils/api'
import { getBindTicket, saveBindTicket } from '../../utils/session'

export default {
  data() {
    return {
      loading: false,
      error: '',
      form: {
        bind_ticket: '',
        phone: '',
        plate_no: '',
        verify_code: '',
      },
    }
  },
  onLoad(options) {
    const bindTicket = options?.bind_ticket || getBindTicket()
    if (bindTicket) {
      this.form.bind_ticket = bindTicket
      saveBindTicket(bindTicket)
    }
  },
  methods: {
    async submit() {
      const payload = {
        bind_ticket: String(this.form.bind_ticket || '').trim(),
        phone: String(this.form.phone || '').trim(),
        plate_no: String(this.form.plate_no || '').trim(),
        verify_code: String(this.form.verify_code || '').trim(),
      }
      if (!payload.bind_ticket || !payload.phone || !payload.plate_no || !payload.verify_code) {
        uni.showToast({ title: '请把信息填完整', icon: 'none' })
        return
      }
      this.loading = true
      this.error = ''
      try {
        await api.bindCustomer(payload)
        uni.showToast({ title: '绑定成功', icon: 'success' })
        uni.reLaunch({ url: '/pages/index/index' })
      } catch (error) {
        this.error = error?.message || '绑定失败'
      } finally {
        this.loading = false
      }
    },
    backHome() {
      uni.reLaunch({ url: '/pages/index/index' })
    },
  },
}
</script>

<style lang="scss">
@import '../../styles/mp-customer.scss';
</style>
