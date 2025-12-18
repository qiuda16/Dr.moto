<template>
  <div class="display-board">
    <div class="header">
      <div class="store-name">Dr.Moto Service Center</div>
      <div class="time">{{ currentTime }}</div>
    </div>

    <div class="main-content">
      <div class="column ready">
        <div class="col-header">READY TO PICKUP</div>
        <div class="order-list">
          <div v-for="order in readyOrders" :key="order.id" class="order-card ready-card">
            <div class="plate">{{ maskPlate(order.vehicle_plate) }}</div>
            <div class="status">READY</div>
          </div>
        </div>
      </div>

      <div class="column working">
        <div class="col-header">IN PROGRESS</div>
        <div class="order-list">
          <div v-for="order in workingOrders" :key="order.id" class="order-card work-card">
            <div class="plate">{{ maskPlate(order.vehicle_plate) }}</div>
            <div class="meta">
              <span class="status-tag">{{ order.state.toUpperCase() }}</span>
              <span class="time-est">ETA: ~45m</span>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <div class="ticker">
      PLEASE HAVE YOUR PICKUP CODE READY • STORE CLOSES AT 8:00 PM • FOR EMERGENCY CALL 555-0199
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import axios from 'axios'

const orders = ref([])
const currentTime = ref('')

const readyOrders = computed(() => orders.value.filter(o => o.state === 'ready'))
const workingOrders = computed(() => orders.value.filter(o => ['diagnosing', 'in_progress', 'quoted'].includes(o.state)))

const maskPlate = (plate) => {
  if (!plate || plate.length < 4) return plate
  return plate.substring(0, 2) + '***' + plate.substring(plate.length - 2)
}

const updateTime = () => {
  const now = new Date()
  currentTime.value = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

const fetchOrders = async () => {
  try {
    // We reuse the active list endpoint from BFF
    // In prod, this should use a specific public/display endpoint
    const res = await axios.get('/api/mp/workorders/active/list')
    orders.value = res.data
  } catch (e) {
    console.error("Fetch failed", e)
  }
}

onMounted(() => {
  updateTime()
  setInterval(updateTime, 1000)
  fetchOrders()
  setInterval(fetchOrders, 30000) // Refresh every 30s
})
</script>

<style scoped>
.display-board {
  display: flex; flex-direction: column; height: 100vh;
  background: #000; color: white;
}
.header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 20px 40px; border-bottom: 2px solid #333;
}
.store-name { font-size: 32px; font-weight: bold; letter-spacing: 2px; }
.time { font-size: 32px; font-weight: 300; }

.main-content {
  flex: 1; display: flex; padding: 20px; gap: 20px;
}
.column {
  flex: 1; background: #111; border-radius: 16px; padding: 20px;
  display: flex; flex-direction: column;
}
.col-header {
  font-size: 24px; font-weight: 900; color: #888; margin-bottom: 20px; text-transform: uppercase;
}
.ready .col-header { color: #30d158; }
.working .col-header { color: #0a84ff; }

.order-list {
  flex: 1; display: flex; flex-direction: column; gap: 15px; overflow-y: auto;
}

.order-card {
  background: #222; padding: 20px; border-radius: 8px;
  display: flex; justify-content: space-between; align-items: center;
}
.ready-card { border-left: 8px solid #30d158; background: #1a3a2a; }
.work-card { border-left: 8px solid #0a84ff; }

.plate { font-size: 40px; font-weight: bold; font-family: monospace; letter-spacing: 2px; }
.status { font-size: 24px; font-weight: bold; color: #30d158; }
.meta { display: flex; flex-direction: column; text-align: right; }
.status-tag { font-size: 16px; color: #888; }
.time-est { font-size: 14px; color: #666; margin-top: 5px; }

.ticker {
  background: #111; padding: 10px; text-align: center;
  font-size: 18px; color: #666; letter-spacing: 1px;
  text-transform: uppercase;
}
</style>
