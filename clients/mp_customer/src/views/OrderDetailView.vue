<template>
  <div class="page-container">
    <van-nav-bar
      title="Order Details"
      left-arrow
      @click-left="$router.back()"
      class="nav-transparent"
    />

    <div v-if="loading" class="loading-state">
      <van-loading type="spinner" color="#fff" />
    </div>

    <div v-else-if="order" class="content">
      <div class="header-section">
        <h2 class="title">{{ order.data.odoo.name || 'Order' }}</h2>
        <div class="status-badge" :class="order.status">{{ order.status }}</div>
      </div>

      <div class="info-card">
        <div class="row">
          <label>Vehicle</label>
          <span>{{ order.data.vehicle_plate }}</span>
        </div>
        <div class="row">
          <label>Issue</label>
          <span>{{ order.data.description }}</span>
        </div>
      </div>

      <div class="timeline-section">
        <h3 class="section-header">Timeline</h3>
        <van-steps direction="vertical" :active="activeStep" active-color="#3e64ff" inactive-color="#333">
          <van-step>
            <h3>Received</h3>
            <p>We've got your request</p>
          </van-step>
          <van-step>
            <h3>Diagnosing</h3>
            <p>Tech is checking the bike</p>
          </van-step>
          <van-step>
            <h3>Quote Ready</h3>
            <p>Review estimate</p>
          </van-step>
          <van-step>
            <h3>Repairing</h3>
            <p>Fix in progress</p>
          </van-step>
          <van-step>
            <h3>Ready</h3>
            <p>Pick up your ride</p>
          </van-step>
        </van-steps>
      </div>

      <div class="quote-card" v-if="hasQuote">
        <h3 class="section-header">Estimate</h3>
        <div class="line-items">
          <div class="item" v-for="line in order.data.odoo.lines" :key="line.id">
            <span class="name">{{ line.product_id[1] }}</span>
            <span class="qty">x{{ line.quantity }}</span>
            <span class="price">${{ line.price_subtotal }}</span>
          </div>
          <div class="total-line">
            <span>Total</span>
            <span class="total-price">${{ order.data.odoo.amount_total }}</span>
          </div>
        </div>
      </div>

      <div class="action-dock" v-if="canAction">
        <div v-if="order.status === 'quoted'" class="dock-inner">
          <div class="summary">
            <span>Total to pay</span>
            <span class="big-price">${{ order.data.odoo.amount_total }}</span>
          </div>
          <van-button color="#3e64ff" round block @click="confirmQuote">Accept & Start</van-button>
        </div>
        
        <div v-if="order.status === 'ready'" class="dock-inner">
          <div class="summary">
            <span>Amount Due</span>
            <span class="big-price">${{ order.data.odoo.amount_total }}</span>
          </div>
          <van-button color="#30d158" round block @click="payNow">Pay Now</van-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import request from '../utils/request'
import { showSuccessToast, showConfirmDialog } from 'vant'

const route = useRoute()
const order = ref(null)
const loading = ref(true)

onMounted(() => loadOrder())

const loadOrder = async () => {
  loading.value = true
  try {
    const res = await request.get(`/mp/workorders/${route.params.id}`)
    order.value = res
  } catch (err) {
  } finally {
    loading.value = false
  }
}

const activeStep = computed(() => {
  if (!order.value) return 0
  const s = order.value.status
  const map = { draft: 0, confirmed: 1, diagnosing: 1, quoted: 2, in_progress: 3, ready: 4, done: 4 }
  return map[s] || 0
})

const hasQuote = computed(() => order.value?.data?.odoo?.lines?.length > 0)
const canAction = computed(() => ['quoted', 'ready'].includes(order.value?.status))

const confirmQuote = () => {
  showConfirmDialog({ title: 'Approve Estimate', message: 'Start repairs now?' })
    .then(async () => {
      await request.post(`/mp/workorders/${order.value.id}/status?status=in_progress`)
      showSuccessToast('Approved')
      loadOrder()
    })
}

const payNow = async () => {
  await request.post(`/mp/workorders/${order.value.id}/status?status=done`)
  showSuccessToast('Paid')
  loadOrder()
}
</script>

<style scoped>
.nav-transparent { background: transparent !important; }
.loading-state { display: flex; justify-content: center; padding-top: 100px; }
.content { padding: 20px; padding-bottom: 120px; }

.header-section { margin-bottom: 30px; }
.title { font-size: 28px; margin: 0 0 10px 0; }
.status-badge { 
  display: inline-block; padding: 6px 12px; border-radius: 20px; 
  font-size: 12px; font-weight: 600; text-transform: uppercase; background: #333;
}
.status-badge.quoted { background: #ff9f0a; color: black; }
.status-badge.ready { background: #30d158; color: black; }
.status-badge.in_progress { background: #3e64ff; }

.info-card { background: #1c1c1e; border-radius: 12px; padding: 20px; margin-bottom: 20px; }
.row { display: flex; justify-content: space-between; margin-bottom: 10px; }
.row:last-child { margin-bottom: 0; }
.row label { color: #8e8e93; }

.section-header { font-size: 14px; text-transform: uppercase; color: #8e8e93; margin: 20px 0 10px; }

.quote-card { background: #1c1c1e; padding: 20px; border-radius: 12px; }
.item { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #333; }
.name { flex: 1; }
.qty { color: #8e8e93; margin: 0 10px; }
.total-line { display: flex; justify-content: space-between; margin-top: 15px; font-weight: bold; font-size: 18px; }

.action-dock {
  position: fixed; bottom: 0; left: 0; right: 0;
  background: #1c1c1e; border-top: 1px solid #333;
  padding: 20px; padding-bottom: max(20px, env(safe-area-inset-bottom));
}
.dock-inner { display: flex; align-items: center; gap: 20px; }
.summary { flex: 1; }
.summary span { display: block; font-size: 12px; color: #8e8e93; }
.summary .big-price { font-size: 24px; font-weight: 600; color: white; }
</style>
