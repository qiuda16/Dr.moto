<template>
  <view class="page-shell">
    <view class="page-body">
      <view class="hero-card">
        <view class="hero-title">最近任务</view>
        <view class="hero-subtitle">把最近做过的切车、AI 咨询和预约草稿串起来继续处理。</view>
      </view>

      <view class="light-card">
        <view class="section-title">时间线</view>
        <view v-if="items.length">
          <view v-for="(item, index) in items" :key="item.id + item.updatedAt" class="timeline-item" @click="openItem(index)">
            <view class="item-title">{{ item.title }}</view>
            <view class="item-desc">{{ item.desc }}</view>
            <view class="item-meta">{{ item.updated_at_text }} · {{ item.status_text }}</view>
          </view>
        </view>
        <view v-else class="empty-state">还没有历史任务。</view>
      </view>
    </view>
  </view>
</template>

<script>
import { api } from '../../utils/api'
import { formatDateTime } from '../../utils/format'
import { getHistory, saveJourney } from '../../utils/journey'

export default {
  data() {
    return {
      items: [],
    }
  },
  onShow() {
    this.items = (getHistory() || []).map((item) => ({
      ...item,
      updated_at_text: formatDateTime(item.updatedAt),
      status_text: item.status === 'done' ? '已完成' : '进行中',
    }))
  },
  methods: {
    openItem(index) {
      const item = this.items[index]
      if (!item) {
        return
      }
      if (item.id === 'appointment_created' && item.draftId) {
        uni.navigateTo({ url: `/pages/appointment/index?draft_id=${encodeURIComponent(item.draftId)}` })
        return
      }
      if (item.id === 'switch_vehicle' && item.vehicleId) {
        api.saveSelectedVehicleId(item.vehicleId)
        uni.reLaunch({ url: '/pages/index/index' })
        return
      }
      saveJourney({
        id: `history_${item.id || 'item'}`,
        title: item.title || '继续处理',
        desc: item.desc || '继续完成当前任务。',
        source: 'history',
        vehicleId: item.vehicleId || null,
        aiPrompt: `基于这条历史任务继续：${item.title || ''} ${item.desc || ''}`.trim(),
        appointmentSubject: item.title || '历史任务跟进',
        serviceKind: 'maintenance',
        notes: item.desc || '来自历史时间线。',
      })
      uni.switchTab({ url: '/pages/ai/index' })
    },
  },
}
</script>

<style lang="scss">
@import '../../styles/mp-customer.scss';
</style>
