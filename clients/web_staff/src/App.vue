<template>
  <div class="app-layout">
    <el-container>
      <el-aside width="220px" class="sidebar">
        <div class="logo">DrMoto <span class="badge">Admin</span></div>
        <el-menu
          router
          :default-active="$route.path"
          background-color="#001529"
          text-color="#fff"
          active-text-color="#409EFF"
        >
          <el-menu-item index="/">
            <el-icon><Odometer /></el-icon>
            <span>Dashboard</span>
          </el-menu-item>
          <el-menu-item index="/orders">
            <el-icon><List /></el-icon>
            <span>Work Orders</span>
          </el-menu-item>
          <el-menu-item index="/customers">
            <el-icon><User /></el-icon>
            <span>Customers</span>
          </el-menu-item>
          <el-menu-item index="/inventory">
            <el-icon><Box /></el-icon>
            <span>Inventory</span>
          </el-menu-item>
        </el-menu>
      </el-aside>
      
      <el-container>
        <el-header class="page-header">
          <div class="breadcrumb">Shop Floor Console</div>
          <div class="user-profile">
            <el-avatar size="small" src="https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png" />
            <span style="margin-left: 10px">Manager</span>
          </div>
        </el-header>
        
        <el-main class="main-content">
          <router-view />
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<style scoped>
.app-layout { height: 100vh; display: flex; }
.sidebar { background-color: #001529; color: white; display: flex; flex-direction: column; }
.logo { height: 60px; line-height: 60px; text-align: center; font-size: 20px; font-weight: bold; background: #002140; }
.badge { font-size: 10px; background: #409EFF; padding: 2px 6px; border-radius: 4px; vertical-align: top; }

.el-menu { border: none; flex: 1; }
</style>
