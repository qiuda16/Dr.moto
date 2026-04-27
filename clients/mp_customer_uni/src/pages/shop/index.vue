<template>
  <view class="page-shell">
    <view class="page-body">
      <view v-if="error" class="error-state">{{ error }}</view>

      <view class="hero-card">
        <view class="hero-title">商城</view>
        <view class="hero-subtitle">按车辆适配结果筛选商品，也可以让 AI 先帮你缩小范围。</view>
      </view>

      <view class="light-card">
        <view class="section-title">筛选</view>
        <view class="choice-row">
          <view
            v-for="item in categories"
            :key="item.value"
            class="choice-pill"
            :class="{ 'choice-pill--active': item.value === kind }"
            @click="chooseKind(item.value)"
          >
            {{ item.label }}
          </view>
        </view>
        <input v-model="query" class="field-input" placeholder="搜索商品、品牌或服务" />
        <view class="btn-row">
          <button class="btn-primary" @click="bootstrap">搜索</button>
          <button class="btn-secondary" @click="consultAI">让 AI 帮选</button>
        </view>
      </view>

      <view class="light-card">
        <view class="section-title">商品列表</view>
        <view v-if="products.length">
          <view v-for="item in products" :key="item.id" class="product-card" @click="openDetail(item)">
            <view class="item-title">{{ item.name }}</view>
            <view class="item-desc">{{ item.description || item.product_type_label }}</view>
            <view class="tag-row" style="margin-top: 10rpx">
              <view class="choice-pill">{{ item.product_type_label }}</view>
              <view class="choice-pill">{{ item.price_text }}</view>
            </view>
          </view>
        </view>
        <view v-else class="empty-state">当前筛选条件下还没有商品。</view>
      </view>
    </view>
  </view>
</template>

<script>
import { api } from '../../utils/api'
import { formatMoney, productTypeLabel } from '../../utils/format'
import { getBindTicket } from '../../utils/session'
import { getJourney, saveJourney } from '../../utils/journey'

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
      vehicleId: '',
      kind: '',
      query: '',
      products: [],
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
        const resp = await api.getShopProducts({
          vehicle_id: this.vehicleId || api.getSelectedVehicleId() || '',
          kind: this.kind,
          query: this.query,
        })
        this.products = (resp?.items || []).map(withProductView)
      } catch (error) {
        this.error = error?.message || '商城加载失败'
      } finally {
        this.loading = false
      }
    },
    chooseKind(kind) {
      this.kind = kind
      this.bootstrap()
    },
    consultAI() {
      const activeJourney = getJourney() || {}
      saveJourney({
        ...activeJourney,
        id: activeJourney.id || 'shop_consult',
        title: activeJourney.title || '先确认选购建议',
        desc: '结合当前车辆和筛选结果，让 AI 帮你缩小选择范围。',
        source: 'shop',
        aiPrompt: this.query
          ? `请结合当前车辆和搜索词“${this.query}”，帮我挑选更合适的商品。`
          : '请结合当前车辆和商城筛选结果，帮我推荐优先查看的商品。',
        shopKind: this.kind,
        shopQuery: this.query,
        vehicleId: this.vehicleId || api.getSelectedVehicleId() || null,
      })
      uni.switchTab({ url: '/pages/ai/index' })
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
