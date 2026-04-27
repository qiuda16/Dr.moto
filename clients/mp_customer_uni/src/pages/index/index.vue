<template>
  <view class="page-shell">
    <view class="page-body">
      <view v-if="error" class="error-state">{{ error }}</view>

      <view class="hero-card">
        <view class="chip" :class="cockpit.health_state_class">{{ cockpit.health_state_label }}</view>
        <view class="hero-title">{{ primaryTask.title || '先看懂当前车况' }}</view>
        <view class="hero-subtitle">{{ primaryTask.desc || '把异常、建议和下一步动作串起来处理。' }}</view>
        <view class="btn-row">
          <button class="btn-primary" @click="runTaskAction(primaryTask.primaryAction || 'ai')">{{ primaryTask.primaryLabel || '问 AI' }}</button>
          <button class="btn-secondary" @click="runTaskAction(primaryTask.secondaryAction || 'detail')">{{ primaryTask.secondaryLabel || '看详情' }}</button>
        </view>
      </view>

      <view class="surface-card">
        <view class="section-title section-title--dark">当前车辆</view>
        <view class="hero-subtitle">{{ cockpit.vehicle.license_plate || '未选择车辆' }} {{ cockpit.vehicle.make || '' }} {{ cockpit.vehicle.model || '' }}</view>
        <view class="metrics-grid" style="margin-top: 18rpx">
          <view class="metric-tile">
            <view class="metric-label">里程</view>
            <view class="metric-value">{{ cockpit.health_summary.latest_odometer_km || '-' }}</view>
          </view>
          <view class="metric-tile">
            <view class="metric-label">待处理建议</view>
            <view class="metric-value">{{ cockpit.health_summary.pending_recommendations || 0 }}</view>
          </view>
          <view class="metric-tile">
            <view class="metric-label">最近工单</view>
            <view class="metric-value">{{ cockpit.health_summary.latest_order_status_text || '-' }}</view>
          </view>
          <view class="metric-tile">
            <view class="metric-label">最近检测</view>
            <view class="metric-value">{{ cockpit.latest_measured_at_text || '-' }}</view>
          </view>
        </view>
      </view>

      <view class="light-card">
        <view class="section-title">服务主线</view>
        <view class="muted">{{ purposeFlow.desc }}</view>
        <view class="choice-row" style="margin-top: 18rpx">
          <view v-for="step in purposeFlow.steps" :key="step.key" class="choice-pill" :class="{ 'choice-pill--active': step.active }">
            {{ step.label }}
          </view>
        </view>
      </view>

      <view class="light-card" v-if="vehicles.length">
        <view class="section-title">车辆切换</view>
        <view class="vehicle-row">
          <view
            v-for="vehicle in vehicles"
            :key="vehicle.id"
            class="vehicle-pill"
            :class="{ 'vehicle-pill--active': Number(vehicle.id) === Number(selectedVehicleId) }"
            @click="switchVehicle(vehicle)"
          >
            {{ vehicle.license_plate || `车辆 ${vehicle.id}` }}
          </view>
        </view>
      </view>

      <view class="light-card">
        <view class="section-title">检测摘要</view>
        <view v-if="previewInspectionSummary.length" class="inspection-grid">
          <view v-for="item in previewInspectionSummary" :key="item.label" class="inspection-tile" @click="goToVehicleDetail">
            <view class="tile-title">{{ item.label }}</view>
            <view class="tile-value">{{ item.value || '-' }}</view>
            <view class="tile-desc">{{ item.status_text }}</view>
          </view>
        </view>
        <view v-else class="muted">还没有可展示的检测摘要。</view>
      </view>

      <view class="light-card">
        <view class="section-title">最近任务</view>
        <view v-if="recentHistory.length">
          <view v-for="item in recentHistory" :key="item.id + item.updatedAt" class="list-item" @click="goToHistory">
            <view class="item-title">{{ item.title }}</view>
            <view class="item-desc">{{ item.desc }}</view>
            <view class="item-meta">{{ item.updated_at_text }}</view>
          </view>
        </view>
        <view v-else class="muted">还没有最近任务记录。</view>
      </view>
    </view>
  </view>
