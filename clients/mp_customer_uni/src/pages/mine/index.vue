<template>
  <view class="page-shell">
    <view class="page-body">
      <view v-if="error" class="error-state">{{ error }}</view>

      <view class="hero-card">
        <view class="hero-kicker">{{ useDemoMode ? '车主档案（演示）' : '车主档案' }}</view>
        <view class="hero-title">{{ profile.customer_name || '车主账号' }}</view>
        <view class="hero-subtitle">{{ profile.phone_masked || '未绑定手机号' }} · {{ profile.store_id || 'default' }}</view>
        <view class="hero-note">已绑定 {{ vehicles.length }} 台车，当前查看 {{ selectedVehicleLabel }}</view>
      </view>

      <view class="light-card">
        <view class="section-head">
          <view class="section-title">账号信息</view>
          <view class="section-head__sub">客户身份与服务门店</view>
        </view>
        <view class="profile-banner">
          <view class="profile-banner__row">
            <view class="profile-banner__label">客户编号</view>
            <view class="profile-banner__value">{{ profile.partner_id || '-' }}</view>
          </view>
          <view class="profile-banner__row">
            <view class="profile-banner__label">手机号</view>
            <view class="profile-banner__value">{{ profile.phone_masked || '-' }}</view>
          </view>
          <view class="profile-banner__row">
            <view class="profile-banner__label">服务门店</view>
            <view class="profile-banner__value">{{ profile.store_id || '-' }}</view>
          </view>
          <view class="profile-banner__row">
            <view class="profile-banner__label">选中车辆</view>
            <view class="profile-banner__value">{{ selectedVehicleLabel }}</view>
          </view>
        </view>
      </view>

      <view class="light-card">
        <view class="section-head">
          <view class="section-title">车辆档案</view>
          <view class="section-head__sub">切换后同步车况和适配服务</view>
        </view>
        <view v-if="vehicles.length" class="card-stack">
          <view
            v-for="vehicle in visibleVehicles"
            :key="vehicle.id"
            class="vehicle-card"
            :class="{ 'vehicle-card--active': String(vehicle.id) === String(selectedVehicleId) }"
            @click="switchVehicle(vehicle)"
          >
            <view class="vehicle-card__head">
              <view class="vehicle-card__title">{{ vehicle.license_plate || `车辆 ${vehicle.id}` }}</view>
              <view class="status-pill" :class="String(vehicle.id) === String(selectedVehicleId) ? 'status-pill--success' : ''">
                {{ String(vehicle.id) === String(selectedVehicleId) ? '当前车辆' : '可切换' }}
              </view>
            </view>
            <view class="vehicle-card__desc">{{ vehicle.vehicle_line || '暂无车型信息' }}</view>
            <view class="vehicle-card__meta">
              <view class="vehicle-card__chip">VIN {{ vehicle.vin || '-' }}</view>
              <view class="vehicle-card__chip">发动机 {{ vehicle.engine_code || '-' }}</view>
            </view>
          </view>
          <view v-if="vehicleOverflowCount > 0" class="shortcut-card shortcut-card--soft" @click="openVehicleSelector">
            <view class="shortcut-card__title">还有 {{ vehicleOverflowCount }} 台车</view>
            <view class="shortcut-card__desc">进入车辆选择页查看全部</view>
          </view>
        </view>
        <view v-else class="muted">当前账号还没有车辆。</view>
      </view>

      <view class="light-card">
        <view class="section-head">
          <view class="section-title">快捷入口</view>
          <view class="section-head__sub">常用服务动作</view>
        </view>
        <view class="shortcut-grid">
          <view class="shortcut-card" @click="goToHome">
            <view class="shortcut-card__title">车况首页</view>
            <view class="shortcut-card__desc">查看当前状态</view>
          </view>
          <view class="shortcut-card" @click="goToShop">
            <view class="shortcut-card__title">适配服务</view>
            <view class="shortcut-card__desc">配件与套餐</view>
          </view>
          <view class="shortcut-card" @click="goToHistory">
            <view class="shortcut-card__title">服务记录</view>
            <view class="shortcut-card__desc">查看历史动作</view>
          </view>
          <view class="shortcut-card" @click="openVehicleSelector">
            <view class="shortcut-card__title">车辆管理</view>
            <view class="shortcut-card__desc">增删与切换车辆</view>
          </view>
          <view class="shortcut-card" @click="openHealthEdit">
            <view class="shortcut-card__title">补录体检</view>
            <view class="shortcut-card__desc">手动填写检测项</view>
          </view>
        </view>
        <view class="btn-row">
          <button class="btn-primary" @click="goToBind">重新绑定车辆</button>
          <button class="btn-secondary" @click="logout">退出账号</button>
        </view>
      </view>

      <view class="light-card">
        <view class="section-head">
          <view class="section-title">二级菜单</view>
          <view class="section-head__sub">体检数据、工单和提醒</view>
        </view>
        <view class="secondary-menu-toggle" @click="toggleAdvancedMenu">
          <view>
            <view class="secondary-menu-toggle__title">{{ showAdvancedMenu ? '收起详情面板' : '展开详情面板' }}</view>
            <view class="secondary-menu-toggle__desc">重点检测项、体检记录、最近工单、提醒设置</view>
          </view>
          <view class="secondary-menu-toggle__arrow">{{ showAdvancedMenu ? '收起' : '展开' }}</view>
        </view>
        <view v-if="showAdvancedMenu" class="secondary-menu-panel">
          <view class="detail-grid">
            <view class="detail-card">
              <view class="detail-card__title">最新里程</view>
              <view class="detail-card__value">{{ cockpit.health_summary.latest_odometer_km || '-' }}</view>
              <view class="detail-card__desc">当前车辆里程</view>
            </view>
            <view class="detail-card">
              <view class="detail-card__title">体检记录</view>
              <view class="detail-card__value">{{ cockpit.health_summary.health_records_count || 0 }}</view>
              <view class="detail-card__desc">累计体检数量</view>
            </view>
            <view class="detail-card">
              <view class="detail-card__title">待处理建议</view>
              <view class="detail-card__value">{{ cockpit.health_summary.pending_recommendations || 0 }}</view>
              <view class="detail-card__desc">需要尽快处理</view>
            </view>
            <view class="detail-card">
              <view class="detail-card__title">最近检测</view>
              <view class="detail-card__value">{{ cockpit.latest_measured_at_text || '-' }}</view>
              <view class="detail-card__desc">最新体检时间</view>
            </view>
          </view>

          <view class="section-divider"></view>

          <view class="section-head">
            <view class="section-title">重点检测项</view>
            <view class="section-head__sub">异常与关注项优先展示</view>
          </view>
          <view v-if="inspectionItems.length" class="health-focus-list health-focus-list--light">
            <view v-for="item in inspectionItems" :key="item.key || item.label" class="health-focus-item" :class="item.status_class">
              <view class="health-focus-item__head">
                <view class="health-focus-item__title">{{ item.label }}</view>
                <view class="status-pill" :class="item.status_pill_class">{{ item.status_text }}</view>
              </view>
              <view class="health-focus-item__value">{{ item.value || '-' }}</view>
              <view class="health-focus-item__desc">{{ item.advice || '建议到店复核。' }}</view>
            </view>
          </view>
          <view v-else class="muted">当前车辆还没有检测项。</view>

          <view class="section-divider"></view>

          <view class="section-head">
            <view class="section-title">最近体检</view>
            <view class="section-head__sub">按时间倒序展示</view>
          </view>
          <view v-if="healthRecords.length">
            <view v-for="record in healthRecords" :key="record.id" class="list-item list-item--soft">
              <view class="item-title">{{ record.measured_at_text }}</view>
              <view class="item-desc">里程 {{ record.odometer_km }} km · 电瓶 {{ record.battery_voltage_text }} · 机油寿命 {{ record.oil_life_percent_text }}</view>
              <view class="item-meta">录入时间 {{ record.created_at_text || record.measured_at_text || '-' }}</view>
              <view class="item-meta">{{ record.notes || '无备注' }}</view>
            </view>
          </view>
          <view v-else class="muted">暂无体检记录。</view>

          <view class="section-divider"></view>

          <view class="section-head">
            <view class="section-title">最近工单</view>
            <view class="section-head__sub">门店状态同步</view>
          </view>
          <view v-if="maintenanceOrders.length">
            <view v-for="order in maintenanceOrders" :key="order.id" class="list-item list-item--soft">
              <view class="item-title">{{ order.name || order.id }}</view>
              <view class="item-desc">{{ order.vehicle_plate || '-' }} · {{ order.status_text }} · {{ order.payment_status_text }}</view>
              <view class="item-meta">{{ order.date_planned_text }} · {{ order.amount_total_text }}</view>
            </view>
          </view>
          <view v-else class="muted">当前账号还没有工单。</view>

          <view class="section-divider"></view>

          <view class="section-head">
            <view class="section-title">订阅设置</view>
            <view class="section-head__sub">提醒偏好与通知方式</view>
          </view>
          <view v-if="subscriptions.length">
            <view v-for="item in subscriptions" :key="item.id" class="list-item list-item--soft">
              <view class="item-title">{{ item.vehicle_label || '全局订阅' }}</view>
              <view class="item-desc">{{ item.notify_enabled_text }} · {{ item.channel_text }}</view>
              <view class="item-meta">{{ item.remind_before_days }} 天前 / {{ item.remind_before_km }} km 前提醒</view>
            </view>
          </view>
          <view v-else class="muted">暂无订阅设置。</view>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { DEMO_ACCOUNT } from '../../config/demo-account'
