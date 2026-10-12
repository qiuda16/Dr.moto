<template>
  <view class="page-shell">
    <view class="page-body">
      <view class="hero-card">
        <view class="hero-title">{{ primaryTask.title || '当前车况总览' }}</view>
        <view class="hero-subtitle">{{ primaryTask.desc || '查看当前车辆状态，并选择下一步服务动作。' }}</view>
        <view class="summary-band">
          <view class="summary-band__item">
            <view class="summary-band__value">{{ cockpit.vehicle.license_plate || '未选择' }}</view>
            <view class="summary-band__label">当前车辆</view>
          </view>
          <view class="summary-band__item">
            <view class="summary-band__value">{{ cockpit.health_summary.pending_recommendations || 0 }}</view>
            <view class="summary-band__label">待关注项</view>
          </view>
          <view class="summary-band__item">
            <view class="summary-band__value">{{ cockpit.latest_measured_at_short || '-' }}</view>
            <view class="summary-band__label">最近体检</view>
          </view>
        </view>
        <view class="home-action-grid">
          <view class="home-action-card home-action-card--primary" @click="runTaskAction('detail')">
            <view class="home-action-card__art home-action-card__art--detail">
              <view class="home-action-card__art-sheet"></view>
              <view class="home-action-card__art-line home-action-card__art-line--one"></view>
              <view class="home-action-card__art-line home-action-card__art-line--two"></view>
              <view class="home-action-card__art-badge"></view>
            </view>
            <view class="home-action-card__title">体检详情</view>
            <view class="home-action-card__desc">先看异常和建议</view>
          </view>
          <view class="home-action-card" @click="runTaskAction('appointment')">
            <view class="home-action-card__art home-action-card__art--appointment">
              <view class="home-action-card__art-top"></view>
              <view class="home-action-card__art-grid">
                <view></view>
                <view></view>
                <view></view>
                <view></view>
              </view>
              <view class="home-action-card__art-check"></view>
            </view>
            <view class="home-action-card__title">预约门店</view>
            <view class="home-action-card__desc">把问题交给门店确认</view>
          </view>
          <view class="home-action-card" @click="runTaskAction('shop')">
            <view class="home-action-card__art home-action-card__art--shop">
              <view class="home-action-card__art-tag"></view>
              <view class="home-action-card__art-wrench"></view>
            </view>
            <view class="home-action-card__title">适配服务</view>
            <view class="home-action-card__desc">看能直接用的方案</view>
          </view>
        </view>
      </view>

      <view v-if="error" class="notice-banner notice-banner--compact notice-banner--soft">
        <view class="notice-banner__text">
          <view class="notice-banner__title">数据同步中</view>
          <view class="notice-banner__desc">{{ error }}</view>
        </view>
        <button class="notice-banner__action" @click="bootstrap">重试</button>
      </view>

      <view class="surface-card">
        <view class="section-head">
          <view class="section-title section-title--dark">当前车辆</view>
          <view class="section-head__sub">车辆档案与体检结论</view>
        </view>
        <view class="vehicle-banner">
          <view class="vehicle-banner__body">
            <view class="vehicle-banner__plate">{{ cockpit.vehicle.license_plate || '未选择车辆' }}</view>
            <view class="vehicle-banner__model">{{ [cockpit.vehicle.make, cockpit.vehicle.model].filter(Boolean).join(' · ') || '暂无车型信息' }}</view>
          </view>
          <view class="vehicle-banner__actions">
            <view class="status-pill" :class="cockpit.health_state_pill_class">{{ cockpit.health_state_label }}</view>
            <button class="vehicle-switch-button" @tap="openVehicleSwitcher">切换车辆</button>
          </view>
        </view>
        <view class="metrics-grid metrics-grid--vehicle" style="margin-top: 18rpx">
          <view class="metric-tile">
            <view class="metric-label">里程</view>
            <view class="metric-value">{{ cockpit.health_summary.latest_odometer_km || '-' }}</view>
          </view>
          <view class="metric-tile">
            <view class="metric-label">体检记录</view>
            <view class="metric-value">{{ cockpit.health_summary.health_records_count || 0 }}</view>
          </view>
          <view class="metric-tile">
            <view class="metric-label">最近检测</view>
            <view class="metric-value">{{ cockpit.latest_measured_at_text || '-' }}</view>
          </view>
        </view>
        <view v-if="importantInspectionItems.length" class="health-focus-list">
          <view v-for="item in importantInspectionItems" :key="item.key || item.label" class="health-focus-item" :class="item.status_class">
            <view class="health-focus-item__head">
              <view class="health-focus-item__title">{{ item.label }}</view>
              <view class="status-pill" :class="item.status_pill_class">{{ item.status_text }}</view>
            </view>
            <view class="health-focus-item__value">{{ item.value || '-' }}</view>
            <view class="health-focus-item__desc">{{ item.advice || '建议到店复核。' }}</view>
          </view>
        </view>
        <view v-if="vehicles.length" class="vehicle-row" style="margin-top: 18rpx">
          <button
            v-for="vehicle in visibleVehicles"
            :key="vehicle.id"
            class="vehicle-pill vehicle-pill--button"
            :class="{ 'vehicle-pill--active': Number(vehicle.id) === Number(selectedVehicleId) }"
            @tap="switchVehicle(vehicle)"
            :disabled="Number(vehicle.id) === Number(selectedVehicleId)"
          >
            {{ vehicle.license_plate || `车辆 ${vehicle.id}` }}
          </button>
          <button
            v-if="vehicleOverflowCount > 0"
            class="vehicle-pill vehicle-pill--button vehicle-pill--more"
            @tap="openVehicleSelector"
          >
            更多 {{ vehicleOverflowCount }} 台
          </button>
        </view>
      </view>

      <view class="light-card">
        <view class="section-head">
          <view class="section-title">服务流程</view>
          <view class="section-head__sub">从体检到门店处理</view>
        </view>
        <view class="muted">{{ purposeFlow.desc }}</view>
        <view class="step-list" style="margin-top: 18rpx">
          <view v-for="(step, index) in purposeFlow.steps" :key="step.key" class="step-item" :class="{ 'step-item--active': step.active }">
            <view class="step-item__index">{{ String(index + 1).padStart(2, '0') }}</view>
            <view class="step-item__body">
              <view class="step-item__title">{{ step.label }}</view>
              <view class="step-item__desc">{{ step.desc }}</view>
            </view>
          </view>
        </view>
      </view>

      <view class="light-card">
        <view class="section-head">
          <view class="section-title">最近任务</view>
          <view class="section-head__sub">继续处理未完成事项</view>
        </view>
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
import { DEMO_ACCOUNT } from '../../config/demo-account'
import { ALLOW_DEMO_FALLBACK } from '../../config/env'
import { api } from '../../utils/api'
import { addHistory, getHistory, saveJourney } from '../../utils/journey'
import { buildPurposeFlow } from '../../utils/purpose'
import { formatDateTime, healthClass, healthLabel, inspectionStatusLabel, orderStateLabel } from '../../utils/format'
import { getBindTicket } from '../../utils/session'

