<template>
  <view class="page">
    <view class="card">
      <view class="section-title">推荐保养</view>
      <view class="subtext">优先级清晰，便于快速决策。</view>
    </view>

    <view v-if="loading" class="card subtext">正在加载推荐项目...</view>

    <view v-else-if="errorMessage" class="card">
      <view class="section-title">加载失败</view>
      <view class="subtext">{{ errorMessage }}</view>
      <button class="btn-primary" style="margin-top: 16rpx;" @click="loadRows">重试</button>
    </view>

    <view v-else-if="rows.length === 0" class="card subtext">当前没有推荐项目</view>

    <view v-for="item in rows" :key="item.id || item.template_item_id || item.service_code" class="card">
      <view class="row">
        <text>{{ item.service_name || item.part_name || '推荐项目' }}</text>
        <text class="badge">{{ levelText(item.level) }}</text>
      </view>
      <view class="subtext" style="margin-top: 12rpx;">{{ item.reason || item.repair_method || '系统将根据里程和体检记录动态推荐。' }}</view>
      <view class="row" style="margin-top: 12rpx;"><text>参考价格</text><text>{{ fmtAmount(item.suggested_price) }}</text></view>
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
