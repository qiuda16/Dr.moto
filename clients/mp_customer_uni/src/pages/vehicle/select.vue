<template>
  <view class="page-shell">
    <view class="page-body">
      <view v-if="error" class="notice-banner notice-banner--soft notice-banner--compact">
        <view class="notice-banner__text">
          <view class="notice-banner__title">车辆加载提示</view>
          <view class="notice-banner__desc">{{ error }}</view>
        </view>
      </view>

      <view class="hero-card">
        <view class="hero-kicker">{{ useDemoMode ? '车辆选择（演示）' : '车辆选择' }}</view>
        <view class="hero-title">切换你的车辆</view>
        <view class="hero-subtitle">车辆很多时，先搜索车牌、车型或 VIN，再点选当前要看的车。</view>
        <view class="summary-band">
          <view class="summary-band__item">
            <view class="summary-band__value">{{ vehicles.length }}</view>
            <view class="summary-band__label">车辆总数</view>
          </view>
          <view class="summary-band__item">
            <view class="summary-band__value">{{ filteredVehicles.length }}</view>
            <view class="summary-band__label">当前结果</view>
          </view>
          <view class="summary-band__item">
            <view class="summary-band__value">{{ selectedVehicleLabel }}</view>
            <view class="summary-band__label">当前车辆</view>
          </view>
        </view>
        <view class="hero-note">当前车辆会同步首页、商城、体检详情和补录页面。</view>
      </view>

      <view class="light-card">
        <view class="section-head">
          <view class="section-title">搜索车辆</view>
          <view class="section-head__sub">支持车牌、车型、VIN、发动机号</view>
        </view>
        <input v-model="query" class="field-input" placeholder="输入车牌 / 车型 / VIN 搜索" />
        <view class="btn-row btn-row--stacked" style="margin-top: 14rpx">
          <button class="btn-primary" @tap="openVehicleCreate">新增车辆</button>
          <button class="btn-secondary" @tap="openHealthEdit">补录体检</button>
        </view>
        <view class="btn-row btn-row--stacked" style="margin-top: 12rpx">
          <button class="btn-primary btn-primary--soft" @tap="clearQuery">清空搜索</button>
          <button class="btn-secondary" @tap="refreshVehicles">重新加载</button>
        </view>
        <view class="field-help" style="margin-top: 12rpx">如果车很多，可以先筛选后，再从列表里切换或删除。</view>
      </view>

      <view class="light-card" v-if="currentVehicle">
        <view class="section-head">
          <view class="section-title">当前车辆</view>
          <view class="section-head__sub">正在同步的那一台</view>
        </view>
        <view class="vehicle-card vehicle-card--active">
          <view class="vehicle-card__head">
            <view class="vehicle-card__title">{{ currentVehicle.license_plate || `车辆 ${currentVehicle.id}` }}</view>
            <view class="status-pill status-pill--success">当前车辆</view>
          </view>
          <view class="vehicle-card__desc">{{ currentVehicle.vehicle_line || '暂无车型信息' }}</view>
          <view class="vehicle-card__meta">
            <view class="vehicle-card__chip">VIN {{ currentVehicle.vin || '-' }}</view>
            <view class="vehicle-card__chip">发动机 {{ currentVehicle.engine_code || '-' }}</view>
            <view class="vehicle-card__chip">ID {{ currentVehicle.id }}</view>
          </view>
          <view class="vehicle-card__hint">切换到其他车辆后，首页和详情页会立即跟着同步。</view>
        </view>
      </view>

      <view class="light-card">
        <view class="section-head">
          <view class="section-title">车辆列表</view>
          <view class="section-head__sub">点选后会同步首页、商城和详情页</view>
        </view>
        <view v-if="otherVehicles.length" class="card-stack">
          <view
            v-for="vehicle in otherVehicles"
            :key="vehicle.id"
            class="vehicle-card"
          >
            <view class="vehicle-card__head">
              <view class="vehicle-card__title">{{ vehicle.license_plate || `车辆 ${vehicle.id}` }}</view>
              <view class="status-pill">待切换</view>
            </view>
            <view class="vehicle-card__desc">{{ vehicle.vehicle_line || '暂无车型信息' }}</view>
            <view class="vehicle-card__meta">
              <view class="vehicle-card__chip">VIN {{ vehicle.vin || '-' }}</view>
              <view class="vehicle-card__chip">发动机 {{ vehicle.engine_code || '-' }}</view>
              <view class="vehicle-card__chip">ID {{ vehicle.id }}</view>
            </view>
            <view class="vehicle-card__hint">切换后会自动返回首页，方便继续看车况。</view>
            <view class="btn-row btn-row--stacked" style="margin-top: 14rpx">
              <button class="btn-primary" @tap.stop="chooseVehicle(vehicle)">切换</button>
              <button class="btn-secondary" @tap.stop="deleteVehicle(vehicle)">删除车辆</button>
            </view>
          </view>
        </view>
        <view v-else-if="filteredVehicles.length === 0" class="empty-state">
          <view class="empty-state__title">没有找到匹配车辆</view>
          <view class="empty-state__desc">试试换个车牌、车型或 VIN 再搜索。</view>
        </view>
        <view v-else class="empty-state">
          <view class="empty-state__title">没有其他可切换车辆</view>
          <view class="empty-state__desc">当前已经只剩这一台正在查看的车辆。</view>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { DEMO_ACCOUNT } from '../../config/demo-account'
