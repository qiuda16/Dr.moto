<template>
  <div class="page-container">
    <van-nav-bar title="养护科普" />
    <p class="page-subtitle">用通俗内容解释保养件和维修决策。</p>

    <VehicleSwitcher />

    <div class="card">
      <div v-if="loading" class="empty-tip">正在加载科普资料...</div>
      <div v-else-if="!rows.length" class="empty-tip">暂无科普资料</div>
      <div v-else>
        <div v-for="item in rows" :key="item.id" class="list-item doc" @click="openDoc(item.file_url)">
          <div>
            <div class="list-title">{{ item.title || item.file_name || '资料' }}</div>
            <div class="list-meta">{{ item.category || '通用' }}</div>
          </div>
          <van-icon name="arrow" color="#7b8697" />
        </div>
      </div>
    </div>

    <CustomerSupportBar />
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import { showToast } from 'vant'
import { fetchKnowledgeDocs, fetchVehicles } from '../api'
import CustomerSupportBar from '../components/CustomerSupportBar.vue'
import VehicleSwitcher from '../components/VehicleSwitcher.vue'
import { useVehicleStore } from '../stores/vehicle'

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
    const data = await fetchKnowledgeDocs(vehicleId)
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

function openDoc(url) {
  if (!url) {
    showToast('资料地址未配置')
    return
  }
  window.open(url, '_blank')
}
</script>

<style scoped>
.doc {
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
}
</style>
