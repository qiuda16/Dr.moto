<template>
  <div class="page-container">
    <van-nav-bar title="保养" />
    <p class="page-subtitle">每一次保养透明留痕，随时可查。</p>

    <VehicleSwitcher />

    <div class="card">
      <div v-if="loading" class="empty-tip">正在加载保养记录...</div>
      <div v-else-if="!orders.length" class="empty-tip">暂无保养记录</div>
      <div v-else>
        <div v-for="item in orders" :key="item.id || item.order_id" class="list-item">
          <div class="row">
            <div class="list-title">{{ item.name || item.order_no || '工单' }}</div>
            <span class="soft-chip chip-neutral">{{ orderStatusText(item.state || item.status) }}</span>
          </div>
          <div class="list-meta">金额：{{ formatAmount(item.amount_total) }}</div>
          <div class="list-meta">日期：{{ formatDate(item.date_planned || item.create_date) }}</div>
        </div>
      </div>
    </div>

    <CustomerSupportBar />
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import { fetchMaintenanceOrders, fetchVehicles } from '../api'
import CustomerSupportBar from '../components/CustomerSupportBar.vue'
import VehicleSwitcher from '../components/VehicleSwitcher.vue'
import { useVehicleStore } from '../stores/vehicle'
import { formatAmount, formatDate, orderStatusText } from '../utils/customerText'

const vehicleStore = useVehicleStore()
const orders = ref([])
const loading = ref(false)

async function ensureVehicles() {
  if (vehicleStore.vehicles.length) return
  vehicleStore.setVehicles(await fetchVehicles())
}

async function loadOrders(vehicleId) {
  if (!vehicleId) {
    orders.value = []
    return
  }
  loading.value = true
  try {
    const data = await fetchMaintenanceOrders(vehicleId, 1, 20)
    orders.value = data.items || data || []
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
    await loadOrders(vehicleId)
  },
  { immediate: true }
)
</script>

<style scoped>
.row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.chip-neutral {
  background: #eef2f7;
  color: #495769;
}
</style>