function withDisplayLabels(cockpit) {
  const healthSummary = cockpit?.health_summary || {}
  const measuredText = formatDateTime(healthSummary.latest_measured_at)
  return {
    ...cockpit,
    health_state_label: healthLabel(cockpit?.health_state),
    health_state_class: healthClass(cockpit?.health_state),
    health_state_pill_class: {
      normal: 'status-pill status-pill--success',
      notice: 'status-pill status-pill--warning',
      warning: 'status-pill status-pill--danger',
      critical: 'status-pill status-pill--danger',
      unknown: 'status-pill',
    }[String(cockpit?.health_state || '').toLowerCase()] || 'status-pill',
    latest_measured_at_text: measuredText,
    latest_measured_at_short: measuredText === '-' ? '-' : measuredText.slice(5),
    health_summary: {
      ...healthSummary,
      latest_order_status_text: orderStateLabel(healthSummary.latest_order_status),
    },
  }
}

function withHistoryView(items) {
  return (items || []).map((item) => ({
    ...item,
    updated_at_text: formatDateTime(item.updatedAt),
  }))
}

function inspectionStatusRank(status) {
  const rank = {
    critical: 0,
    warning: 1,
    notice: 2,
    unknown: 3,
    normal: 4,
  }
  return rank[String(status || '').toLowerCase()] ?? 5
}

function withInspectionView(item) {
  const status = String(item?.status || 'unknown').toLowerCase()
  const pillClass = {
    normal: 'status-pill--success',
    notice: 'status-pill--warning',
    warning: 'status-pill--danger',
    critical: 'status-pill--danger',
  }[status] || ''
  return {
    ...item,
    status_text: inspectionStatusLabel(status),
    status_class: `health-focus-item--${status}`,
    status_pill_class: pillClass,
  }
}

