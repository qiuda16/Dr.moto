<template>
  <div class="page-container home-view">
    <!-- Header: Status Bar style -->
    <div class="header-status">
      <div class="user-info" v-if="currentUser">
        <span class="name">Hi, {{ currentUser.name.split(' ')[0] }}</span>
      </div>
      <div class="status-icons">
        <van-icon name="scan" class="icon-btn" @click="scanCode" />
        <van-icon name="bell" class="icon-btn" />
      </div>
    </div>

    <!-- Hero Vehicle Section (Tesla Style) -->
    <div class="vehicle-hero">
      <div class="vehicle-info">
        <h1 class="model-name">{{ mainVehicle ? mainVehicle.vehicle_id[1] : 'DrMoto' }}</h1>
        <div class="vehicle-status">
          <span v-if="activeOrder" class="status-tag warning">
            <van-icon name="info-o" /> Service in Progress
          </span>
          <span v-else class="status-tag">
            <van-icon name="location-o" /> Parked
          </span>
          <span class="range">82%</span>
        </div>
      </div>
      
      <div class="vehicle-visual">
        <img src="https://images.unsplash.com/photo-1568772585407-9361f9bf3a87?q=80&w=600&auto=format&fit=crop" class="vehicle-img" />
        <div class="shadow"></div>
      </div>
    </div>

    <!-- Quick Controls Grid -->
    <div class="controls-container">
      <div class="control-row">
        <div class="control-btn" @click="startBooking('repair')">
          <div class="icon-circle repair"><van-icon name="setting" /></div>
          <span>Repair</span>
        </div>
        <div class="control-btn" @click="startBooking('maintenance')">
          <div class="icon-circle maint"><van-icon name="gem" /></div>
          <span>Service</span>
        </div>
        <div class="control-btn" @click="startBooking('rescue')">
          <div class="icon-circle rescue"><van-icon name="phone" /></div>
          <span>Rescue</span>
        </div>
        <div class="control-btn" @click="$router.push('/ai-help')">
          <div class="icon-circle ai"><van-icon name="chat" /></div>
          <span>Ask AI</span>
        </div>
      </div>
    </div>

    <!-- Active Service Card (Floating) -->
    <div class="service-status-card" v-if="activeOrder" @click="$router.push('/orders')">
      <div class="progress-bar">
        <div class="fill" :style="{ width: getProgressWidth(activeOrder.state) }"></div>
      </div>
      <div class="status-content">
        <div class="left">
          <span class="label">Current Service</span>
          <span class="value">{{ activeOrder.name }}</span>
        </div>
        <div class="right">
          <span class="state-text">{{ activeOrder.state }}</span>
          <van-icon name="arrow" />
        </div>
      </div>
    </div>

    <!-- Info Lists -->
    <div class="info-section">
      <div class="menu-item" @click="$router.push('/orders')">
        <span>History</span>
        <van-icon name="arrow" />
      </div>
      <div class="menu-item" @click="$router.push('/profile')">
        <span>Account</span>
        <van-icon name="arrow" />
      </div>
    </div>

    <!-- Booking Popup (Dark Theme) -->
    <van-popup 
      v-model:show="showBooking" 
      position="bottom" 
      round 
      :style="{ height: '70%', background: '#1c1c1e' }"
    >
      <div class="popup-content">
        <div class="popup-header">Request Service</div>
        
        <van-form @submit="submitOrder">
          <van-field name="vehicle" label="Vehicle" class="dark-field">
            <template #input>
              <van-radio-group v-model="form.vehicle_plate" direction="horizontal">
                <van-radio :name="v.license_plate" v-for="v in vehicles" :key="v.id">{{ v.license_plate }}</van-radio>
              </van-radio-group>
            </template>
          </van-field>

          <van-field
            v-model="form.description"
            name="description"
            label="Issue"
            placeholder="What needs fixing?"
            type="textarea"
            rows="3"
            class="dark-field"
            :rules="[{ required: true, message: 'Required' }]"
          />
          
          <div class="upload-area">
             <van-uploader v-model="fileList" multiple :max-count="3" />
             <p>Add Photos / Videos</p>
          </div>

          <div class="submit-area">
            <van-button round block color="#3e64ff" native-type="submit">
              Schedule Service
            </van-button>
          </div>
        </van-form>
      </div>
    </van-popup>

  </div>
</template>

<script setup>
import { ref, onMounted, computed, reactive } from 'vue'
import request from '../utils/request'
import { showSuccessToast } from 'vant'

const currentUser = ref(null)
const vehicles = ref([])
const activeOrder = ref(null)
const showBooking = ref(false)
const form = reactive({ vehicle_plate: '', description: '' })
const fileList = ref([])

const mainVehicle = computed(() => vehicles.value[0])