</template>

<script>
import { api } from '../../utils/api'
import { addHistory, getHistory, saveJourney } from '../../utils/journey'
import { buildPurposeFlow } from '../../utils/purpose'
import { formatDateTime, healthClass, healthLabel, inspectionStatusLabel, orderStateLabel } from '../../utils/format'
import { getBindTicket } from '../../utils/session'

function withDisplayLabels(cockpit) {
  const healthSummary = cockpit?.health_summary || {}
  return {
    ...cockpit,
    health_state_label: healthLabel(cockpit?.health_state),
    health_state_class: healthClass(cockpit?.health_state),
    latest_measured_at_text: formatDateTime(healthSummary.latest_measured_at),
    health_summary: {
      ...healthSummary,
      latest_order_status_text: orderStateLabel(healthSummary.latest_order_status),
    },
  }
}

function pickInspectionSummary(items, limit = 4) {
  return (items || []).slice(0, limit).map((item) => ({
    ...item,
    status_text: inspectionStatusLabel(item?.status),
  }))
}

function withHistoryView(items) {
  return (items || []).map((item) => ({
    ...item,
    updated_at_text: formatDateTime(item.updatedAt),
  }))
}

function buildPrimaryTask(cockpit, vehicleId) {
  const flags = cockpit?.health_summary?.flags || []
  const pending = cockpit?.health_summary?.pending_recommendations || 0
  const shopItems = cockpit?.shop_items || []
  const plate = cockpit?.vehicle?.license_plate || '当前车辆'

  if (flags.length) {
    return {
      id: 'health_attention',
      title: '优先处理异常提醒',
      desc: `${flags[0]?.label || '当前车况'}值得先判断是否影响继续骑行。`,
      primaryLabel: '问 AI 判断',
      secondaryLabel: '直接预约',
      primaryAction: 'ai',
      secondaryAction: 'appointment',
      aiPrompt: `请结合 ${plate} 当前异常提醒，告诉我是否需要尽快处理，以及应该预约什么服务。`,
      appointmentSubject: '异常检测处理',
      serviceKind: 'repair',
      notes: flags[0]?.advice || '',
      vehicleId,
    }
  }

  if (pending > 0) {
    return {
      id: 'recommended_maintenance',
      title: '先看推荐保养',
      desc: `当前有 ${pending} 项推荐保养，先看方案再决定是否预约。`,
      primaryLabel: '问 AI 方案',
      secondaryLabel: '去预约',
      primaryAction: 'ai',
      secondaryAction: 'appointment',
      aiPrompt: `请根据 ${plate} 当前推荐保养项目，给我一个简单的保养建议和价格范围。`,
      appointmentSubject: '推荐保养咨询',
      serviceKind: 'maintenance',
      notes: `当前有 ${pending} 项推荐保养。`,
      vehicleId,
    }
  }

  if (shopItems.length > 0) {
    return {
      id: 'shop_recommendation',
      title: '先看适配商品',
      desc: '这台车已经有适配商品，先浏览推荐，再决定要不要让 AI 帮你筛选。',
      primaryLabel: '看商城',
      secondaryLabel: '问 AI 选购',
      primaryAction: 'shop',
      secondaryAction: 'ai',
      aiPrompt: `请根据 ${plate} 当前适配商品，帮我挑选更值得优先看的配件或服务。`,
      appointmentSubject: '配件与服务咨询',
      serviceKind: 'package',
      notes: '用户从商城推荐进入，希望先了解适配方案。',
      vehicleId,
    }
  }

  return {
    id: 'steady_overview',
    title: '先快速了解车况',
    desc: '目前没有明显异常，适合先看 AI 解读，再决定是否保养或预约。',
    primaryLabel: '问 AI',
    secondaryLabel: '看详情',
    primaryAction: 'ai',
    secondaryAction: 'detail',
    aiPrompt: `请快速总结 ${plate} 当前车况，并告诉我接下来最值得关注的一件事。`,
    appointmentSubject: '常规车况咨询',
    serviceKind: 'inspection',
    notes: '用户想先快速了解当前车况。',
    vehicleId,
  }
}

