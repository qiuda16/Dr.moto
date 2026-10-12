<template>
  <view class="page-shell">
    <view class="page-body">
      <view class="hero-card">
        <view class="hero-kicker">推荐保养 · 优先级清晰</view>
        <view class="hero-title">推荐保养</view>
        <view class="hero-subtitle">按当前里程和体检记录做建议，不需要一次看太多。</view>
        <view class="summary-band">
          <view class="summary-band__item">
            <view class="summary-band__value">{{ rows.length }}</view>
            <view class="summary-band__label">推荐数量</view>
          </view>
          <view class="summary-band__item">
            <view class="summary-band__value">{{ loading ? '加载中' : '已就绪' }}</view>
            <view class="summary-band__label">当前状态</view>
          </view>
          <view class="summary-band__item">
            <view class="summary-band__value">优先确认</view>
            <view class="summary-band__label">处理建议</view>
          </view>
        </view>
      </view>

      <view v-if="loading" class="error-state">正在加载推荐项目...</view>

      <view v-else-if="errorMessage" class="error-state">
        <view class="section-title">加载失败</view>
        <view class="subtext">{{ errorMessage }}</view>
        <button class="btn-primary" style="margin-top: 16rpx;" @click="loadRows">重试</button>
      </view>

      <view v-else-if="rows.length === 0" class="light-card">
        <view class="section-title">暂无推荐项目</view>
        <view class="muted">当前车辆暂时没有需要优先处理的项目。</view>
      </view>

      <view v-else class="card-stack">
        <view v-for="item in rows" :key="item.id || item.template_item_id || item.service_code" class="light-card">
          <view class="section-head">
            <view class="section-title">{{ item.service_name || item.part_name || '推荐项目' }}</view>
            <view class="badge">{{ levelText(item.level) }}</view>
          </view>
          <view class="subtext">{{ item.reason || item.repair_method || '系统将根据里程和体检记录动态推荐。' }}</view>
          <view class="row" style="margin-top: 12rpx;"><text>参考价格</text><text>{{ fmtAmount(item.suggested_price) }}</text></view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { onPullDownRefresh, onShow } from '@dcloudio/uni-app'
import { api } from '../../utils/api'
import { ensureLogin, getActiveVehicleId } from '../../utils/session'
import { fmtAmount, levelText } from '../../utils/text'

const rows = ref([])
const loading = ref(false)
const errorMessage = ref('')

async function loadRows() {
  if (!ensureLogin()) return
  const vehicleId = getActiveVehicleId()
  if (!vehicleId) {
    rows.value = []
    errorMessage.value = '请先在首页选择车辆'
    return
  }

  loading.value = true
  errorMessage.value = ''
  try {
    rows.value = await api.fetchRecommendations(vehicleId)
  } catch (err) {
    errorMessage.value = err?.message || '暂时无法加载推荐项目'
  } finally {
    loading.value = false
  }
}

onShow(() => {
  loadRows()
})

onPullDownRefresh(async () => {
  await loadRows()
  uni.stopPullDownRefresh()
})
</script>
