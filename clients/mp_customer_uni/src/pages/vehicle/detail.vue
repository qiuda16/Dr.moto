<template>
  <view class="page-shell">
    <view class="page-body">
      <view v-if="error" class="error-state">{{ error }}</view>

      <view class="hero-card">
        <view class="chip" :class="cockpit.health_state_class">{{ cockpit.health_state_label }}</view>
        <view class="hero-title">{{ cockpit.vehicle.license_plate || '车辆详情' }}</view>
        <view class="hero-subtitle">{{ cockpit.vehicle.make || '' }} {{ cockpit.vehicle.model || '' }}</view>
        <view class="btn-row">
          <button class="btn-primary" @click="openAI">问 AI</button>
          <button class="btn-secondary" @click="goToAppointment">去预约</button>
        </view>
      </view>

      <view class="light-card">
        <view class="section-title">检测地图</view>
        <view v-if="inspectionItems.length" class="inspection-grid">
          <view v-for="item in inspectionItems" :key="item.key || item.label" class="inspection-tile" @click="inspectItem(item)">
            <view class="tile-title">{{ item.label }}</view>
            <view class="tile-value">{{ item.value || '-' }}</view>
            <view class="tile-desc">{{ item.status_text }}</view>
          </view>
        </view>
        <view v-else class="empty-state">当前没有检测项。</view>
      </view>

      <view class="light-card">
        <view class="section-title">推荐服务</view>
        <view v-if="services.length">
          <view v-for="item in services" :key="item.id || item.name" class="list-item">
            <view class="item-title">{{ item.service_name || item.name }}</view>
            <view class="item-desc">{{ item.description || item.suggested_price_text }}</view>
          </view>
        </view>
        <view v-else class="muted">还没有推荐服务。</view>
      </view>

      <view class="light-card">
        <view class="section-title">最近工单</view>
        <view v-if="orders.length">
          <view v-for="item in orders" :key="item.id" class="list-item">
            <view class="item-title">{{ item.subject || item.order_no || `工单 ${item.id}` }}</view>
            <view class="item-desc">{{ item.state_text }}</view>
            <view class="item-meta">{{ item.amount_total_text }}</view>
          </view>
        </view>
        <view v-else class="muted">还没有历史工单。</view>
      </view>
    </view>
  </view>
</template>

<script>
import { api } from '../../utils/api'
import { formatMoney, healthClass, healthLabel, inspectionStatusLabel, orderStateLabel } from '../../utils/format'
import { getBindTicket } from '../../utils/session'
import { saveJourney, setAiSeed } from '../../utils/journey'

function withDisplayLabels(cockpit) {
  return {
    ...cockpit,
    health_state_label: healthLabel(cockpit?.health_state),
    health_state_class: healthClass(cockpit?.health_state),
  }
}

export default {
  data() {
    return {
      error: '',
      vehicleId: '',
      cockpit: { vehicle: {}, health_summary: {} },
      inspectionItems: [],
      orders: [],
      services: [],
    }
  },
  onLoad(options) {
    if (options?.vehicle_id) {
      this.vehicleId = Number(options.vehicle_id)
      api.saveSelectedVehicleId(this.vehicleId)
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
        const cockpit = withDisplayLabels(await api.getCockpit(this.vehicleId || api.getSelectedVehicleId() || ''))
        this.vehicleId = cockpit.selected_vehicle_id || this.vehicleId || api.getSelectedVehicleId() || ''
        const [ordersResp, services] = await Promise.all([
          this.vehicleId ? api.getVehicleMaintenanceOrders(this.vehicleId, 1, 10) : Promise.resolve({ items: [] }),
          this.vehicleId ? api.getVehicleRecommendedServices(this.vehicleId) : Promise.resolve([]),
        ])
        this.cockpit = cockpit
        this.inspectionItems = (cockpit.health_summary?.inspection_items || []).slice(0, 12).map((item) => ({
          ...item,
          status_text: inspectionStatusLabel(item?.status),
        }))
        this.orders = (ordersResp?.items || []).map((item) => ({
          ...item,
          state_text: orderStateLabel(item?.state),
          amount_total_text: formatMoney(item?.amount_total),
        }))
        this.services = (services || []).map((item) => ({
          ...item,
          suggested_price_text: formatMoney(item?.suggested_price),
        }))
      } catch (error) {
        this.error = error?.message || '车辆详情加载失败'
      }
    },
    openAI() {
      const plate = this.cockpit.vehicle?.license_plate || '当前车辆'
      saveJourney({
        id: 'vehicle_ai_review',
        title: '先做车况解读',
        desc: '结合当前车辆详情，判断是否要立刻处理。',
        source: 'vehicle',
        aiPrompt: `请结合 ${plate} 的检测信息，告诉我优先要处理哪一项。`,
        appointmentSubject: '车况解读后咨询',
        serviceKind: 'inspection',
        vehicleId: this.vehicleId || null,
      })
      uni.switchTab({ url: '/pages/ai/index' })
    },
    goToAppointment() {
      saveJourney({
        id: 'vehicle_appointment',
        title: '从检测结果发起预约',
        desc: '按当前车辆异常与建议保养，直接创建预约草稿。',
        source: 'vehicle',
        appointmentSubject: '车辆检测后预约',
        serviceKind: 'repair',
        notes: '来自车辆详情页。',
        vehicleId: this.vehicleId || null,
      })
      uni.navigateTo({ url: `/pages/appointment/index?vehicle_id=${encodeURIComponent(this.vehicleId || '')}` })
    },
    inspectItem(item) {
      const prompt = `请帮我解读 ${item.label}，现在显示 ${item.value || '-'}，状态是 ${item.status_text}。`
      setAiSeed({ inputValue: prompt, source: 'inspection' })
      saveJourney({
        id: 'inspection_item_review',
        title: `解读检测项：${item.label}`,
        desc: '从车辆详情中进入，优先判断风险和处理时机。',
        source: 'vehicle',
        aiPrompt: prompt,
        appointmentSubject: '检测项异常咨询',
        serviceKind: 'inspection',
        vehicleId: this.vehicleId || null,
      })
      uni.switchTab({ url: '/pages/ai/index' })
    },
  },
}
</script>

<style lang="scss">
@import '../../styles/mp-customer.scss';
</style>