export default {
  data() {
    return {
      loading: true,
      error: '',
      cockpit: {
        vehicle: {},
        health_state: 'unknown',
        health_summary: {},
      },
      vehicles: [],
      selectedVehicleId: '',
      previewInspectionSummary: [],
      recentHistory: [],
      purposeFlow: { steps: [], desc: '' },
      primaryTask: {},
    }
  },
  onShow() {
    this.bootstrap()
  },
  onPullDownRefresh() {
    this.bootstrap().finally(() => uni.stopPullDownRefresh())
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
        const cockpit = withDisplayLabels(await api.getCockpit(api.getSelectedVehicleId() || ''))
        this.selectedVehicleId = cockpit.selected_vehicle_id || ''
        api.saveSelectedVehicleId(this.selectedVehicleId)
        this.primaryTask = buildPrimaryTask(cockpit, this.selectedVehicleId)
        saveJourney({ ...this.primaryTask, source: 'home' })
        this.cockpit = cockpit
        this.vehicles = cockpit.vehicles || []
        this.previewInspectionSummary = pickInspectionSummary(cockpit.health_summary?.inspection_items || [])
        this.recentHistory = withHistoryView(getHistory().slice(0, 2))
        this.purposeFlow = buildPurposeFlow(cockpit)
      } catch (error) {
        this.error = error?.message || '驾驶舱加载失败'
      } finally {
        this.loading = false
      }
    },
    switchVehicle(vehicle) {
      if (!vehicle?.id || Number(vehicle.id) === Number(this.selectedVehicleId)) {
        return
      }
      addHistory({
        id: 'switch_vehicle',
        title: '切换车辆',
        desc: `${vehicle.license_plate || '已切换'} ${vehicle.make || ''} ${vehicle.model || ''}`.trim(),
        source: 'home',
        vehicleId: vehicle.id,
      })
      api.saveSelectedVehicleId(vehicle.id)
      this.bootstrap()
    },
    runTaskAction(action) {
      saveJourney({ ...(this.primaryTask || {}), vehicleId: this.selectedVehicleId || null, source: 'home' })
      if (action === 'appointment') {
        const query = []
        if (this.selectedVehicleId) query.push(`vehicle_id=${encodeURIComponent(this.selectedVehicleId)}`)
        if (this.primaryTask.appointmentSubject) query.push(`subject=${encodeURIComponent(this.primaryTask.appointmentSubject)}`)
        if (this.primaryTask.serviceKind) query.push(`service_kind=${encodeURIComponent(this.primaryTask.serviceKind)}`)
        if (this.primaryTask.notes) query.push(`notes=${encodeURIComponent(this.primaryTask.notes)}`)
        uni.navigateTo({ url: `/pages/appointment/index${query.length ? `?${query.join('&')}` : ''}` })
        return
      }
      if (action === 'shop') {
        uni.switchTab({ url: '/pages/shop/index' })
        return
      }
      if (action === 'detail') {
        this.goToVehicleDetail()
        return
      }
      uni.switchTab({ url: '/pages/ai/index' })
    },
    goToVehicleDetail() {
      if (!this.selectedVehicleId) {
        uni.showToast({ title: '暂无车辆', icon: 'none' })
        return
      }
      uni.navigateTo({ url: `/pages/vehicle/detail?vehicle_id=${encodeURIComponent(this.selectedVehicleId)}` })
    },
    goToHistory() {
      uni.navigateTo({ url: '/pages/history/index' })
    },
  },
}
</script>

<style lang="scss">
@import '../../styles/mp-customer.scss';
</style>
