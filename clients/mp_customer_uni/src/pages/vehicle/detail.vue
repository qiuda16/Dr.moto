<template>
  <view class="page-shell">
    <view class="page-body">
      <view v-if="syncNotice" class="sync-state">{{ syncNotice }}</view>

      <view class="hero-card">
        <view class="hero-kicker">车辆体检详情</view>
        <view class="chip" :class="cockpit.health_state_class">{{ cockpit.health_state_label }}</view>
        <view class="hero-title">{{ cockpit.vehicle.license_plate || '车辆详情' }}</view>
        <view class="hero-subtitle">
          {{ [cockpit.vehicle.make, cockpit.vehicle.model].filter(Boolean).join(' · ') || '暂无车型信息' }}
        </view>
        <view class="hero-note">{{ reportSummaryText }}</view>
        <view class="metrics-grid metrics-grid--vehicle" style="margin-top: 18rpx">
          <view class="metric-tile">
            <view class="metric-label">最新里程</view>
            <view class="metric-value">{{ cockpit.health_summary.latest_odometer_km || '-' }}</view>
            <view class="metric-label">km</view>
          </view>
          <view class="metric-tile">
            <view class="metric-label">最近检测</view>
            <view class="metric-value">{{ cockpit.latest_measured_at_text || '-' }}</view>
            <view class="metric-label">更新时间</view>
          </view>
          <view class="metric-tile">
            <view class="metric-label">待处理建议</view>
            <view class="metric-value">{{ cockpit.health_summary.pending_recommendations || 0 }}</view>
            <view class="metric-label">项</view>
          </view>
        </view>
        <view class="step-list" style="margin-top: 18rpx">
          <view class="step-item step-item--active">
            <view class="step-item__index">1</view>
            <view class="step-item__body">
              <view class="step-item__title">先看检测项</view>
              <view class="step-item__desc">异常和关注项会优先显示，方便快速判断。</view>
            </view>
          </view>
          <view class="step-item">
            <view class="step-item__index">2</view>
            <view class="step-item__body">
              <view class="step-item__title">必要时补录</view>
              <view class="step-item__desc">可以手动填写体检数据，并自动记录时间。</view>
            </view>
          </view>
          <view class="step-item">
            <view class="step-item__index">3</view>
            <view class="step-item__body">
              <view class="step-item__title">再去预约处理</view>
              <view class="step-item__desc">把问题交给门店，形成预约草稿或工单。</view>
            </view>
          </view>
        </view>
        <view class="btn-row" style="margin-top: 18rpx">
          <button class="btn-primary" @click="goToAppointment">预约门店</button>
          <button class="btn-secondary" @click="goShop">适配服务</button>
        </view>
        <view class="btn-row" style="margin-top: 12rpx">
          <button class="btn-secondary btn-primary--soft" @click="goToHealthEdit">手动补录</button>
        </view>
      </view>

      <view class="light-card">
        <view class="section-head">
          <view class="section-title">检测项目</view>
          <view class="section-head__sub">按分类列出，有数据就显示数值，没有就标注无数据</view>
        </view>
        <view class="summary-band" style="margin-top: 0; margin-bottom: 18rpx">
          <view class="summary-band__item">
            <view class="summary-band__value">{{ inspectionOverview.normal }}</view>
            <view class="summary-band__label">正常</view>
          </view>
          <view class="summary-band__item">
            <view class="summary-band__value">{{ inspectionOverview.notice }}</view>
            <view class="summary-band__label">关注</view>
          </view>
          <view class="summary-band__item">
            <view class="summary-band__value">{{ inspectionOverview.warning }}</view>
            <view class="summary-band__label">建议处理</view>
          </view>
        </view>
        <view class="inspection-group-list">
          <view v-for="group in inspectionGroups" :key="group.key" class="inspection-group">
            <view class="inspection-group__head">
              <view>
                <view class="inspection-group__title">{{ group.label }}</view>
                <view class="inspection-group__sub">{{ group.description }}</view>
              </view>
              <view class="inspection-group__count">{{ group.count_label }}</view>
            </view>
            <view class="inspection-item-list">
              <view
                v-for="item in group.items"
                :key="item.key || item.label"
                class="inspection-item-row"
                :class="{ 'inspection-item-row--clickable': item.has_data }"
                @click="item.has_data ? inspectItem(item) : null"
              >
                <view class="inspection-item-row__top">
                  <view class="inspection-item-row__body">
                    <view class="inspection-item-row__title">{{ item.label }}</view>
                    <view class="inspection-item-row__desc">{{ group.label }}</view>
                  </view>
                  <view class="inspection-item-row__status" :class="{ 'inspection-item-row__status--empty': !item.has_data }">
                    {{ item.status_text }}
                  </view>
                  <view class="inspection-item-row__value" :class="{ 'inspection-item-row__value--empty': !item.has_data }">
                    {{ item.display_value }}
                  </view>
                </view>
                <view class="inspection-item-row__bottom">
                  <view class="inspection-item-row__advice">{{ item.advice || '建议到店复核。' }}</view>
                </view>
              </view>
            </view>
          </view>
        </view>
      </view>

      <view class="light-card">
        <view class="section-head">
          <view class="section-title">推荐服务</view>
          <view class="section-head__sub">根据当前体检结果给出的处理建议</view>
        </view>
        <view v-if="services.length">
          <view v-for="item in services" :key="item.id || item.name" class="list-item">
            <view class="item-title">{{ item.service_name || item.name }}</view>
            <view class="item-desc">{{ item.description || item.suggested_price_text }}</view>
            <view class="tag-row" style="margin-top: 10rpx">
              <view class="choice-pill choice-pill--soft">{{ item.suggested_price_text }}</view>
            </view>
          </view>
        </view>
        <view v-else class="muted">还没有推荐服务。</view>
      </view>

      <view class="light-card">
        <view class="section-head">
          <view class="section-title">历史工单</view>
          <view class="section-head__sub">折叠查看最近处理过的门店任务</view>
        </view>
        <view class="secondary-menu-toggle" @click="showHistoryOrders = !showHistoryOrders">
          <view>
            <view class="secondary-menu-toggle__title">{{ showHistoryOrders ? '收起历史工单' : '展开历史工单' }}</view>
            <view class="secondary-menu-toggle__desc">最近 {{ orders.length }} 条处理记录</view>
          </view>
          <view class="secondary-menu-toggle__arrow">{{ showHistoryOrders ? '收起' : '展开' }}</view>
        </view>
        <view v-if="showHistoryOrders" class="secondary-menu-panel">
          <view v-if="orders.length">
            <view v-for="item in orders" :key="item.id" class="list-item">
              <view class="item-title">{{ item.subject || item.order_no || `工单 ${item.id}` }}</view>
              <view class="item-desc">{{ item.state_text }} · {{ item.payment_status_text }}</view>
              <view class="item-meta">{{ item.amount_total_text }}</view>
            </view>
          </view>
          <view v-else class="muted">还没有历史工单。</view>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { api } from '../../utils/api'
