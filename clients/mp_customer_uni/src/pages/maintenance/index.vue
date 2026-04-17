<template>
  <view class="page">
    <view class="card">
      <view class="section-title">保养工单</view>
      <view class="subtext">每次保养透明可追溯。</view>
    </view>

    <view v-if="loading" class="card subtext">正在加载保养记录...</view>

    <view v-else-if="errorMessage" class="card">
      <view class="section-title">加载失败</view>
      <view class="subtext">{{ errorMessage }}</view>
      <button class="btn-primary" style="margin-top: 16rpx;" @click="loadRows">重试</button>
    </view>

    <view v-else-if="rows.length === 0" class="card subtext">暂无保养工单</view>

    <view v-for="item in rows" :key="item.id || item.order_id" class="card">
      <view class="row">
        <text>{{ item.name || item.order_no || '工单' }}</text>
        <text class="badge">{{ orderStatusText(item.state || item.status) }}</text>
      </view>
      <view class="row" style="margin-top: 12rpx;"><text>金额</text><text>{{ fmtAmount(item.amount_total) }}</text></view>
      <view class="row" style="margin-top: 12rpx;"><text>日期</text><text>{{ fmtDate(item.date_planned || item.create_date) }}</text></view>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { onPullDownRefresh, onShow } from '@dcloudio/uni-app'
import { api } from '../../utils/api'
import { ensureLogin, getActiveVehicleId } from '../../utils/session'
import { fmtAmount, fmtDate, orderStatusText } from '../../utils/text'

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
    const data = await api.fetchMaintenanceOrders(vehicleId, 1, 20)
    rows.value = data.items || data || []
  } catch (err) {
    errorMessage.value = err?.message || '暂时无法加载保养记录'
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
