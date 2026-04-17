<template>
  <div class="page-container">
    <van-nav-bar title="推荐保养" />
    <p class="page-subtitle">建议清楚直给，便于快速决策。</p>

    <VehicleSwitcher />

    <div class="card">
      <div v-if="loading" class="empty-tip">正在加载推荐项目...</div>
      <div v-else-if="!rows.length" class="empty-tip">当前没有推荐项目</div>
      <div v-else>
        <div v-for="item in rows" :key="item.id || item.template_item_id || item.service_code" class="list-item">
          <div class="row">
            <div class="list-title">{{ item.service_name || item.part_name || '推荐项目' }}</div>
            <span class="soft-chip" :class="recommendationLevelClass(item.level)">{{ recommendationLevelText(item.level) }}</span>
          </div>
          <div class="list-meta">{{ item.reason || item.repair_method || '后续将按里程和体检结果补充推荐依据。' }}</div>
          <div class="list-meta">参考价格：{{ formatAmount(item.suggested_price) }}</div>
        </div>
      </div>
    </div>

    <CustomerSupportBar />
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import { fetchRecommendations, fetchVehicles } from '../api'
import CustomerSupportBar from '../components/CustomerSupportBar.vue'
import VehicleSwitcher from '../components/VehicleSwitcher.vue'
import { useVehicleStore } from '../stores/vehicle'
import {
  formatAmount,
  recommendationLevelClass,
  recommendationLevelText,
} from '../utils/customerText'

const vehicleStore = useVehicleStore()
const rows = ref([])
const loading = ref(false)

async function ensureVehicles() {
  if (vehicleStore.vehicles.length) return
  vehicleStore.setVehicles(await fetchVehicles())
}

async function loadRows(vehicleId) {
  if (!vehicleId) {
    rows.value = []
    return
  }
  loading.value = true
  try {
    const data = await fetchRecommendations(vehicleId)
    rows.value = Array.isArray(data) ? data : []
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
    await loadRows(vehicleId)
  },
  { immediate: true }
)
</script>

<style scoped>
.row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
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
