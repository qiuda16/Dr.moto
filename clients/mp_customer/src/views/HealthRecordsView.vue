<template>
  <div class="page-container">
    <van-nav-bar title="体检" />
    <p class="page-subtitle">检测数据清晰可读，变化趋势一目了然。</p>

    <VehicleSwitcher />

    <div class="card">
      <div v-if="loading" class="empty-tip">正在加载体检记录...</div>
      <div v-else-if="!rows.length" class="empty-tip">暂无体检记录</div>
      <div v-else>
        <div v-for="item in rows" :key="item.id" class="list-item">
          <div class="list-title">{{ formatDateTime(item.measured_at) }}</div>
          <div class="list-meta">里程：{{ valueOrDash(item.odometer_km, ' km') }}</div>
          <div class="list-meta">
            电瓶：{{ valueOrDash(item.battery_voltage, ' V') }} ｜ 胎压：
            前 {{ valueOrDash(item.tire_front_psi, ' psi') }} / 后 {{ valueOrDash(item.tire_rear_psi, ' psi') }}
          </div>
        </div>
      </div>
    </div>

    <CustomerSupportBar />
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import { fetchHealthRecords, fetchVehicles } from '../api'
import CustomerSupportBar from '../components/CustomerSupportBar.vue'
import VehicleSwitcher from '../components/VehicleSwitcher.vue'
import { useVehicleStore } from '../stores/vehicle'
import { formatDateTime, valueOrDash } from '../utils/customerText'

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
    rows.value = await fetchHealthRecords(vehicleId, 30)
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
