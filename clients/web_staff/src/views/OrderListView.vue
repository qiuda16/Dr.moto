<template>
  <div class="order-list">
    <div class="card">
      <div class="toolbar" style="margin-bottom: 20px; display: flex; justify-content: space-between;">
        <el-input v-model="search" placeholder="Search Plate or Name" style="width: 300px;" prefix-icon="Search" />
        <el-button type="primary" @click="refresh">Refresh</el-button>
      </div>

      <el-table :data="orders" v-loading="loading" style="width: 100%">
        <el-table-column prop="name" label="Order ID" width="150" />
        <el-table-column prop="vehicle_plate" label="Vehicle" width="150" />
        <el-table-column prop="state" label="Status" width="150">
          <template #default="scope">
            <el-tag :type="getStatusType(scope.row.state)">{{ scope.row.state }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="amount_total" label="Total">
           <template #default="scope">${{ scope.row.amount_total }}</template>
        </el-table-column>
        <el-table-column label="Actions">
          <template #default="scope">
            <el-button size="small" @click="viewDetail(scope.row)">View</el-button>
            <el-button size="small" type="danger" plain>Cancel</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import request from '../utils/request'

const search = ref('')
const orders = ref([])
const loading = ref(false)

onMounted(() => refresh())

const refresh = async () => {
  loading.value = true
  try {
    // For now, reuse active list, later use a proper search API with pagination
    const res = await request.get('/mp/workorders/active/list')
    orders.value = res
  } finally {
    loading.value = false
  }
}

const getStatusType = (state) => {
  const map = { draft: 'info', confirmed: 'warning', in_progress: 'primary', done: 'success', quoted: 'warning' }
  return map[state] || ''
}

const viewDetail = (row) => {
  // Implement drawer or dialog
}
</script>
