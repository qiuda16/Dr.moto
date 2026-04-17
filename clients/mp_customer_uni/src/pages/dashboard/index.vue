<template>
  <view class="page">
    <view class="card">
      <view class="section-title">我的车辆</view>
      <picker mode="selector" :range="vehicleOptions" range-key="label" @change="onVehicleChange">
        <view class="input">{{ activeVehicleLabel }}</view>
      </picker>
      <view class="subtext">先看最重要的信息，再做保养决策。</view>
    </view>

    <view v-if="loading" class="card subtext">正在加载车辆信息...</view>

    <view v-else-if="errorMessage" class="card">
      <view class="section-title">加载失败</view>
      <view class="subtext">{{ errorMessage }}</view>
      <button class="btn-primary" style="margin-top: 16rpx;" @click="loadData">重试</button>
    </view>

    <view v-else-if="!vehicles.length" class="card">
      <view class="section-title">暂无车辆</view>
      <view class="subtext">请先在门店绑定车辆信息后再查看。</view>
    </view>

    <template v-else>
      <view class="card">
        <view class="row">
          <text>当前里程</text>
          <text>{{ home.latest_odometer_km || '--' }} km</text>
        </view>
        <view class="row" style="margin-top: 16rpx;">
          <text>体检记录</text>
          <text>{{ home.health_records_count || 0 }}</text>
        </view>
        <view class="row" style="margin-top: 16rpx;">
          <text>待处理建议</text>
          <text>{{ home.pending_recommendations || 0 }}</text>
        </view>
        <view class="row" style="margin-top: 16rpx;">
          <text>最近工单</text>
          <text>{{ orderStatusText(home.latest_order_status) }}</text>
        </view>
      </view>

      <view class="card">
        <view class="section-title">快捷入口</view>
        <button size="mini" style="margin-right: 12rpx;" @click="toTab('/pages/health/index')">体检</button>
        <button size="mini" style="margin-right: 12rpx;" @click="toTab('/pages/maintenance/index')">保养</button>
        <button size="mini" style="margin-right: 12rpx;" @click="toPage('/subpages/recommendations/index')">推荐</button>
        <button size="mini" @click="toPage('/subpages/knowledge/index')">科普</button>
      </view>
    </template>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onPullDownRefresh, onShow } from '@dcloudio/uni-app'
import { api } from '../../utils/api'
import { ensureLogin, getActiveVehicleId, setActiveVehicleId } from '../../utils/session'
import { orderStatusText } from '../../utils/text'

const vehicles = ref([])
const selectedVehicleId = ref('')
const home = ref({})
const loading = ref(false)
const errorMessage = ref('')

const vehicleOptions = computed(() =>
  vehicles.value.map((v) => ({
    label: `${v.license_plate || '未命名车辆'}${v.model ? ` · ${v.model}` : ''}`,
    id: String(v.id),
  }))
)

const activeVehicleLabel = computed(() => {
  const target = vehicleOptions.value.find((v) => v.id === String(selectedVehicleId.value))
  return target?.label || '请选择车辆'
})

function toMessage(err) {
  if (!err) return '暂时无法获取数据，请稍后再试'
  return err?.message || '暂时无法获取数据，请稍后再试'
}

async function loadData() {
  if (!ensureLogin()) return
  loading.value = true
  errorMessage.value = ''
  try {
    vehicles.value = await api.fetchVehicles()
    if (!vehicles.value.length) {
      home.value = {}
      return
    }

    const cachedId = getActiveVehicleId()
    const found = vehicles.value.find((v) => String(v.id) === String(cachedId))
    selectedVehicleId.value = found ? String(found.id) : String(vehicles.value[0].id)
    setActiveVehicleId(selectedVehicleId.value)

    home.value = await api.fetchHome(selectedVehicleId.value)
  } catch (err) {
    errorMessage.value = toMessage(err)
  } finally {
    loading.value = false
  }
}

async function onVehicleChange(e) {
  const idx = Number(e.detail.value)
  const selected = vehicleOptions.value[idx]
  if (!selected) return
  selectedVehicleId.value = selected.id
  setActiveVehicleId(selected.id)
  loading.value = true
  errorMessage.value = ''
  try {
    home.value = await api.fetchHome(selected.id)
  } catch (err) {
    errorMessage.value = toMessage(err)
  } finally {
    loading.value = false
  }
}

function toTab(url) {
  uni.switchTab({ url })
}

function toPage(url) {
  uni.navigateTo({ url })
}

onShow(() => {
  loadData()
})

onPullDownRefresh(async () => {
  await loadData()
  uni.stopPullDownRefresh()
})
</script>
