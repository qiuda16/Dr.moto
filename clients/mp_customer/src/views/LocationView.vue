<template>
  <div class="page-container location-view">
    <van-nav-bar
      title="Location"
      left-arrow
      @click-left="$router.back()"
      class="transparent-nav"
    />
    
    <div class="map-container">
      <!-- Mock Map Background -->
      <div class="map-bg"></div>
      
      <!-- Vehicle Pin -->
      <div class="pin vehicle-pin">
        <div class="pin-icon">🏍️</div>
        <div class="pin-label">My Ninja</div>
      </div>

      <!-- Mock POI Pins -->
      <div class="pin poi-pin" style="top:30%; left:20%;">
        <div class="dot"></div>
      </div>
      <div class="pin poi-pin" style="top:60%; left:80%;">
        <div class="dot"></div>
      </div>
    </div>

    <div class="location-card">
      <div class="address-row">
        <van-icon name="location" class="icon" />
        <div class="text">
          <div class="title">123 Main Street</div>
          <div class="subtitle">San Francisco, CA</div>
        </div>
      </div>
      <div class="action-row">
        <button class="btn-nav">Navigate</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.location-view { height: 100vh; display: flex; flex-direction: column; padding: 0; }
.transparent-nav { position: absolute; top: 0; left: 0; right: 0; z-index: 10; background: transparent; }

.map-container { flex: 1; background: #222; position: relative; overflow: hidden; }
.map-bg {
  width: 100%; height: 100%;
  background-image: radial-gradient(#333 1px, transparent 1px);
  background-size: 20px 20px;
  opacity: 0.3;
}

.pin { position: absolute; transform: translate(-50%, -100%); display: flex; flex-direction: column; align-items: center; }
.vehicle-pin { top: 50%; left: 50%; }
.vehicle-pin .pin-icon { font-size: 24px; background: #3498db; width: 40px; height: 40px; border-radius: 50%; display: flex; justify-content: center; align-items: center; box-shadow: 0 4px 10px rgba(0,0,0,0.5); border: 2px solid white; }
.vehicle-pin .pin-label { margin-top: 5px; background: rgba(0,0,0,0.7); padding: 2px 6px; border-radius: 4px; font-size: 10px; }

.poi-pin .dot { width: 10px; height: 10px; background: #e74c3c; border-radius: 50%; border: 2px solid white; }

.location-card {
  background: #1e1e1e;
  padding: 20px;
  border-radius: 20px 20px 0 0;
  box-shadow: 0 -5px 20px rgba(0,0,0,0.3);
}
.address-row { display: flex; align-items: center; gap: 15px; margin-bottom: 20px; }
.address-row .icon { font-size: 24px; color: #3498db; }
.address-row .title { font-size: 18px; font-weight: 600; }
.address-row .subtitle { color: #888; }

.btn-nav {
  width: 100%; padding: 12px; border-radius: 10px; border: none;
  background: #3498db; color: white; font-weight: 600; cursor: pointer;
}
</style>
