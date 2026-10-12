<template>
  <view class="page-shell">
    <view class="page-body">
      <view class="hero-card">
        <view class="hero-kicker">养护科普 · 看得懂，用得上</view>
        <view class="hero-title">养护科普</view>
        <view class="hero-subtitle">把门店常用的知识整理成好读的内容，方便随时翻看。</view>
        <view class="summary-band">
          <view class="summary-band__item">
            <view class="summary-band__value">{{ rows.length }}</view>
            <view class="summary-band__label">资料数量</view>
          </view>
          <view class="summary-band__item">
            <view class="summary-band__value">{{ loading ? '加载中' : '可浏览' }}</view>
            <view class="summary-band__label">当前状态</view>
          </view>
          <view class="summary-band__item">
            <view class="summary-band__value">长按复制</view>
            <view class="summary-band__label">打开方式</view>
          </view>
        </view>
      </view>

      <view v-if="loading" class="error-state">正在加载科普资料...</view>

      <view v-else-if="errorMessage" class="error-state">
        <view class="section-title">加载失败</view>
        <view class="subtext">{{ errorMessage }}</view>
        <button class="btn-primary" style="margin-top: 16rpx;" @click="loadRows">重试</button>
      </view>

      <view v-else-if="rows.length === 0" class="light-card">
        <view class="section-title">暂无科普资料</view>
        <view class="muted">门店还没有上传可查看的知识文件。</view>
      </view>

      <view v-else class="card-stack">
        <view v-for="item in rows" :key="item.id" class="light-card" @click="openDoc(item.file_url)">
          <view class="section-head">
            <view class="section-title">{{ item.title || item.file_name || '资料' }}</view>
            <view class="badge">查看</view>
          </view>
          <view class="subtext">{{ item.category || '通用' }}</view>
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
