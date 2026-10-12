<template>
  <view class="page-shell">
    <view class="page-body">
      <view v-if="error" class="error-state">{{ error }}</view>

      <view class="hero-card">
        <view class="hero-kicker">{{ useDemoMode ? '适配服务（演示）' : '适配服务' }}</view>
        <view class="hero-title">{{ vehicleLibraryTitle }}</view>
        <view class="shop-focus">
          <view class="shop-focus__row">
            <text class="shop-focus__label">当前车辆</text>
            <text class="shop-focus__value">{{ currentVehicleLabel }}</text>
          </view>
          <view class="shop-focus__row">
            <text class="shop-focus__label">当前关注</text>
            <text class="shop-focus__value">{{ activeKindLabel }}</text>
          </view>
          <view class="shop-focus__lead">
            <view class="shop-focus__lead-label">建议优先看</view>
            <view class="shop-focus__lead-value">{{ priorityTypeLabel }}</view>
            <view class="shop-focus__lead-desc">{{ priorityTypeHint }}</view>
          </view>
          <view class="shop-focus__chips">
            <view v-for="item in focusTags" :key="item" class="choice-pill choice-pill--soft choice-pill--wide shop-focus__chip">
              {{ item }}
            </view>
          </view>
        </view>
      </view>

      <view class="light-card">
        <view class="section-head">
          <view class="section-title">筛选条件</view>
          <view class="section-head__sub">只保留类型和关键词两个入口</view>
        </view>
        <view class="choice-row choice-row--loose">
          <view
            v-for="item in categories"
            :key="item.value"
            class="choice-pill choice-pill--soft choice-pill--wide"
            :class="{ 'choice-pill--active': item.value === kind }"
            @click="chooseKind(item.value)"
          >
            {{ item.label }}
          </view>
        </view>
        <view class="form-panel" style="margin-top: 14rpx;">
          <input v-model="query" class="field-input" placeholder="搜索商品、品牌或服务" />
          <view class="shop-actions">
            <button class="btn-primary shop-actions__primary" @click="bootstrap">查适配商品</button>
            <button class="btn-secondary shop-actions__secondary" @click="createConsultation">预约确认</button>
          </view>
        </view>
      </view>

      <view class="light-card">
        <view class="section-head">
          <view class="section-title">相关商品</view>
          <view class="section-head__sub">只显示与你的车型相关的配件与服务</view>
        </view>
        <view v-if="groupedProducts.length">
          <view v-for="group in groupedProducts" :key="group.key" class="product-group">
            <view class="product-group__head">
              <view class="product-group__title">{{ group.label }}</view>
              <view class="product-group__count">{{ group.items.length }} 个</view>
            </view>
            <view v-for="item in group.items" :key="`${group.key}-${item.id}`" class="product-card" @click="openDetail(item)">
              <view class="product-card__head">
                <view class="product-card__title-wrap">
                  <view class="item-title">{{ item.name }}</view>
                  <view class="product-card__meta">{{ item.product_type_label }} · 适配当前车型</view>
                </view>
                <view class="choice-pill choice-pill--soft">{{ item.price_text }}</view>
              </view>
              <view class="item-desc">{{ item.description || item.product_type_label }}</view>
            </view>
          </view>
        </view>
        <view v-else class="empty-state">
          <view class="empty-state__title">暂未找到适配项目</view>
          <view class="empty-state__desc">可以放宽筛选条件，或预约门店确认具体配件和服务。</view>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { DEMO_ACCOUNT } from '../../config/demo-account'
import { ALLOW_DEMO_FALLBACK } from '../../config/env'
import { api } from '../../utils/api'
import { formatMoney, productTypeLabel } from '../../utils/format'
import { getBindTicket } from '../../utils/session'
import { saveJourney } from '../../utils/journey'

function withProductView(item) {
  return {
    ...item,
    product_type_label: productTypeLabel(item?.product_type),
    price_text: formatMoney(item?.price),
  }
}