import { ALLOW_DEMO_FALLBACK } from '../../config/env'
import { api } from '../../utils/api'
import { clearBindTicket, clearSession, getBindTicket } from '../../utils/session'
import { formatDateTime, formatMoney, healthLabel, inspectionStatusLabel, orderStateLabel, paymentStatusLabel } from '../../utils/format'

function withVehicleView(vehicle) {
  const vehicleLine = [vehicle?.make, vehicle?.model, vehicle?.year ? String(vehicle.year) : ''].filter(Boolean).join(' · ')
  return {
    ...vehicle,
    vehicle_line: vehicleLine || '暂无车型信息',
  }
}

function withHealthRecordView(record) {
  return {
    ...record,
    measured_at_text: formatDateTime(record?.measured_at),
    created_at_text: formatDateTime(record?.created_at),
    battery_voltage_text: record?.battery_voltage === null || record?.battery_voltage === undefined ? '-' : `${Number(record.battery_voltage).toFixed(1)} V`,
    oil_life_percent_text: record?.oil_life_percent === null || record?.oil_life_percent === undefined ? '-' : `${Number(record.oil_life_percent).toFixed(0)}%`,
  }
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

function withInspectionItemView(item) {
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

function withOrderView(order) {
  return {
    ...order,
    status_text: orderStateLabel(order?.state),
    payment_status_text: paymentStatusLabel(order?.payment_summary),
    date_planned_text: formatDateTime(order?.date_planned),
    amount_total_text: formatMoney(order?.amount_total),
  }
}

function withSubscriptionView(item, vehicles) {
  const matchedVehicle = (vehicles || []).find((vehicle) => String(vehicle.id) === String(item?.vehicle_id))
  return {
    ...item,
    vehicle_label: matchedVehicle?.vehicle_line || matchedVehicle?.license_plate || (item?.vehicle_id ? `车辆 ${item.vehicle_id}` : '全局订阅'),
    notify_enabled_text: item?.notify_enabled ? '已开启提醒' : '已关闭提醒',
    channel_text: item?.prefer_channel || 'wechat_subscribe',
  }
}

function withCockpitView(cockpit) {
  return {
    ...cockpit,
    health_state_label: healthLabel(cockpit?.health_state),
    latest_measured_at_text: formatDateTime(cockpit?.health_summary?.latest_measured_at),
    health_summary: {
      ...(cockpit?.health_summary || {}),
      latest_order_status_text: orderStateLabel(cockpit?.health_summary?.latest_order_status),
    },
  }
}

export default {
  data() {
    return {
      error: '',
      useDemoMode: false,
      profile: {},
      vehicles: [],
      selectedVehicleId: '',
      selectedVehicleLabel: '未选择车辆',
      showAdvancedMenu: false,
      cockpit: {
        health_state_label: '未知',
        health_summary: {},
      },
      inspectionItems: [],
      healthRecords: [],
      maintenanceOrders: [],
      subscriptions: [],
    }
  },
  computed: {
    visibleVehicles() {
      return (this.vehicles || []).slice(0, 5)
    },
    vehicleOverflowCount() {
      return Math.max(0, (this.vehicles || []).length - this.visibleVehicles.length)
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
        this.profile = await api.getMe()
        this.vehicles = (await api.getVehicles()).map(withVehicleView)
        if (!this.vehicles.length) {
          this.applyDemoFallback()
          return
        }
        const selectedId = api.getSelectedVehicleId() || this.vehicles[0]?.id || ''
        this.selectedVehicleId = selectedId ? String(selectedId) : ''
        if (this.selectedVehicleId) {
          api.saveSelectedVehicleId(this.selectedVehicleId)
        }
        this.selectedVehicleLabel = this.resolveVehicleLabel(this.selectedVehicleId)
        await this.loadVehicleBundle(this.selectedVehicleId)
      } catch (error) {
        this.error = error?.message || '个人中心加载失败'
        if (ALLOW_DEMO_FALLBACK) this.applyDemoFallback()
      }
    },
    applyDemoFallback() {
      if (!ALLOW_DEMO_FALLBACK) return
      this.useDemoMode = true
      this.error = ''
      this.profile = DEMO_ACCOUNT.profile
      this.vehicles = DEMO_ACCOUNT.vehicles
      this.selectedVehicleId = String(DEMO_ACCOUNT.selectedVehicleId)
      this.selectedVehicleLabel = DEMO_ACCOUNT.cockpit.vehicle.vehicle_line
      this.cockpit = DEMO_ACCOUNT.cockpit
      this.inspectionItems = (DEMO_ACCOUNT.cockpit.health_summary.inspection_items || [])
        .slice()
        .sort((a, b) => inspectionStatusRank(a.status) - inspectionStatusRank(b.status))
        .map(withInspectionItemView)
      this.healthRecords = DEMO_ACCOUNT.healthRecords
      this.maintenanceOrders = DEMO_ACCOUNT.maintenanceOrders
      this.subscriptions = DEMO_ACCOUNT.subscriptions
    },
    resolveVehicleLabel(vehicleId) {
      const matched = this.vehicles.find((vehicle) => String(vehicle.id) === String(vehicleId))
      if (!matched) {
        return '未选择车辆'
      }
      return matched.vehicle_line || matched.license_plate || `车辆 ${matched.id}`
    },
    async loadVehicleBundle(vehicleId) {
      const [cockpitResp, recordsResp, ordersResp, subscriptionsResp] = await Promise.all([
        api.getCockpit(vehicleId || ''),
        vehicleId ? api.getVehicleHealthRecords(vehicleId, 3) : Promise.resolve([]),
        vehicleId ? api.getVehicleMaintenanceOrders(vehicleId, 1, 3) : Promise.resolve({ items: [] }),
        api.getSubscriptions(),
      ])
      this.cockpit = withCockpitView(cockpitResp)
      this.inspectionItems = (cockpitResp?.health_summary?.inspection_items || [])
        .slice()
        .sort((a, b) => inspectionStatusRank(a.status) - inspectionStatusRank(b.status))
        .map(withInspectionItemView)
      this.healthRecords = (recordsResp || []).map(withHealthRecordView)
      this.maintenanceOrders = (ordersResp?.items || []).map(withOrderView)
      this.subscriptions = (subscriptionsResp || []).map((item) => withSubscriptionView(item, this.vehicles))
    },
    async switchVehicle(vehicle) {
      if (!vehicle?.id || String(vehicle.id) === String(this.selectedVehicleId)) {
        return
      }
      this.selectedVehicleId = String(vehicle.id)
      this.selectedVehicleLabel = vehicle.vehicle_line || vehicle.license_plate || `车辆 ${vehicle.id}`
      api.saveSelectedVehicleId(this.selectedVehicleId)
      try {
        await this.loadVehicleBundle(this.selectedVehicleId)
      } catch (error) {
        this.error = error?.message || '切换车辆失败'
      }
    },
    toggleAdvancedMenu() {
      this.showAdvancedMenu = !this.showAdvancedMenu
    },
    goToBind() {
      uni.navigateTo({ url: `/pages/bind/index?bind_ticket=${encodeURIComponent(getBindTicket() || '')}` })
    },
    goToHome() {
      uni.switchTab({ url: '/pages/index/index' })
    },
    goToShop() {
      uni.switchTab({ url: '/pages/shop/index' })
    },
    goToHistory() {
      uni.navigateTo({ url: '/pages/history/index' })
    },
    openVehicleSelector() {
      uni.navigateTo({ url: '/pages/vehicle/select?source=mine' })
    },
    openHealthEdit() {
      const query = this.selectedVehicleId ? `?vehicle_id=${encodeURIComponent(this.selectedVehicleId)}` : ''
      uni.navigateTo({ url: `/pages/vehicle/health-edit${query}` })
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
