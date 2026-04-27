<template>
  <view class="page-shell">
    <view class="page-body">
      <view v-if="error" class="error-state">{{ error }}</view>

      <view class="hero-card">
        <view class="chip" :class="context.health_state_class">{{ context.health_state_label }}</view>
        <view class="hero-title">AI 车况助手</view>
        <view class="hero-subtitle">{{ context.overview_text || '根据当前车况给出下一步建议。' }}</view>
      </view>

      <view class="surface-card">
        <view class="section-title section-title--dark">快捷提问</view>
        <view class="tag-row">
          <view v-for="item in suggestions" :key="item.text || item" class="tag-chip" @click="sendQuick(item.text || item)">
            {{ item.text || item }}
          </view>
        </view>
      </view>

      <view class="light-card">
        <view class="section-title">对话</view>
        <view v-for="(message, index) in messages" :key="index" class="message-card" :class="{ 'message-card--user': message.role === 'user' }">
          <view class="message-role">{{ message.role === 'user' ? '你' : 'AI' }}</view>
          <view class="message-content">{{ message.content }}</view>
          <view v-if="message.suggested_actions_text" class="item-meta">{{ message.suggested_actions_text }}</view>
          <view v-if="message.action_cards?.length" class="message-actions" style="margin-top: 12rpx">
            <view v-for="card in message.action_cards" :key="card.label" class="choice-pill" @click="handleActionCard(card)">
              {{ card.label }}
            </view>
          </view>
        </view>
        <input v-model="inputValue" class="field-input" placeholder="问保养、价格、异常和预约..." />
        <view class="btn-row">
          <button class="btn-primary" :disabled="sending" @click="sendMessage">{{ sending ? '发送中...' : '发送' }}</button>
          <button class="btn-secondary" @click="goToVehicle">看车辆详情</button>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { api } from '../../utils/api'
import { consumeAiSeed, getJourney, saveJourney } from '../../utils/journey'
import { formatDateTime, healthClass, healthLabel, inspectionStatusLabel } from '../../utils/format'
import { getBindTicket } from '../../utils/session'

function withContextLabels(context) {
  const healthSummary = context?.health_summary || {}
  return {
    ...context,
    health_state_label: healthLabel(context?.health_state),
    health_state_class: healthClass(context?.health_state),
    overview_text: [
      context?.vehicle?.license_plate || '未选择车辆',
      healthLabel(context?.health_state),
      formatDateTime(healthSummary.latest_measured_at),
    ].filter(Boolean).join(' · '),
    health_summary: {
      ...healthSummary,
      inspection_items: (healthSummary.inspection_items || []).map((item) => ({
        ...item,
        status_text: inspectionStatusLabel(item?.status),
      })),
    },
  }
}

function withActionText(message) {
  const content = String(message?.content || '')
  return {
    ...message,
    suggested_actions_text: Array.isArray(message?.suggested_actions) ? message.suggested_actions.join(' / ') : '',
    content,
  }
}

export default {
  data() {
    return {
      loading: true,
      error: '',
      context: { vehicle: {}, health_summary: {} },
      suggestions: [],
      messages: [],
      inputValue: '',
      sending: false,
      selectedVehicleId: '',
      activeJourney: null,
    }
  },
  onShow() {
    this.bootstrap()
  },
  methods: {
    async bootstrap() {
      this.loading = true
      this.error = ''
      try {
        const session = await api.ensureCustomerSession()
        if (!session.bound) {
          uni.redirectTo({ url: `/pages/bind/index?bind_ticket=${encodeURIComponent(session.bindTicket || getBindTicket() || '')}` })
          return
        }
        const context = withContextLabels(await api.getAiContext(api.getSelectedVehicleId() || ''))
        const suggestionPayload = await api.getAiSuggestions(context.selected_vehicle_id || api.getSelectedVehicleId() || '')
        this.context = context
        this.selectedVehicleId = context.selected_vehicle_id || api.getSelectedVehicleId() || ''
        this.suggestions = (suggestionPayload?.suggestions || []).slice(0, 4)
        this.activeJourney = getJourney()
        const seed = consumeAiSeed()
        if (seed?.inputValue) {
          this.inputValue = seed.inputValue
        } else if (!this.inputValue && this.activeJourney?.aiPrompt) {
          this.inputValue = this.activeJourney.aiPrompt
        }
        if (!this.messages.length) {
          this.messages = [withActionText({
            role: 'assistant',
            content: this.activeJourney?.title
              ? `当前主任务是“${this.activeJourney.title}”。我已经接入你的车况数据，可以直接帮你判断下一步。`
              : '我已经接入你的车况数据。你可以直接问我保养、价格、维修方法或预约建议。',
          })]
        }
      } catch (error) {
        this.error = error?.message || 'AI 页面加载失败'
      } finally {
        this.loading = false
      }
    },
    async sendMessage() {
      const message = String(this.inputValue || '').trim()
      if (!message || this.sending) {
        return
      }
      this.sending = true
      this.messages = [...this.messages, { role: 'user', content: message }]
      this.inputValue = ''
      try {
        const response = await api.sendAiChat({
          message,
          vehicle_id: this.selectedVehicleId || api.getSelectedVehicleId() || undefined,
          context: { source: 'mini_program' },
        })
        this.messages = [...this.messages, withActionText({
          role: 'assistant',
          content: response?.response || '我暂时没有拿到回复。',
          suggested_actions: response?.suggested_actions || [],
          action_cards: response?.action_cards || [],
        })]
      } catch (error) {
        this.messages = [...this.messages, withActionText({ role: 'assistant', content: error?.message || 'AI 服务暂时不可用。' })]
      } finally {
        this.sending = false
      }
    },
    sendQuick(text) {
      this.inputValue = text
      this.sendMessage()
    },
    goToVehicle() {
      const vehicleId = this.selectedVehicleId || api.getSelectedVehicleId()
      if (!vehicleId) {
        uni.showToast({ title: '没有可查看的车辆', icon: 'none' })
        return
      }
      uni.navigateTo({ url: `/pages/vehicle/detail?vehicle_id=${encodeURIComponent(vehicleId)}` })
    },
    handleActionCard(card) {
      const action = String(card?.action || '')
      if (action === 'view_vehicle') {
        this.goToVehicle()
        return
      }
      if (action === 'view_shop') {
        uni.switchTab({ url: '/pages/shop/index' })
        return
      }
      if (action === 'create_appointment' || action === 'create_appointment_draft') {
        const query = []
        if (this.selectedVehicleId) query.push(`vehicle_id=${encodeURIComponent(this.selectedVehicleId)}`)
        if (card?.label) query.push(`subject=${encodeURIComponent(card.label)}`)
        if (card?.service_kind) query.push(`service_kind=${encodeURIComponent(card.service_kind)}`)
        if (card?.notes) query.push(`notes=${encodeURIComponent(card.notes)}`)
        uni.navigateTo({ url: `/pages/appointment/index${query.length ? `?${query.join('&')}` : ''}` })
        return
      }
      if (this.activeJourney) {
        saveJourney(this.activeJourney)
      }
      uni.showToast({ title: card?.label || '暂不支持', icon: 'none' })
    },
  },
}
</script>

<style lang="scss">
@import '../../styles/mp-customer.scss';
</style>
