<template>
  <div class="page-container workbench">
    <van-nav-bar
      title="Workbench"
      left-arrow
      @click-left="$router.back()"
      fixed placeholder
    />

    <div v-if="order" class="content">
      <!-- Info Header -->
      <div class="card info-card">
        <h2>{{ order.data.vehicle_plate }}</h2>
        <p>{{ order.data.description }}</p>
        <van-steps :active="activeStep" active-color="#ff9f0a">
          <van-step>Check</van-step>
          <van-step>Quote</van-step>
          <van-step>Fix</van-step>
          <van-step>Done</van-step>
        </van-steps>
      </div>

      <!-- Action Area -->
      <div class="actions-grid">
        <div class="action-btn" @click="showChecklist=true">
          <van-icon name="todo-list-o" />
          <span>Inspect</span>
        </div>
        <div class="action-btn" @click="showParts=true">
          <van-icon name="cart-o" />
          <span>Parts</span>
        </div>
        <div class="action-btn" @click="showCamera=true">
          <van-icon name="photograph" />
          <span>Photo</span>
        </div>
      </div>

      <!-- Parts List (Quote Preview) -->
      <div class="card" v-if="order.data.odoo.lines?.length">
        <div class="section-title">Parts & Labor</div>
        <van-cell 
          v-for="line in order.data.odoo.lines" 
          :key="line.id"
          :title="line.product_id[1]"
          :value="`x${line.quantity}`"
        />
        <div class="total-bar">Total: ${{ order.data.odoo.amount_total }}</div>
      </div>

      <!-- Status Controller -->
      <div class="status-controller card">
        <div class="section-title">Status Action</div>
        <van-button v-if="order.status === 'confirmed'" block type="warning" @click="setStatus('diagnosing')">
          Start Diagnosis
        </van-button>
        <van-button v-if="order.status === 'diagnosing'" block type="primary" @click="setStatus('quoted')">
          Submit Quote
        </van-button>
        <van-button v-if="order.status === 'in_progress'" block type="success" @click="setStatus('ready')">
          Finish Work
        </van-button>
        <p v-if="order.status === 'quoted'" class="waiting-text">Waiting for customer approval...</p>
      </div>
    </div>

    <!-- Parts Selector Sheet -->
    <van-action-sheet v-model:show="showParts" title="Add Part / Labor">
      <div class="sheet-content">
        <van-field v-model="partSearch" placeholder="Search part (e.g. Oil)" />
        <div class="part-results">
          <!-- Mock Results -->
          <div class="part-item" @click="addPart('Motul 7100', 80)">
            <span>Motul 7100 4L</span>
            <span>$80</span>
          </div>
          <div class="part-item" @click="addPart('Labor Hour', 100)">
            <span>Labor (1h)</span>
            <span>$100</span>
          </div>
        </div>
      </div>
    </van-action-sheet>

  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import request from '../utils/request'
import { showToast, showSuccessToast } from 'vant'

const route = useRoute()
const order = ref(null)
const showParts = ref(false)
const partSearch = ref('')

onMounted(() => loadOrder())

const loadOrder = async () => {
  const res = await request.get(`/mp/workorders/${route.params.id}`)
  order.value = res
}

const activeStep = computed(() => {
  if (!order.value) return 0
  const s = order.value.status
  if (['draft', 'confirmed', 'diagnosing'].includes(s)) return 0
  if (s === 'quoted') return 1
  if (s === 'in_progress') return 2
  if (['ready', 'done'].includes(s)) return 3
  return 0
})

const setStatus = async (status) => {
  await request.post(`/mp/workorders/${order.value.id}/status?status=${status}`)
  showSuccessToast('Status Updated')
  loadOrder()
}

const addPart = async (name, price) => {
  // In real app: POST /mp/workorders/{id}/lines
  // Here we just mock it visually or call a hypothetical endpoint
  showToast(`Added ${name}`)
  showParts.value = false
}
</script>

<style scoped>
.info-card h2 { margin: 0; }
.actions-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; padding: 0 12px; }
.action-btn { 
  background: white; padding: 20px; border-radius: 12px; text-align: center;
  display: flex; flex-direction: column; align-items: center; gap: 8px;
  font-size: 14px; font-weight: 600; color: #333;
  box-shadow: 0 2px 5px rgba(0,0,0,0.05);
}
.action-btn .van-icon { font-size: 24px; color: #ff9f0a; }

.total-bar { text-align: right; font-weight: bold; font-size: 18px; padding-top: 10px; border-top: 1px solid #eee; }
.waiting-text { text-align: center; color: #999; font-style: italic; }

.sheet-content { padding: 10px 20px 40px; }
.part-item { display: flex; justify-content: space-between; padding: 15px 0; border-bottom: 1px solid #eee; }
</style>
