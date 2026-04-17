<template>
  <view class="page">
    <view class="card">
      <view class="section-title">养护科普</view>
      <view class="subtext">看得懂、用得上的养护知识。</view>
    </view>

    <view v-if="loading" class="card subtext">正在加载科普资料...</view>

    <view v-else-if="errorMessage" class="card">
      <view class="section-title">加载失败</view>
      <view class="subtext">{{ errorMessage }}</view>
      <button class="btn-primary" style="margin-top: 16rpx;" @click="loadRows">重试</button>
    </view>

    <view v-else-if="rows.length === 0" class="card subtext">暂无科普资料</view>

    <view v-for="item in rows" :key="item.id" class="card" @click="openDoc(item.file_url)">
      <view class="row"><text>{{ item.title || item.file_name || '资料' }}</text><text>查看</text></view>
      <view class="subtext" style="margin-top: 12rpx;">{{ item.category || '通用' }}</view>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { onPullDownRefresh, onShow } from '@dcloudio/uni-app'
import { api } from '../../utils/api'
import { ensureLogin, getActiveVehicleId } from '../../utils/session'

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
    rows.value = await api.fetchKnowledgeDocs(vehicleId)
  } catch (err) {
    errorMessage.value = err?.message || '暂时无法加载科普资料'
  } finally {
    loading.value = false
  }
}

function openDoc(url) {
  if (!url) {
    uni.showToast({ title: '资料地址未配置', icon: 'none' })
    return
  }
  uni.setClipboardData({
    data: url,
    success: () => uni.showToast({ title: '链接已复制，请在浏览器打开', icon: 'none' }),
  })
}

onShow(() => {
  loadRows()
})

onPullDownRefresh(async () => {
  await loadRows()
  uni.stopPullDownRefresh()
})
</script>
