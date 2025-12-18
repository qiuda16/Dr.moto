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
        <van-field 
          v-model="partSearch" 
          placeholder="Search part (e.g. Oil)" 
          @update:model-value="onSearchPart"
        />
        <div class="part-results">
          <div v-if="loadingParts" class="loading-parts">Loading...</div>
          <div 
            v-else
            class="part-item" 
            v-for="part in partResults" 
            :key="part.id"
            @click="addPart(part)"
          >
            <span class="part-name">{{ part.name }}</span>
            <span class="part-price">${{ part.list_price }}</span>
          </div>
          <div v-if="!loadingParts && partResults.length === 0 && partSearch" class="no-results">
            No parts found
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
import { showToast, showSuccessToast, showLoadingToast } from 'vant'
import DiagnosisPanel from '../components/DiagnosisPanel.vue'

const route = useRoute()
const order = ref(null)
const showParts = ref(false)
const partSearch = ref('')
const partResults = ref([])
const loadingParts = ref(false)
let searchTimer = null

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

const onSearchPart = async (val) => {
  if (!val) {
    partResults.value = []
    return
  }
  
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(async () => {
    loadingParts.value = true
    try {
      const res = await request.get(`/mp/inventory/products`, { params: { query: val } })
      partResults.value = res
    } catch (e) {
      console.error(e)
    } finally {
      loadingParts.value = false
    }
  }, 500)
}

const addPart = async (part) => {
  showLoadingToast('Adding...')
  try {
    await request.post('/mp/inventory/issue', {
      work_order_id: order.value.id,
      product_id: part.id,
      quantity: 1
    })
    showSuccessToast(`Added ${part.name}`)
    showParts.value = false
    partSearch.value = ''
    partResults.value = []
    loadOrder() // Refresh lines
  } catch (err) {
    showToast('Failed to add part')
  }
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

.sheet-content { padding: 10px 20px 40px; height: 300px; display: flex; flex-direction: column; }
.part-results { flex: 1; overflow-y: auto; margin-top: 10px; }
.part-item { display: flex; justify-content: space-between; padding: 15px 0; border-bottom: 1px solid #eee; cursor: pointer; }
.part-name { font-weight: 500; }
.loading-parts, .no-results { text-align: center; color: #999; padding: 20px; }
</style>
