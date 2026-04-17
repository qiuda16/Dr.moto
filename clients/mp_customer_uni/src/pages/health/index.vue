<template>
  <view class="page">
    <view class="card">
      <view class="section-title">体检记录</view>
      <view class="subtext">按时间查看车辆健康变化。</view>
    </view>

    <view v-if="loading" class="card subtext">正在加载体检记录...</view>

    <view v-else-if="errorMessage" class="card">
      <view class="section-title">加载失败</view>
      <view class="subtext">{{ errorMessage }}</view>
      <button class="btn-primary" style="margin-top: 16rpx;" @click="loadRows">重试</button>
    </view>

    <view v-else-if="rows.length === 0" class="card subtext">暂无体检记录</view>

    <view v-for="item in rows" :key="item.id" class="card">
      <view class="row"><text>检测时间</text><text>{{ fmtDateTime(item.measured_at) }}</text></view>
      <view class="row" style="margin-top: 12rpx;"><text>里程</text><text>{{ item.odometer_km || '--' }} km</text></view>
      <view class="row" style="margin-top: 12rpx;"><text>电瓶</text><text>{{ item.battery_voltage || '--' }} V</text></view>
      <view class="row" style="margin-top: 12rpx;"><text>胎压</text><text>前 {{ item.tire_front_psi || '--' }} / 后 {{ item.tire_rear_psi || '--' }}</text></view>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { onPullDownRefresh, onShow } from '@dcloudio/uni-app'
import { api } from '../../utils/api'
import { ensureLogin, getActiveVehicleId } from '../../utils/session'
import { fmtDateTime } from '../../utils/text'

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
    rows.value = await api.fetchHealthRecords(vehicleId, 30)
  } catch (err) {
    errorMessage.value = err?.message || '暂时无法加载体检记录'
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