function buildImportantInspectionItems(cockpit) {
  const summary = cockpit?.health_summary || {}
  const flags = (summary.flags || []).map((item) => ({ ...item, source: 'flag' }))
  const items = (summary.inspection_items || []).map((item) => ({ ...item, source: 'inspection' }))
  const merged = [...flags, ...items]
  const deduped = []
  merged.forEach((item) => {
    const key = item.key || item.label
    if (!key || deduped.some((existing) => (existing.key || existing.label) === key)) {
      return
    }
    deduped.push(item)
  })
  return deduped
    .sort((a, b) => inspectionStatusRank(a.status) - inspectionStatusRank(b.status))
    .slice(0, 3)
    .map(withInspectionView)
}

function buildPrimaryTask(cockpit, vehicleId) {
  const flags = cockpit?.health_summary?.flags || []
  const pending = cockpit?.health_summary?.pending_recommendations || 0
  const shopItems = cockpit?.shop_items || []
  if (flags.length) {
    return {
      id: 'health_attention',
      title: '优先确认体检异常',
      desc: `${flags[0]?.label || '当前车况'}需要先复核，确认是否影响继续骑行。`,
      primaryLabel: '体检详情',
      secondaryLabel: '预约门店',
      primaryAction: 'detail',
      secondaryAction: 'appointment',
      appointmentSubject: '异常检测处理',
      serviceKind: 'repair',
      notes: flags[0]?.advice || '',
      vehicleId,
    }
  }

  if (pending > 0) {
    return {
      id: 'recommended_maintenance',
      title: '有保养建议待确认',
      desc: `当前有 ${pending} 项建议，适合先查看明细，再预约门店确认。`,
      primaryLabel: '体检详情',
      secondaryLabel: '预约门店',
      primaryAction: 'detail',
      secondaryAction: 'appointment',
      appointmentSubject: '推荐保养咨询',
      serviceKind: 'maintenance',
      notes: `当前有 ${pending} 项推荐保养。`,
      vehicleId,
    }
  }

  if (shopItems.length > 0) {
    return {
      id: 'shop_recommendation',
      title: '已有适配服务可选',
      desc: '可以查看适配商品与服务，必要时预约门店确认。',
      primaryLabel: '适配服务',
      secondaryLabel: '体检详情',
      primaryAction: 'shop',
      secondaryAction: 'detail',
      appointmentSubject: '配件与服务咨询',
      serviceKind: 'package',
      notes: '用户从商城推荐进入，希望先了解适配方案。',
      vehicleId,
    }
  }

  return {
    id: 'steady_overview',
    title: '车况状态稳定',
    desc: '目前没有明显异常，可以查看体检详情或按里程安排保养。',
    primaryLabel: '体检详情',
    secondaryLabel: '适配服务',
    primaryAction: 'detail',
    secondaryAction: 'shop',
    appointmentSubject: '常规车况咨询',
    serviceKind: 'inspection',
    notes: '用户想先快速了解当前车况。',
    vehicleId,
  }
}

function buildDemoCockpit(vehicleId) {
  const selectedId = String(vehicleId || DEMO_ACCOUNT.selectedVehicleId || '')
  const vehicles = DEMO_ACCOUNT.cockpit.vehicles || DEMO_ACCOUNT.vehicles || []
  const selectedVehicle = vehicles.find((item) => String(item.id) === selectedId) || vehicles[0] || DEMO_ACCOUNT.cockpit.vehicle
  return withDisplayLabels({
    ...DEMO_ACCOUNT.cockpit,
    selected_vehicle_id: Number(selectedVehicle?.id || DEMO_ACCOUNT.selectedVehicleId || 0) || '',
    vehicle: selectedVehicle,
    vehicles,
  })
}

