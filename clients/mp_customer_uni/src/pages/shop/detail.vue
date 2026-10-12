<template>
  <view class="page-shell">
    <view class="page-body">
      <view v-if="error" class="error-state">{{ error }}</view>

      <view class="hero-card">
        <view class="hero-kicker">适配项目详情</view>
        <view class="hero-title">{{ item.name || '项目详情' }}</view>
        <view class="hero-subtitle">{{ item.summary_text || item.product_type_label }}</view>
        <view class="summary-band">
          <view class="summary-band__item">
            <view class="summary-band__value">{{ item.price_text }}</view>
            <view class="summary-band__label">价格</view>
          </view>
          <view class="summary-band__item">
            <view class="summary-band__value">{{ item.product_type_label }}</view>
            <view class="summary-band__label">类型</view>
          </view>
          <view class="summary-band__item">
            <view class="summary-band__value">{{ item.stock_status_text }}</view>
            <view class="summary-band__label">库存</view>
          </view>
        </view>
      </view>

      <view class="light-card">
        <view class="section-head">
          <view class="section-title">核心信息</view>
          <view class="section-head__sub">清楚看到价格、类型和库存</view>
        </view>
        <view class="list-item">
          <view class="item-title">价格</view>
          <view class="item-desc">{{ item.price_text }}</view>
        </view>
        <view class="list-item">
          <view class="item-title">类型</view>
          <view class="item-desc">{{ item.product_type_label }}</view>
        </view>
        <view class="list-item">
          <view class="item-title">库存</view>
          <view class="item-desc">{{ item.stock_status_text }}</view>
        </view>
      </view>

      <view class="light-card">
        <view class="section-head">
          <view class="section-title">下一步</view>
          <view class="section-head__sub">需要确认时预约门店复核</view>
        </view>
        <view class="btn-row">
          <button class="btn-primary" @click="goToAppointment">预约门店</button>
          <button class="btn-secondary" @click="goBackShop">返回列表</button>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { api } from '../../utils/api'
import { formatMoney, productTypeLabel } from '../../utils/format'
import { getBindTicket } from '../../utils/session'
import { saveJourney } from '../../utils/journey'

function withDetailView(item) {
  return {
    ...item,
    product_type_label: productTypeLabel(item?.product_type),
    price_text: formatMoney(item?.price),
    stock_status_text:
      item?.stock_qty === null || item?.stock_qty === undefined
        ? '库存未知'
        : Number(item.stock_qty) > 0
          ? '有库存'
          : '缺货',
    summary_text: item?.description || item?.payload?.unit || '暂无详细说明',
  }
}

export default {
  data() {
    return {
      error: '',
      vehicleId: '',
      productId: '',
      productType: 'part',
      item: {},
    }
  },
  onLoad(options) {
    if (options?.vehicle_id) this.vehicleId = Number(options.vehicle_id)
    if (options?.product_id) this.productId = Number(options.product_id)
    if (options?.product_type) this.productType = String(options.product_type)
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
        if (!this.productId) {
          throw new Error('缺少商品信息')
        }
        const resp = await api.getShopProductDetail(this.productId, {
          product_type: this.productType,
          vehicle_id: this.vehicleId || api.getSelectedVehicleId() || '',
        })
        this.item = withDetailView(resp?.item || {})
      } catch (error) {
        this.error = error?.message || '商品详情加载失败'
      }
    },
    goToAppointment() {
      const vehicleId = this.vehicleId || api.getSelectedVehicleId()
      saveJourney({
        id: 'shop_detail_to_appointment',
        title: '将商品咨询转成预约',
        desc: '从商品详情进入，确认服务内容并创建预约草稿。',
        source: 'shop_detail',
        appointmentSubject: this.item.name || '商品相关预约',
        serviceKind: this.item.product_type || 'maintenance',
        notes: `来自商品详情：${this.item.name || '商品'}`,
        vehicleId: vehicleId || null,
      })
      const query = []
      if (vehicleId) query.push(`vehicle_id=${encodeURIComponent(vehicleId)}`)
      if (this.item.name) query.push(`subject=${encodeURIComponent(this.item.name)}`)
      if (this.item.product_type) query.push(`service_kind=${encodeURIComponent(this.item.product_type)}`)
      uni.navigateTo({ url: `/pages/appointment/index${query.length ? `?${query.join('&')}` : ''}` })
    },
    goBackShop() {
      uni.switchTab({ url: '/pages/shop/index' })
    },
  },
}
</script>

<style lang="scss">
@import '../../styles/mp-customer.scss';
</style>