import { formatDateTime, formatMoney, healthClass, healthLabel, inspectionStatusLabel, orderStateLabel, paymentStatusLabel } from '../../utils/format'
import { getBindTicket } from '../../utils/session'
import { saveJourney } from '../../utils/journey'

const INSPECTION_GROUPS = [
  {
    key: 'power',
    label: '动力系统',
    description: '发动机相关体检项',
    items: [{ key: 'engine_rpm', label: '发动机转速', unit: 'rpm' }],
  },
  {
    key: 'battery',
    label: '电瓶系统',
    description: '电源与起动相关体检项',
    items: [{ key: 'battery_voltage', label: '电瓶电压', unit: 'V' }],
  },
  {
    key: 'tires',
    label: '胎压系统',
    description: '前后轮胎压',
    items: [
      { key: 'tire_front_psi', label: '前胎压', unit: 'psi' },
      { key: 'tire_rear_psi', label: '后胎压', unit: 'psi' },
    ],
  },
  {
    key: 'cooling',
    label: '冷却系统',
    description: '冷却温度与散热状态',
    items: [{ key: 'coolant_temp_c', label: '冷却液温度', unit: '°C' }],
  },
  {
    key: 'lubrication',
    label: '润滑系统',
    description: '机油寿命与保养提醒',
    items: [{ key: 'oil_life_percent', label: '机油寿命', unit: '%' }],
  },
  {
    key: 'electrical',
    label: '车身电气',
    description: '灯光和车身电气状态',
    items: [{ key: 'lighting', label: '灯光状态', unit: '' }],
  },
  {
    key: 'drivetrain',
    label: '传动系统',
    description: '链条 / 皮带状态',
    items: [{ key: 'chain_belt', label: '链条 / 皮带', unit: '' }],
  },
]

function hasInspectionData(value) {
  if (value === null || value === undefined) {
    return false
  }
  const text = String(value).trim()
  return text !== '' && text !== '-'
}