onMounted(async () => {
  const stored = localStorage.getItem('drmoto_user')
  if (stored) {
    currentUser.value = JSON.parse(stored)
    await loadData()
  }
})

const loadData = async () => {
  try {
    const [vRes, oRes] = await Promise.all([
      request.get(`/mp/workorders/customers/${currentUser.value.id}/vehicles`),
      request.get(`/mp/workorders/customers/${currentUser.value.id}/orders`)
    ])
    vehicles.value = vRes
    activeOrder.value = oRes.find(o => !['done', 'cancel'].includes(o.state))
    if (vehicles.value.length > 0) form.vehicle_plate = vehicles.value[0].license_plate
  } catch (err) {
    console.error(err)
  }
}

const startBooking = (type) => {
  if (!currentUser.value) {
    showSuccessToast('Please login first')
    return router.push('/profile')
  }
  showBooking.value = true
}

const submitOrder = async () => {
  try {
    await request.post('/mp/workorders/', {
      customer_id: currentUser.value.id,
      vehicle_plate: form.vehicle_plate,
      description: form.description
    })
    showSuccessToast('Request Sent')
    showBooking.value = false
    loadData()
  } catch (err) {}
}

const getProgressWidth = (state) => {
  const map = { draft: '10%', confirmed: '30%', quoted: '50%', in_progress: '70%', ready: '90%' }
  return map[state] || '0%'
}
</script>

<style scoped>
.home-view { padding-top: 20px; background: black; }

.header-status {
  display: flex; justify-content: space-between; align-items: center;
  padding: 20px;
}
.name { font-size: 18px; font-weight: 600; color: #fff; }
.icon-btn { font-size: 24px; color: #fff; margin-left: 20px; background: rgba(255,255,255,0.1); padding: 8px; border-radius: 50%; }

.vehicle-hero {
  text-align: center; margin-bottom: 30px; position: relative;
}
.model-name { font-size: 32px; margin: 0; letter-spacing: 1px; }
.vehicle-status { margin-top: 10px; color: #8e8e93; font-size: 14px; display: flex; justify-content: center; gap: 15px; }
.status-tag { display: flex; align-items: center; gap: 5px; }
.status-tag.warning { color: #ffd60a; }

.vehicle-visual { margin-top: 30px; position: relative; height: 250px; display: flex; justify-content: center; }
.vehicle-img { height: 100%; object-fit: contain; z-index: 2; }
.shadow { 
  position: absolute; bottom: 10px; width: 60%; height: 20px; 
  background: radial-gradient(ellipse at center, rgba(255,255,255,0.2) 0%, transparent 70%); 
}

.controls-container { padding: 0 20px; margin-bottom: 30px; }
.control-row { display: flex; justify-content: space-around; }
.control-btn { display: flex; flex-direction: column; align-items: center; gap: 10px; cursor: pointer; }
.icon-circle {
  width: 56px; height: 56px; border-radius: 50%; background: #1c1c1e;
  display: flex; justify-content: center; align-items: center; font-size: 24px; color: #fff;
  transition: all 0.2s; border: 1px solid rgba(255,255,255,0.1);
}
.control-btn:active .icon-circle { transform: scale(0.95); background: #333; }
.control-btn span { font-size: 12px; color: #8e8e93; }

.service-status-card {
  margin: 0 20px 30px; background: #1c1c1e; border-radius: 12px; overflow: hidden;
  border: 1px solid rgba(255,255,255,0.1);
}
.progress-bar { height: 4px; background: #333; width: 100%; }
.fill { height: 100%; background: #3e64ff; transition: width 0.5s; }
.status-content { padding: 15px; display: flex; justify-content: space-between; align-items: center; }
.left { display: flex; flex-direction: column; }
.left .label { font-size: 12px; color: #8e8e93; }
.left .value { font-size: 16px; font-weight: 600; margin-top: 4px; }
.right { color: #8e8e93; display: flex; align-items: center; gap: 5px; font-size: 14px; }
.state-text { color: #3e64ff; font-weight: 500; text-transform: uppercase; }

.info-section { padding: 0 20px; }
.menu-item {
  display: flex; justify-content: space-between; align-items: center;
  padding: 20px 0; border-bottom: 1px solid rgba(255,255,255,0.1);
  font-size: 16px; color: #fff;
}

.popup-content { padding: 25px; color: white; }
.popup-header { font-size: 20px; font-weight: bold; margin-bottom: 20px; text-align: center; }
.dark-field { background: #2c2c2e; border-radius: 10px; margin-bottom: 15px; padding: 15px; }
.upload-area { margin: 20px 0; text-align: center; }
.upload-area p { font-size: 12px; color: #666; margin-top: 5px; }
.submit-area { margin-top: 30px; }
</style>