import { ALLOW_DEMO_FALLBACK } from '../../config/env'
import { api } from '../../utils/api'
import { getBindTicket } from '../../utils/session'

function withVehicleView(vehicle) {
  const vehicleLine = [vehicle?.make, vehicle?.model, vehicle?.year ? String(vehicle.year) : ''].filter(Boolean).join(' · ')
  return {
    ...vehicle,
    vehicle_line: vehicleLine || '暂无车型信息',
  }
}

function normalizeText(value) {
  return String(value || '').trim().toLowerCase()
}

export default {
  data() {
    return {
      error: '',
      useDemoMode: false,
      query: '',
      vehicles: [],
      selectedVehicleId: '',
    }
  },
  computed: {
    currentVehicle() {
      return this.vehicles.find((item) => String(item.id) === String(this.selectedVehicleId)) || null
    },
    selectedVehicleLabel() {
      return this.currentVehicle?.license_plate || '未选择'
    },
    otherVehicles() {
      return this.filteredVehicles.filter((item) => String(item.id) !== String(this.selectedVehicleId))
    },
    filteredVehicles() {
      const q = normalizeText(this.query)
      const source = this.vehicles || []
      if (!q) {
        return source
      }
      return source.filter((vehicle) => {
        const target = [
          vehicle.license_plate,
          vehicle.make,
          vehicle.model,
          vehicle.vin,
          vehicle.engine_code,
          vehicle.vehicle_line,
        ]
          .map(normalizeText)
          .join(' ')
        return target.includes(q)
      })
    },
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
          this.applyDemoFallback()
          return
        }
        const vehicles = await api.getVehicles()
        if (!vehicles?.length) {
          this.vehicles = []
          this.selectedVehicleId = api.getSelectedVehicleId() || ''
          this.useDemoMode = false
          return
        }
        this.useDemoMode = false
        this.vehicles = (vehicles || []).map(withVehicleView)
        this.selectedVehicleId = api.getSelectedVehicleId() || String(this.vehicles[0]?.id || '')
        api.saveSelectedVehicleId(this.selectedVehicleId)
      } catch (error) {
        this.error = error?.message || '车辆列表加载失败'
        if (ALLOW_DEMO_FALLBACK) this.applyDemoFallback()
      }
    },
    applyDemoFallback() {
      if (!ALLOW_DEMO_FALLBACK) return
      this.useDemoMode = true
      this.vehicles = (DEMO_ACCOUNT.cockpit.vehicles || DEMO_ACCOUNT.vehicles || []).map(withVehicleView)
      this.selectedVehicleId = String(api.getSelectedVehicleId() || DEMO_ACCOUNT.selectedVehicleId || this.vehicles[0]?.id || '')
      api.saveSelectedVehicleId(this.selectedVehicleId)
      this.error = ''
    },
    clearQuery() {
      this.query = ''
    },
    async refreshVehicles() {
      await this.bootstrap()
    },
    openVehicleCreate() {
      uni.navigateTo({ url: '/pages/vehicle/edit' })
    },
    openHealthEdit() {
      const query = this.selectedVehicleId ? `?vehicle_id=${encodeURIComponent(this.selectedVehicleId)}` : ''
      uni.navigateTo({ url: `/pages/vehicle/health-edit${query}` })
    },
    chooseVehicle(vehicle) {
      if (!vehicle?.id) {
        return
      }
      const nextId = String(vehicle.id)
      if (nextId === String(this.selectedVehicleId)) {
        uni.showToast({ title: '已经是当前车辆', icon: 'none' })
        return
      }
      api.saveSelectedVehicleId(nextId)
      uni.showToast({ title: `已切换到 ${vehicle.license_plate || '该车辆'}`, icon: 'none' })
      const pages = getCurrentPages()
      if (pages.length > 1) {
        uni.navigateBack({ delta: 1 })
        return
      }
      uni.switchTab({ url: '/pages/index/index' })
    },
    deleteVehicle(vehicle) {
      if (!vehicle?.id) {
        return
      }
      uni.showModal({
        title: '删除车辆',
        content: `确认删除 ${vehicle.license_plate || '这台车'} 吗？删除后仍可重新添加。`,
        success: async (res) => {
          if (!res.confirm) {
            return
          }
          try {
            await api.deleteVehicle(vehicle.id)
            if (String(vehicle.id) === String(this.selectedVehicleId)) {
              api.saveSelectedVehicleId('')
            }
            uni.showToast({ title: '车辆已删除', icon: 'success' })
            await this.bootstrap()
          } catch (error) {
            uni.showToast({ title: error?.message || '删除失败', icon: 'none' })
          }
        },
      })
    },
  },
}
</script>

<style lang="scss">
@import '../../styles/mp-customer.scss';
</style>
