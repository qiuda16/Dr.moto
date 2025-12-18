<template>
  <div class="page-container climate-view">
    <van-nav-bar
      title="Climate"
      left-arrow
      @click-left="$router.back()"
      class="transparent-nav"
    />

    <div class="climate-content">
      <div class="temp-display">
        <div class="temp-val">{{ temperature }}°</div>
        <div class="temp-status">{{ isOn ? 'Heating...' : 'Off' }}</div>
      </div>

      <div class="car-visualization">
        <!-- Abstract Car Top View -->
        <div class="car-outline">
          <div class="airflow" v-if="isOn">
            <div class="flow-arrow a1"></div>
            <div class="flow-arrow a2"></div>
            <div class="flow-arrow a3"></div>
          </div>
        </div>
      </div>

      <div class="controls-panel">
        <div class="power-btn" :class="{ active: isOn }" @click="togglePower">
          <van-icon name="power-o" />
        </div>

        <div class="slider-container">
          <van-slider v-model="temperature" :min="16" :max="30" bar-height="4px" active-color="#e74c3c" />
          <div class="slider-labels">
            <span>Lo</span>
            <span>Hi</span>
          </div>
        </div>

        <div class="mode-toggles">
          <div class="mode-btn active">Auto</div>
          <div class="mode-btn">A/C</div>
          <div class="mode-btn">Recirc</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const temperature = ref(22)
const isOn = ref(true)

const togglePower = () => {
  isOn.value = !isOn.value
}
</script>

<style scoped>
.climate-view { background: linear-gradient(to bottom, #1a1a1a, #000); height: 100vh; display: flex; flex-direction: column; }
.transparent-nav { background: transparent; --van-nav-bar-icon-color: white; --van-nav-bar-title-text-color: white; }

.climate-content { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: space-between; padding-bottom: 40px; }

.temp-display { text-align: center; margin-top: 20px; }
.temp-val { font-size: 72px; font-weight: 200; letter-spacing: -2px; }
.temp-status { color: var(--text-secondary); font-size: 14px; text-transform: uppercase; letter-spacing: 2px; }

.car-visualization { flex: 1; display: flex; align-items: center; justify-content: center; width: 100%; position: relative; }
.car-outline {
  width: 120px; height: 240px;
  border: 2px solid #333; border-radius: 20px;
  position: relative;
  background: #111;
}

.airflow .flow-arrow {
  position: absolute; width: 4px; height: 20px; background: rgba(231, 76, 60, 0.5); border-radius: 2px;
  animation: flow 1s infinite linear;
}
.a1 { top: 20%; left: 30%; animation-delay: 0s; }
.a2 { top: 20%; left: 50%; animation-delay: 0.3s; }
.a3 { top: 20%; left: 70%; animation-delay: 0.6s; }

@keyframes flow {
  0% { transform: translateY(0); opacity: 0; }
  50% { opacity: 1; }
  100% { transform: translateY(50px); opacity: 0; }
}

.controls-panel { width: 100%; padding: 0 30px; }

.power-btn {
  width: 60px; height: 60px; border-radius: 50%; background: #333;
  display: flex; justify-content: center; align-items: center;
  font-size: 24px; margin: 0 auto 30px; cursor: pointer;
  transition: all 0.3s;
}
.power-btn.active { background: #3498db; color: white; box-shadow: 0 0 20px rgba(52, 152, 219, 0.4); }

.slider-container { margin-bottom: 30px; }
.slider-labels { display: flex; justify-content: space-between; margin-top: 10px; color: #666; font-size: 12px; }

.mode-toggles { display: flex; justify-content: center; gap: 15px; }
.mode-btn {
  padding: 8px 20px; border-radius: 20px; background: #222; color: #888; font-size: 14px; cursor: pointer;
}
.mode-btn.active { background: #444; color: white; }
</style>