export default {
  data() {
    return {
      loading: true,
      error: '',
      useDemoMode: false,
      cockpit: {
        vehicle: {},
        health_state: 'unknown',
        health_summary: {},
      },
      vehicles: [],
      selectedVehicleId: '',
      recentHistory: [],
      purposeFlow: { steps: [], desc: '' },
      primaryTask: {},
      importantInspectionItems: [],
      switchingVehicleId: '',
    }
  },
  computed: {
    visibleVehicles() {
      return (this.vehicles || []).slice(0, 4)
    },
    vehicleOverflowCount() {
      return Math.max(0, (this.vehicles || []).length - this.visibleVehicles.length)
    },
  },
  onShow() {
    this.bootstrap()
  },
  onPullDownRefresh() {
    this.bootstrap().finally(() => uni.stopPullDownRefresh())
  },
  methods: {
    async bootstrap(vehicleIdOverride = '') {
      this.loading = true
      this.error = ''
      try {
        const session = await api.ensureCustomerSession()
        if (!session.bound) {
          uni.redirectTo({ url: `/pages/bind/index?bind_ticket=${encodeURIComponent(session.bindTicket || getBindTicket() || '')}` })
          return
        }
        const cockpit = withDisplayLabels(await api.getCockpit(vehicleIdOverride || api.getSelectedVehicleId() || ''))
        if (!cockpit?.vehicle?.id) {
          if (ALLOW_DEMO_FALLBACK) {
            this.applyDemoFallback(vehicleIdOverride || api.getSelectedVehicleId() || DEMO_ACCOUNT.selectedVehicleId)
          } else {
            this.error = '暂无车辆数据，请先联系门店完成车辆建档。'
          }
          return
        }
        this.selectedVehicleId = cockpit.selected_vehicle_id || ''
        api.saveSelectedVehicleId(this.selectedVehicleId)
        this.primaryTask = buildPrimaryTask(cockpit, this.selectedVehicleId)
        saveJourney({ ...this.primaryTask, source: 'home' })
        this.cockpit = cockpit
        this.vehicles = cockpit.vehicles || []
        this.recentHistory = withHistoryView(getHistory().slice(0, 2))
        this.purposeFlow = buildPurposeFlow(cockpit)
        this.importantInspectionItems = buildImportantInspectionItems(cockpit)
      } catch (error) {
        this.error = error?.message || '驾驶舱加载失败'
        if (ALLOW_DEMO_FALLBACK) {
          this.applyDemoFallback(vehicleIdOverride || api.getSelectedVehicleId() || DEMO_ACCOUNT.selectedVehicleId)
        }
      } finally {
        this.loading = false
      }
    },
    applyDemoFallback(vehicleId = DEMO_ACCOUNT.selectedVehicleId) {
      if (!ALLOW_DEMO_FALLBACK) return
      this.useDemoMode = true
      this.error = ''
      this.cockpit = buildDemoCockpit(vehicleId)
      this.vehicles = this.cockpit.vehicles || []
      this.selectedVehicleId = String(this.cockpit.selected_vehicle_id || vehicleId || DEMO_ACCOUNT.selectedVehicleId || '')
      api.saveSelectedVehicleId(this.selectedVehicleId)
      this.primaryTask = buildPrimaryTask(this.cockpit, this.selectedVehicleId)
      saveJourney({ ...this.primaryTask, source: 'home' })
      this.recentHistory = withHistoryView(getHistory().slice(0, 2))
      this.purposeFlow = buildPurposeFlow(this.cockpit)
      this.importantInspectionItems = buildImportantInspectionItems(this.cockpit)
    },
    switchVehicle(vehicle) {
      if (!vehicle?.id || Number(vehicle.id) === Number(this.selectedVehicleId)) {
        return
      }
      this.switchingVehicleId = String(vehicle.id)
      this.selectedVehicleId = String(vehicle.id)
      api.saveSelectedVehicleId(this.selectedVehicleId)
      uni.showToast({ title: `已切换到 ${vehicle.license_plate || '该车辆'}`, icon: 'none' })
      addHistory({
        id: 'switch_vehicle',
        title: '切换车辆',
        desc: `${vehicle.license_plate || '已切换'} ${vehicle.make || ''} ${vehicle.model || ''}`.trim(),
        source: 'home',
        vehicleId: vehicle.id,
      })
      this.bootstrap(vehicle.id)
    },
    openVehicleSwitcher() {
      if (!this.vehicles.length) {
        uni.showToast({ title: '暂无可切换车辆', icon: 'none' })
        return
      }
      if (this.vehicles.length === 1) {
        this.switchVehicle(this.vehicles[0])
        return
      }
      if (this.vehicles.length > 4) {
        this.openVehicleSelector()
        return
      }
      uni.showActionSheet({
        itemList: this.vehicles.map((vehicle) => vehicle.license_plate || `车辆 ${vehicle.id}`),
        success: ({ tapIndex }) => {
          const vehicle = this.vehicles[tapIndex]
          if (vehicle) {
            this.switchVehicle(vehicle)
          }
        },
      })
    },
    openVehicleSelector() {
      uni.navigateTo({ url: '/pages/vehicle/select?source=home' })
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
      this.goToVehicleDetail()
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