export default {
  data() {
    return {
      loading: true,
      error: '',
      useDemoMode: false,
      vehicleId: '',
      currentVehicleLabel: '未选择车辆',
      currentVehicleModelLabel: '',
      kind: '',
      query: '',
      products: [],
      focusTags: [],
      categories: [
        { value: '', label: '全部' },
        { value: 'part', label: '配件' },
        { value: 'service', label: '服务' },
        { value: 'package', label: '套餐' },
      ],
    }
  },
  onShow() {
    this.bootstrap()
  },
  computed: {
    vehicleLibraryTitle() {
      return `${this.currentVehicleModelLabel || '车型'}配件库`
    },
    activeKindLabel() {
      const found = this.categories.find((item) => item.value === this.kind)
      return found?.label || '全部'
    },
    groupedProducts() {
      return this.groupProducts(this.products)
    },
    priorityTypeLabel() {
      if (this.kind) {
        return this.activeKindLabel
      }
      const ordered = this.groupedProducts.find((group) => group.items.length)
      return ordered?.label || '套餐'
    },
    priorityTypeHint() {
      if (this.kind === 'part') {
        return '先看具体配件型号，再确认适配当前车辆。'
      }
      if (this.kind === 'service') {
        return '先看服务项目和工时，再预约门店确认。'
      }
      if (this.kind === 'package') {
        return '优先看套餐，通常更适合直接下单。'
      }
      return '建议先看套餐和服务，再补充查看配件。'
    },
  },
  methods: {
    buildFocusTags(items) {
      const names = (items || [])
        .map((item) => item.product_type_label || item.category || '')
        .filter(Boolean)
      const unique = [...new Set(names)]
      if (unique.length) {
        return unique.slice(0, 3)
      }
      return ['车型适配', '服务确认', '门店复核']
    },
    groupProducts(items) {
      const source = items || []
      const order = [
        { key: 'package', label: '套餐' },
        { key: 'service', label: '服务' },
        { key: 'part', label: '配件' },
      ]
      return order
        .map((group) => ({
          ...group,
          items: source.filter((item) => item.product_type === group.key),
        }))
        .filter((group) => group.items.length)
    },
    async bootstrap() {
      this.loading = true
      this.error = ''
      try {
        const session = await api.ensureCustomerSession()
        if (!session.bound) {
          if (ALLOW_DEMO_FALLBACK) this.applyDemoFallback()
          return
        }
        const vehicles = await api.getVehicles()
        if (!vehicles?.length) {
          this.applyDemoFallback()
          return
        }
        const selectedId = api.getSelectedVehicleId() || vehicles?.[0]?.id || ''
        this.vehicleId = selectedId ? String(selectedId) : ''
        const selectedVehicle = (vehicles || []).find((item) => String(item.id) === String(this.vehicleId))
        this.currentVehicleLabel = selectedVehicle
          ? [selectedVehicle.license_plate, selectedVehicle.make, selectedVehicle.model].filter(Boolean).join(' · ')
          : '未选择车辆'
        this.currentVehicleModelLabel = selectedVehicle?.model || selectedVehicle?.make || ''
        const resp = await api.getShopProducts({
          vehicle_id: this.vehicleId || api.getSelectedVehicleId() || '',
          kind: this.kind,
          query: this.query,
        })
        this.products = (resp?.items || []).map(withProductView)
        this.focusTags = this.buildFocusTags(this.products)
        if (!this.products.length) {
          this.applyDemoFallback()
        }
      } catch (error) {
        this.error = error?.message || '商城加载失败'
        if (ALLOW_DEMO_FALLBACK) this.applyDemoFallback()
      } finally {
        this.loading = false
      }
    },
    applyDemoFallback() {
      if (!ALLOW_DEMO_FALLBACK) return
      this.useDemoMode = true
      this.error = ''
      this.vehicleId = String(DEMO_ACCOUNT.selectedVehicleId)
      this.currentVehicleLabel = DEMO_ACCOUNT.cockpit.vehicle.vehicle_line
      this.currentVehicleModelLabel = DEMO_ACCOUNT.cockpit.vehicle.model || DEMO_ACCOUNT.cockpit.vehicle.make || ''
      this.products = DEMO_ACCOUNT.products
      this.focusTags = this.buildFocusTags(this.products)
    },
    chooseKind(kind) {
      this.kind = kind
      this.bootstrap()
    },
    createConsultation() {
      const vehicleId = this.vehicleId || api.getSelectedVehicleId() || null
      saveJourney({
        id: 'shop_consult',
        title: '商城选购咨询',
        desc: '根据当前车辆和筛选条件，向门店确认适配服务。',
        source: 'shop',
        appointmentSubject: this.query ? `商品咨询：${this.query}` : '商品选购咨询',
        serviceKind: this.kind || 'package',
        notes: this.query ? `商城搜索词：${this.query}` : '来自商城筛选页。',
        shopKind: this.kind,
        shopQuery: this.query,
        vehicleId,
      })
      const query = []
      if (vehicleId) query.push(`vehicle_id=${encodeURIComponent(vehicleId)}`)
      query.push(`subject=${encodeURIComponent(this.query ? `商品咨询：${this.query}` : '商品选购咨询')}`)
      query.push(`service_kind=${encodeURIComponent(this.kind || 'package')}`)
      if (this.query) query.push(`notes=${encodeURIComponent(`商城搜索词：${this.query}`)}`)
      uni.navigateTo({ url: `/pages/appointment/index?${query.join('&')}` })
    },
    openDetail(item) {
      const query = [`product_id=${encodeURIComponent(item.id)}`, `product_type=${encodeURIComponent(item.product_type || '')}`]
      const vehicleId = this.vehicleId || api.getSelectedVehicleId()
      if (vehicleId) {
        query.push(`vehicle_id=${encodeURIComponent(vehicleId)}`)
      }
      uni.navigateTo({ url: `/pages/shop/detail?${query.join('&')}` })
    },
  },
}
</script>

<style lang="scss">
@import '../../styles/mp-customer.scss';
</style>
