<template>
  <div class="page-container">
    <van-nav-bar title="首页" />
    <p class="page-subtitle">先看今天最该做什么，再看历史和细节。</p>

    <VehicleSwitcher />

    <div class="card hero-card">
      <div class="hero-head">
        <div>
          <div class="soft-chip">{{ activeVehicle?.license_plate || '未绑定车辆' }}</div>
          <h2>{{ activeVehicle?.model || '车型信息待完善' }}</h2>
          <p class="hero-meta">当前里程 {{ valueOrDash(homeSummary.latest_odometer_km, ' km') }}</p>
        </div>
        <van-button size="small" plain @click="goTo('/app/maintenance')">保养记录</van-button>
      </div>
      <div class="hero-foot">
        <div class="todo-count">
          <span>待处理建议</span>
          <strong>{{ homeSummary.pending_recommendations ?? 0 }}</strong>
        </div>
        <div class="order-status">最近工单：{{ orderStatusText(homeSummary.latest_order_status) }}</div>
      </div>
    </div>

    <h3 class="section-title">你现在该做什么</h3>
    <div class="card">
      <div v-if="loading" class="empty-tip">正在加载建议...</div>
      <div v-else-if="!topRecommendations.length" class="empty-tip">当前暂无紧急建议，继续保持良好用车习惯</div>
      <div v-else>
        <div v-for="item in topRecommendations" :key="item.id" class="list-item">
          <div class="row">
            <div class="list-title">{{ item.title }}</div>
            <span class="soft-chip" :class="recommendationLevelClass(item.level)">{{ recommendationLevelText(item.level) }}</span>
          </div>
          <div class="list-meta">{{ item.reason }}</div>
          <div class="list-meta" v-if="item.priceText !== '--'">预计费用：{{ item.priceText }}</div>
        </div>
      </div>
      <van-button type="primary" block @click="goTo('/app/recommendations')">查看完整推荐清单</van-button>
    </div>

    <h3 class="section-title">关键概览</h3>
    <div class="kpi-grid">
      <div class="kpi-item">
        <div class="kpi-label">体检记录</div>
        <div class="kpi-value">{{ homeSummary.health_records_count ?? 0 }}</div>
      </div>
      <div class="kpi-item">
        <div class="kpi-label">最近消费</div>
        <div class="kpi-value kpi-small">{{ formatAmount(homeSummary.latest_order_amount) }}</div>
      </div>
      <div class="kpi-item">
        <div class="kpi-label">下次保养里程</div>
        <div class="kpi-value kpi-small">{{ valueOrDash(homeSummary.next_service_km, ' km') }}</div>
      </div>
      <div class="kpi-item">
        <div class="kpi-label">下次建议日期</div>
        <div class="kpi-value kpi-small">{{ formatDate(homeSummary.next_service_date) }}</div>
      </div>
    </div>

    <h3 class="section-title">快捷入口</h3>
    <div class="card quick-grid">
      <button class="quick-btn" @click="goTo('/app/health')">体检记录</button>
      <button class="quick-btn" @click="goTo('/app/maintenance')">保养工单</button>
      <button class="quick-btn" @click="goTo('/app/recommendations')">推荐保养</button>
      <button class="quick-btn" @click="goTo('/app/knowledge')">养护科普</button>
    </div>

    <CustomerSupportBar />
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { fetchHome, fetchRecommendations, fetchVehicles } from '../api'
import CustomerSupportBar from '../components/CustomerSupportBar.vue'
import VehicleSwitcher from '../components/VehicleSwitcher.vue'
import { useVehicleStore } from '../stores/vehicle'
import {
  formatAmount,
  formatDate,
  orderStatusText,
  recommendationLevelClass,
  recommendationLevelText,
  valueOrDash,
} from '../utils/customerText'

const router = useRouter()
const vehicleStore = useVehicleStore()
const activeVehicle = computed(() => vehicleStore.activeVehicle)
const loading = ref(false)
const recommendations = ref([])

const homeSummary = reactive({
  latest_odometer_km: null,
  health_records_count: 0,
  pending_recommendations: 0,
  latest_order_status: '',
  latest_order_amount: null,
  next_service_km: null,
  next_service_date: null,
})

const topRecommendations = computed(() => {
  const levelWeight = { must: 0, suggest: 1, optional: 2 }
  return recommendations.value
    .map((item, index) => ({
      id: item.id || item.template_item_id || item.service_code || `rec-${index}`,
      title: item.service_name || item.part_name || '建议检查项目',
      reason: item.reason || item.repair_method || '结合车辆里程和体检结果给出的建议',
      level: item.level || 'optional',
      priceText: formatAmount(item.suggested_price),
    }))
    .sort((a, b) => (levelWeight[a.level] ?? 9) - (levelWeight[b.level] ?? 9))
    .slice(0, 3)
})

function goTo(path) {
  router.push(path)
}

async function ensureVehicles() {
  if (vehicleStore.vehicles.length) return
  const vehicles = await fetchVehicles()
  vehicleStore.setVehicles(vehicles)
}

async function loadData(vehicleId) {
  if (!vehicleId) {
    recommendations.value = []
    return
  }

  loading.value = true
  try {
    const [homeData, recData] = await Promise.all([
      fetchHome(vehicleId),
      fetchRecommendations(vehicleId),
    ])
    Object.assign(homeSummary, homeData || {})
    recommendations.value = Array.isArray(recData) ? recData : []
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await ensureVehicles()
})

watch(
  () => vehicleStore.activeVehicleId,
  async (vehicleId) => {
    await loadData(vehicleId)
  },
  { immediate: true }
)
</script>

<style scoped>
.hero-card {
  position: relative;
  overflow: hidden;
  padding: 18px;
  background: linear-gradient(165deg, #ffffff 0%, #f6f8fc 45%, #eef2f8 100%);
}

.hero-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.hero-head h2 {
  margin: 10px 0 0;
  font-size: 25px;
  letter-spacing: -0.02em;
}

.hero-meta {
  margin: 8px 0 0;
  color: var(--text-muted);
  font-size: 13px;
}

.hero-foot {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid var(--line);
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.todo-count {
  display: flex;
  align-items: baseline;
  gap: 8px;
  color: var(--text-muted);
  font-size: 13px;
}

.todo-count strong {
  color: var(--text);
  font-size: 20px;
}

.order-status {
  color: var(--text-muted);
  font-size: 13px;
}

.kpi-small {
  font-size: 16px;
}

.row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.quick-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.quick-btn {
  background: #f8fafd;
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 12px 10px;
  text-align: left;
  font-size: 14px;
  color: var(--text);
  cursor: pointer;
}

.is-must {
  background: #ffe9e5;
  color: #bc2f1f;
}

.is-suggest {
  background: #fff5e8;
  color: #a75b12;
}

.is-optional {
  background: #eef2f7;
  color: #495769;
}
</style>