function buildInspectionGroups(items) {
  const source = items || []
  return INSPECTION_GROUPS.map((group) => {
    const groupItems = group.items.map((definition) => {
      const matched = source.find((item) => item.key === definition.key)
      const hasData = hasInspectionData(matched?.value)
      return {
        key: definition.key,
        label: definition.label,
        unit: definition.unit,
        value: matched?.value ?? null,
        display_value: hasData ? matched.value : '无数据',
        has_data: hasData,
        status_text: matched?.status_text || '未采集',
        advice: matched?.advice || '暂无数据，建议到店补采。',
      }
    })
    return {
      ...group,
      count_label: `${groupItems.length} 项`,
      items: groupItems,
    }
  })
}

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
      syncNotice: '',
      vehicleId: '',
      cockpit: { vehicle: {}, health_summary: {} },
      inspectionItems: [],
      inspectionGroups: buildInspectionGroups([]),
      orders: [],
      services: [],
      showHistoryOrders: false,
    }
  },
  computed: {
    reportSummaryText() {
      const parts = []
      if (this.cockpit.health_state_label) {
        parts.push(`当前车况：${this.cockpit.health_state_label}`)
      }
      const latestMeasured =
        this.cockpit.latest_measured_at_text ||
        formatDateTime(this.cockpit.health_summary?.latest_measured_at) ||
        this.cockpit.health_summary?.latest_measured_at_text
      if (latestMeasured) {
        parts.push(`最近体检 ${latestMeasured}`)
      }
      const pending = this.cockpit.health_summary?.pending_recommendations
      if (pending !== undefined && pending !== null) {
        parts.push(`待处理 ${pending} 项`)
      }
      return parts.join(' · ') || '当前车辆已进入体检报告页，先看异常再决定下一步。'
    },
    inspectionOverview() {
      return this.inspectionItems.reduce(
        (acc, item) => {
          const status = String(item?.status || 'unknown').toLowerCase()
          if (status === 'normal') {
            acc.normal += 1
          } else if (status === 'notice') {
            acc.notice += 1
          } else if (status === 'warning' || status === 'critical') {
            acc.warning += 1
          } else {
            acc.unknown += 1
          }
          return acc
        },
        { normal: 0, notice: 0, warning: 0, unknown: 0 },
      )
    },
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
      this.syncNotice = ''
      this.inspectionGroups = buildInspectionGroups([])
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
        this.inspectionGroups = buildInspectionGroups(this.inspectionItems)
        this.orders = (ordersResp?.items || []).map((item) => ({
          ...item,
          state_text: orderStateLabel(item?.state),
          payment_status_text: paymentStatusLabel(item?.payment_summary),
          amount_total_text: formatMoney(item?.amount_total),
        }))
        this.services = (services || []).map((item) => ({
          ...item,
          suggested_price_text: formatMoney(item?.suggested_price),
        }))
      } catch (error) {
        this.syncNotice = '数据同步中，部分内容暂未更新'
        this.cockpit = withDisplayLabels(this.cockpit || { vehicle: {}, health_summary: {} })
        this.inspectionItems = []
        this.inspectionGroups = buildInspectionGroups([])
        this.orders = []
        this.services = []
      }
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
    goShop() {
      uni.switchTab({ url: '/pages/shop/index' })
    },
    goToHealthEdit() {
      const query = this.vehicleId ? `?vehicle_id=${encodeURIComponent(this.vehicleId)}` : ''
      uni.navigateTo({ url: `/pages/vehicle/health-edit${query}` })
    },
    inspectItem(item) {
      saveJourney({
        id: 'inspection_item_review',
        title: `检测项咨询：${item.label}`,
        desc: '从车辆详情中进入，向门店确认风险和处理时机。',
        source: 'vehicle',
        appointmentSubject: '检测项异常咨询',
        serviceKind: 'inspection',
        notes: `${item.label}：${item.value || '-'}，状态：${item.status_text}`,
        vehicleId: this.vehicleId || null,
      })
      uni.navigateTo({
        url: `/pages/appointment/index?vehicle_id=${encodeURIComponent(this.vehicleId || '')}&subject=${encodeURIComponent('检测项异常咨询')}&service_kind=inspection&notes=${encodeURIComponent(`${item.label}：${item.value || '-'}，状态：${item.status_text}`)}`,
      })
    },
  },
}
</script>

<style lang="scss">
@import '../../styles/mp-customer.scss';
</style>
