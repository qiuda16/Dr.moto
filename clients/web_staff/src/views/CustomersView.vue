<template>
  <div class="customers-page">
    <div class="card overview-card">
      <div class="overview-title">
        <div>
          <h3>客户库</h3>
      <p>{{ customerIntroText }}</p>
        </div>
        <el-button type="primary" @click="openCreateDialog">新建客户</el-button>
      </div>

      <div class="overview-kpis">
        <div class="kpi-item">
          <span>客户总数</span>
          <strong>{{ customers.length }}</strong>
        </div>
        <div class="kpi-item">
          <span>车辆总数</span>
          <strong>{{ totalVehicleCount }}</strong>
        </div>
        <div class="kpi-item">
          <span>有车辆客户</span>
          <strong>{{ customersWithVehicles }}</strong>
        </div>
      </div>
    </div>

    <div class="card domain-card">
      <strong>{{ customerDomainTitle }}</strong>
          <span>{{ customerDomainText }}</span>
    </div>

    <el-alert
      v-if="pageError"
      :title="pageError"
      type="error"
      show-icon
      :closable="false"
      class="page-alert"
    >
      <template #default>
        <el-button text type="primary" @click="loadCustomers">重新加载客户库</el-button>
      </template>
    </el-alert>

    <div class="card toolbar-card">
      <div class="toolbar">
        <el-input
          v-model="query"
          placeholder="搜索姓名、手机号、车牌"
          clearable
          style="max-width: 320px;"
          @keyup.enter="loadCustomers"
        />
        <div class="actions">
          <el-button type="primary" plain @click="loadCustomers">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
          <el-dropdown trigger="click" @command="onCustomerMoreCommand">
            <el-button plain>更多操作</el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="batch-pin" :disabled="!selectedCustomerIds.length">批量置顶</el-dropdown-item>
                <el-dropdown-item command="clear-pin" :disabled="!pinnedCustomerIds.length">清空置顶</el-dropdown-item>
                <el-dropdown-item command="batch-delete" :disabled="!selectedCustomerIds.length" divided>批量删除</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>
    </div>

    <div class="card">
      <el-table
        ref="customerTableRef"
        :data="customers"
        v-loading="loading"
        :element-loading-text="TABLE_LOADING_TEXT"
        :empty-text="EMPTY_TEXT.customers"
        row-key="id"
        @selection-change="onCustomerSelectionChange"
        @row-dblclick="onCustomerRowDblClick"
      >
        <el-table-column type="selection" width="44" />
        <el-table-column prop="name" label="客户姓名" min-width="160" />
        <el-table-column prop="phone" label="手机号" min-width="150" />
        <el-table-column prop="email" label="邮箱" min-width="200" show-overflow-tooltip />
        <el-table-column prop="vehicle_count" label="名下车辆" width="100" />
        <el-table-column label="名下车辆" min-width="360">
          <template #default="scope">
            <div class="vehicle-list">
              <el-tag
                v-for="vehicle in scope.row.vehicles || []"
                :key="vehicle.id"
                size="small"
                effect="plain"
                class="vehicle-tag"
              >
                {{ vehicle.license_plate }} · {{ vehicle.make || '-' }} {{ vehicle.model || '' }} {{ vehicle.year || '' }}
              </el-tag>
              <span v-if="!(scope.row.vehicles || []).length" class="empty-text">暂无车辆</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220">
          <template #default="scope">
            <el-button type="primary" link @click="openProfile(scope.row)">查看档案</el-button>
            <el-dropdown trigger="click" @command="(command) => onCustomerRowMoreCommand(scope.row, command)">
              <el-button type="primary" link>更多</el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="add-vehicle">新增车辆</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="createDialogVisible" title="新建客户（含车辆）" width="860px">
      <el-form :model="createForm" label-width="90px">
        <el-row :gutter="12">
          <el-col :span="8"><el-form-item label="姓名"><el-input v-model="createForm.name" maxlength="80" show-word-limit /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="手机号"><el-input v-model="createForm.phone" maxlength="40" show-word-limit /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="邮箱"><el-input v-model="createForm.email" maxlength="120" show-word-limit /></el-form-item></el-col>
        </el-row>

        <div class="section-title">名下车辆</div>
        <div v-for="(vehicle, index) in createForm.vehicles" :key="index" class="vehicle-editor">
          <div class="vehicle-editor-head">
            <strong>车辆 {{ index + 1 }}</strong>
            <el-button type="danger" plain size="small" @click="removeVehicle(index)" :disabled="createForm.vehicles.length === 1">删除</el-button>
          </div>

          <el-row :gutter="12">
            <el-col :span="8"><el-form-item label="车牌"><el-input v-model="vehicle.license_plate" maxlength="30" show-word-limit placeholder="例如：沪A12345" /></el-form-item></el-col>
            <el-col :span="8">
              <el-form-item label="品牌">
                <el-select v-model="vehicle.make" filterable allow-create default-first-option style="width: 100%;" @change="onVehicleBrandChange(vehicle)">
                  <el-option v-for="item in vehicleBrandOptions" :key="item" :label="item" :value="item" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="车型">
                <div class="model-editor">
                  <el-select v-model="vehicle.catalog_model_id" filterable clearable style="width: 100%;" @change="(id) => onVehicleModelSelect(vehicle, id)">
                    <el-option
                      v-for="item in getVehicleModelOptions(vehicle.make)"
                      :key="item.id"
                      :label="`${item.model_name} (${item.year_from}-${item.year_to})`"
                      :value="item.id"
                    />
                  </el-select>
                  <el-input v-model="vehicle.model" maxlength="120" show-word-limit placeholder="库里没有时可手动填写" />
                </div>
              </el-form-item>
            </el-col>
          </el-row>

          <el-row :gutter="12">
            <el-col :span="8"><el-form-item label="年份"><el-input-number v-model="vehicle.year" :min="1950" :max="2100" controls-position="right" style="width: 100%;" /></el-form-item></el-col>
            <el-col :span="8"><el-form-item label="发动机号"><el-input v-model="vehicle.engine_code" maxlength="80" show-word-limit /></el-form-item></el-col>
            <el-col :span="8"><el-form-item label="VIN"><el-input v-model="vehicle.vin" maxlength="64" show-word-limit /></el-form-item></el-col>
          </el-row>

          <el-row :gutter="12">
            <el-col :span="8"><el-form-item label="颜色"><el-input v-model="vehicle.color" maxlength="40" show-word-limit /></el-form-item></el-col>
          </el-row>
        </div>

        <el-button text type="primary" @click="addVehicleRow">+ 再添加一辆车</el-button>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitCreateCustomer">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="addVehicleDialogVisible" title="为客户新增车辆" width="680px">
      <el-form :model="addVehicleForm" label-width="100px">
        <el-row :gutter="12">
          <el-col :span="12"><el-form-item label="车牌"><el-input v-model="addVehicleForm.license_plate" maxlength="30" show-word-limit /></el-form-item></el-col>
          <el-col :span="12">
            <el-form-item label="品牌">
              <el-select v-model="addVehicleForm.make" filterable allow-create default-first-option style="width: 100%;" @change="onVehicleBrandChange(addVehicleForm)">
                <el-option v-for="item in vehicleBrandOptions" :key="item" :label="item" :value="item" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="车型">
              <div class="model-editor">
                <el-select v-model="addVehicleForm.catalog_model_id" filterable clearable style="width: 100%;" @change="(id) => onVehicleModelSelect(addVehicleForm, id)">
                  <el-option
                    v-for="item in getVehicleModelOptions(addVehicleForm.make)"
                    :key="item.id"
                    :label="`${item.model_name} (${item.year_from}-${item.year_to})`"
                    :value="item.id"
                  />
                </el-select>
                <el-input v-model="addVehicleForm.model" maxlength="120" show-word-limit placeholder="库里没有时可手动填写" />
              </div>
            </el-form-item>
          </el-col>
          <el-col :span="12"><el-form-item label="年份"><el-input-number v-model="addVehicleForm.year" :min="1950" :max="2100" controls-position="right" style="width: 100%;" /></el-form-item></el-col>
        </el-row>

        <el-row :gutter="12">
          <el-col :span="12"><el-form-item label="发动机号"><el-input v-model="addVehicleForm.engine_code" maxlength="80" show-word-limit /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="VIN"><el-input v-model="addVehicleForm.vin" maxlength="64" show-word-limit /></el-form-item></el-col>
        </el-row>

        <el-form-item label="颜色"><el-input v-model="addVehicleForm.color" maxlength="40" show-word-limit /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addVehicleDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingVehicle" @click="submitAddVehicle">保存</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="profileVisible" title="客户档案" size="1040px">
      <template v-if="profileCustomer">
        <div class="profile-head">
          <div class="row-between">
            <div>
              <div class="profile-name">{{ profileCustomer.name }}</div>
              <div class="profile-meta">
                <span>手机号：{{ profileCustomer.phone || '-' }}</span>
                <span>邮箱：{{ profileCustomer.email || '-' }}</span>
                <span>车辆数：{{ profileVehicles.length }}</span>
              </div>
            </div>
            <el-button type="primary" plain size="small" @click="openEditCustomerDialog">编辑客户</el-button>
          </div>

          <div class="profile-kpi">
            <div class="kpi-item"><span>工单总数</span><strong>{{ profileSummary.total_orders || 0 }}</strong></div>
            <div class="kpi-item"><span>已完成工单</span><strong>{{ profileSummary.done_orders || 0 }}</strong></div>
            <div class="kpi-item"><span>累计消费</span><strong>¥{{ Number(profileSummary.total_amount || 0).toFixed(2) }}</strong></div>
            <div class="kpi-item"><span>最近到店</span><strong>{{ profileSummary.last_visit_at || '-' }}</strong></div>
          </div>
        </div>

        <div class="profile-layout">
          <div class="profile-side">
            <div class="section-head">
              <span>名下车辆</span>
              <el-button type="primary" size="small" plain @click="openAddVehicleDialog(profileCustomer)">新增车辆</el-button>
            </div>

            <div v-if="profileVehicles.length" class="vehicle-card-list">
              <button
                v-for="vehicle in profileVehicles"
                :key="vehicle.id"
                class="vehicle-card"
                :class="{ active: selectedVehiclePlate === vehicle.license_plate }"
                @click="selectVehicleTimeline(vehicle)"
              >
                <div class="vehicle-card-top">
                  <strong>{{ vehicle.license_plate }}</strong>
                  <span>{{ vehicle.year || '-' }}</span>
                </div>
                <div class="vehicle-card-main">{{ vehicle.make || '-' }} {{ vehicle.model || '' }}</div>
                <div class="vehicle-card-meta">VIN：{{ vehicle.vin || '-' }}</div>
              </button>
            </div>
            <div v-else class="empty-panel">该客户还没有车辆。</div>
          </div>

          <div class="profile-main">
            <div v-if="selectedVehicle" class="profile-focus-card">
              <div class="profile-focus-main">
                <div class="section-head profile-focus-head">
                  <span>当前车辆重点</span>
                  <div class="section-actions">
                    <el-button size="small" :disabled="!selectedVehicle" @click="openEditVehicleDialog(selectedVehicle)">编辑车辆</el-button>
                    <el-button plain size="small" :disabled="!selectedVehiclePlate" @click="openIntakeFromProfile">开工单</el-button>
                    <el-button type="primary" size="small" :disabled="!selectedVehiclePlate" @click="openHealthDialog">新增体检记录</el-button>
                  </div>
                </div>
                <div class="profile-focus-title">{{ selectedVehicle.license_plate }} · {{ selectedVehicle.make || '-' }} {{ selectedVehicle.model || '' }}</div>
                <div class="profile-focus-tags">
                  <span>{{ selectedVehicle.year || '年份待补充' }}</span>
                  <span>{{ selectedVehicle.engine_code || '发动机号待补充' }}</span>
                  <span>{{ latestHealthRecord ? '已有体检记录' : '待补首次体检' }}</span>
                  <span>历史工单 {{ selectedVehicleOrders.length }}</span>
                </div>
              </div>
              <div class="profile-focus-grid">
                <div class="focus-box">
                  <span>最近体检</span>
                  <strong>{{ latestHealthRecord?.measured_at || '未记录' }}</strong>
                  <small>{{ latestHealthRecord ? summarizeHealthRecord(latestHealthRecord) : '建议先补一条基础体检记录' }}</small>
                </div>
                <div class="focus-box">
                  <span>最新里程</span>
                  <strong>{{ latestHealthRecord?.odometer_km ?? '-' }}</strong>
                  <small>{{ healthRecords.length > 1 ? `累计变化 ${totalMileageChange}` : '体检记录不足两次' }}</small>
                </div>
                <div class="focus-box">
                  <span>客户累计消费</span>
                  <strong>￥{{ Number(profileSummary.total_amount || 0).toFixed(2) }}</strong>
                  <small>该客户全部车辆的累计历史金额</small>
                </div>
                <div class="focus-box">
                  <span>下一动作</span>
                  <strong>{{ latestHealthRecord ? '继续维护档案' : '先补体检' }}</strong>
                  <small>{{ latestHealthRecord ? '可继续查看时间线或跳转历史工单' : '施工前后都建议留体检记录' }}</small>
                </div>
              </div>
            </div>
            <div class="section-card">
              <div class="section-head">
                <span>当前车辆档案</span>
              </div>

              <template v-if="selectedVehicle">
                <div class="vehicle-summary-grid">
                  <div class="summary-box">
                    <span>该车工单数</span>
                    <strong>{{ selectedVehicleOrders.length }}</strong>
                    <small>当前车牌历史工单</small>
                  </div>
                  <div class="summary-box">
                    <span>最近体检时间</span>
                    <strong>{{ latestHealthRecord?.measured_at || '-' }}</strong>
                    <small>{{ latestHealthRecord ? '最近一次状态留档' : '还没有体检记录' }}</small>
                  </div>
                  <div class="summary-box">
                    <span>最近里程</span>
                    <strong>{{ latestHealthRecord?.odometer_km ?? '-' }}</strong>
                    <small>{{ latestHealthRecord ? '公里' : '等待首次录入' }}</small>
                  </div>
                  <div class="summary-box">
                    <span>较首次里程变化</span>
                    <strong>{{ totalMileageChange }}</strong>
                    <small>{{ healthRecords.length > 1 ? '根据体检时间线计算' : '体检记录不足两次' }}</small>
                  </div>
                </div>

                <div class="vehicle-info-grid">
                  <div class="info-item"><span>车牌</span><strong>{{ selectedVehicle.license_plate || '-' }}</strong></div>
                  <div class="info-item"><span>品牌</span><strong>{{ selectedVehicle.make || '-' }}</strong></div>
                  <div class="info-item"><span>车型</span><strong>{{ selectedVehicle.model || '-' }}</strong></div>
                  <div class="info-item"><span>年份</span><strong>{{ selectedVehicle.year || '-' }}</strong></div>
                  <div class="info-item"><span>发动机号</span><strong>{{ selectedVehicle.engine_code || '-' }}</strong></div>
                  <div class="info-item"><span>VIN</span><strong>{{ selectedVehicle.vin || '-' }}</strong></div>
                  <div class="info-item"><span>颜色</span><strong>{{ selectedVehicle.color || '-' }}</strong></div>
                </div>

                <div class="latest-health-card">
                  <div class="latest-health-head">
                    <strong>最近一次体检摘要</strong>
                    <span>{{ latestHealthRecord?.measured_at || '暂无记录' }}</span>
                  </div>
                  <div v-if="latestHealthRecord" class="latest-health-grid">
                    <div>电压：{{ latestHealthRecord.battery_voltage ?? '-' }} V</div>
                    <div>前胎压：{{ latestHealthRecord.tire_front_psi ?? '-' }}</div>
                    <div>后胎压：{{ latestHealthRecord.tire_rear_psi ?? '-' }}</div>
                    <div>检查摘要：{{ summarizeHealthRecord(latestHealthRecord) }}</div>
                  </div>
                  <div v-else class="empty-inline">这辆车还没有体检记录，建议首次施工前先补一次基础体检。</div>
                </div>
              </template>
              <div v-else class="empty-panel">请选择一辆车查看详细信息。</div>
            </div>

            <div class="section-card">
              <div class="section-head">
                <span>体检时间线（{{ selectedVehiclePlate || '未选择车辆' }}）</span>
              </div>

              <el-table
                :data="healthRecords"
                v-loading="healthLoading"
                :element-loading-text="TABLE_LOADING_TEXT"
                :empty-text="EMPTY_TEXT.healthRecords"
                style="width: 100%"
              >
                <el-table-column prop="measured_at" label="体检时间" width="180" />
                <el-table-column prop="odometer_km" label="里程(km)" width="110" />
                <el-table-column prop="odometer_delta_from_prev" label="较上次变化" width="120">
                  <template #default="scope">
                    {{ scope.row.odometer_delta_from_prev == null ? '-' : Number(scope.row.odometer_delta_from_prev).toFixed(1) }}
                  </template>
                </el-table-column>
                <el-table-column prop="battery_voltage" label="电压(V)" width="100" />
                <el-table-column prop="tire_front_psi" label="前胎压" width="100" />
                <el-table-column prop="tire_rear_psi" label="后胎压" width="100" />
                <el-table-column label="检查摘要" min-width="300" show-overflow-tooltip>
                  <template #default="scope">{{ summarizeHealthRecord(scope.row) }}</template>
                </el-table-column>
                <el-table-column prop="notes" label="备注" min-width="180" show-overflow-tooltip />

              </el-table>
            </div>

            <div class="section-card">
              <div class="section-head">
                <span>历史工单（{{ selectedVehiclePlate || '全部车辆' }}）</span>
              </div>

              <el-table :data="selectedVehicleOrders" :empty-text="EMPTY_TEXT.customerOrders" style="width: 100%" @row-dblclick="openOrderFromProfile">
                <el-table-column prop="name" label="工单号" min-width="160" />
                <el-table-column prop="vehicle_plate" label="车牌" width="110" />
                <el-table-column prop="state" label="状态" width="110" />
                <el-table-column prop="amount_total" label="金额" width="100" />
                <el-table-column prop="date_planned" label="计划时间" min-width="160" />
                <el-table-column label="操作" width="100">
                  <template #default="scope">
                    <el-button type="primary" link @click="openOrderFromProfile(scope.row)">打开工单</el-button>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>
        </div>
      </template>
    </el-drawer>

    <el-dialog v-model="healthDialogVisible" title="新增车辆体检记录" width="1060px">
      <el-form :model="healthForm" label-width="130px">
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="体检时间">
              <el-date-picker v-model="healthForm.measured_at" type="datetime" value-format="YYYY-MM-DDTHH:mm:ssZ" style="width: 100%;" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="里程(km)">
              <el-input-number v-model="healthForm.odometer_km" :min="0" :precision="1" controls-position="right" style="width: 100%;" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">核心指标</el-divider>
        <el-row :gutter="12">
          <el-col :span="8"><el-form-item label="蓄电池电压(V)"><el-input-number v-model="healthForm.battery_voltage" :min="0" :precision="2" controls-position="right" style="width: 100%;" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="前胎压"><el-input-number v-model="healthForm.tire_front_psi" :min="0" :precision="1" controls-position="right" style="width: 100%;" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="后胎压"><el-input-number v-model="healthForm.tire_rear_psi" :min="0" :precision="1" controls-position="right" style="width: 100%;" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="8"><el-form-item label="发动机转速"><el-input-number v-model="healthForm.engine_rpm" :min="0" :precision="0" controls-position="right" style="width: 100%;" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="冷却液温度(°C)"><el-input-number v-model="healthForm.coolant_temp_c" :precision="1" controls-position="right" style="width: 100%;" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="机油寿命(%)"><el-input-number v-model="healthForm.oil_life_percent" :min="0" :max="100" :precision="1" controls-position="right" style="width: 100%;" /></el-form-item></el-col>
        </el-row>

        <el-divider content-position="left">动力与传动</el-divider>
        <el-row :gutter="12">
          <el-col :span="8"><el-form-item label="怠速转速"><el-input-number v-model="healthForm.idle_rpm" :min="0" :precision="0" controls-position="right" style="width: 100%;" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="油门自由行程(mm)"><el-input-number v-model="healthForm.throttle_free_play_mm" :min="0" :precision="1" controls-position="right" style="width: 100%;" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="离合自由行程(mm)"><el-input-number v-model="healthForm.clutch_free_play_mm" :min="0" :precision="1" controls-position="right" style="width: 100%;" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="8"><el-form-item label="链条松紧(mm)"><el-input-number v-model="healthForm.chain_slack_mm" :min="0" :precision="1" controls-position="right" style="width: 100%;" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="发动机异响(0-5)"><el-input-number v-model="healthForm.engine_noise_level" :min="0" :max="5" :precision="0" controls-position="right" style="width: 100%;" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="排烟异常(0-3)"><el-input-number v-model="healthForm.exhaust_smoke_level" :min="0" :max="3" :precision="0" controls-position="right" style="width: 100%;" /></el-form-item></el-col>
        </el-row>

        <el-divider content-position="left">制动 / 轮胎 / 底盘</el-divider>
        <el-row :gutter="12">
          <el-col :span="8"><el-form-item label="前刹车片(mm)"><el-input-number v-model="healthForm.front_brake_pad_mm" :min="0" :precision="1" controls-position="right" style="width: 100%;" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="后刹车片(mm)"><el-input-number v-model="healthForm.rear_brake_pad_mm" :min="0" :precision="1" controls-position="right" style="width: 100%;" /></el-form-item></el-col>
          <el-col :span="8">
            <el-form-item label="ABS 告警">
              <el-select v-model="healthForm.abs_warning" clearable style="width: 100%;">
                <el-option :value="false" label="否" />
                <el-option :value="true" label="是" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="前制动液">
              <el-select v-model="healthForm.front_brake_fluid_level" clearable style="width: 100%;">
                <el-option value="good" label="正常" />
                <el-option value="low" label="偏低" />
                <el-option value="replace" label="建议更换" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="后制动液">
              <el-select v-model="healthForm.rear_brake_fluid_level" clearable style="width: 100%;">
                <el-option value="good" label="正常" />
                <el-option value="low" label="偏低" />
                <el-option value="replace" label="建议更换" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="轮毂轴承异响">
              <el-select v-model="healthForm.wheel_bearing_noise" clearable style="width: 100%;">
                <el-option :value="false" label="否" />
                <el-option :value="true" label="是" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="8"><el-form-item label="前胎纹深度(mm)"><el-input-number v-model="healthForm.front_tread_depth_mm" :min="0" :precision="1" controls-position="right" style="width: 100%;" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="后胎纹深度(mm)"><el-input-number v-model="healthForm.rear_tread_depth_mm" :min="0" :precision="1" controls-position="right" style="width: 100%;" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="启动电流(A)"><el-input-number v-model="healthForm.starter_current_a" :min="0" :precision="1" controls-position="right" style="width: 100%;" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="前减震">
              <el-select v-model="healthForm.front_shock_ok" clearable style="width: 100%;">
                <el-option :value="true" label="正常" />
                <el-option :value="false" label="异常" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="后减震">
              <el-select v-model="healthForm.rear_shock_ok" clearable style="width: 100%;">
                <el-option :value="true" label="正常" />
                <el-option :value="false" label="异常" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8"><el-form-item label="充电电压(V)"><el-input-number v-model="healthForm.charging_voltage" :min="0" :precision="2" controls-position="right" style="width: 100%;" /></el-form-item></el-col>
        </el-row>

        <el-divider content-position="left">电气 / 油液 / 保养计划</el-divider>
        <el-row :gutter="12">
          <el-col :span="6">
            <el-form-item label="前大灯">
              <el-select v-model="healthForm.headlight_ok" clearable style="width: 100%;">
                <el-option :value="true" label="正常" />
                <el-option :value="false" label="故障" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="尾灯">
              <el-select v-model="healthForm.taillight_ok" clearable style="width: 100%;">
                <el-option :value="true" label="正常" />
                <el-option :value="false" label="故障" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="转向灯">
              <el-select v-model="healthForm.turn_signal_ok" clearable style="width: 100%;">
                <el-option :value="true" label="正常" />
                <el-option :value="false" label="故障" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="喇叭">
              <el-select v-model="healthForm.horn_ok" clearable style="width: 100%;">
                <el-option :value="true" label="正常" />
                <el-option :value="false" label="故障" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="冷却液液位">
              <el-select v-model="healthForm.coolant_level" clearable style="width: 100%;">
                <el-option value="full" label="满" />
                <el-option value="normal" label="正常" />
                <el-option value="low" label="偏低" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8"><el-form-item label="机油压力(kPa)"><el-input-number v-model="healthForm.oil_pressure_kpa" :min="0" :precision="1" controls-position="right" style="width: 100%;" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="机油温度(°C)"><el-input-number v-model="healthForm.oil_temp_c" :precision="1" controls-position="right" style="width: 100%;" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="机油状态">
              <el-select v-model="healthForm.oil_condition" clearable style="width: 100%;">
                <el-option value="normal" label="正常" />
                <el-option value="dark" label="偏黑" />
                <el-option value="emulsion" label="乳化" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8"><el-form-item label="渗漏风险(0-3)"><el-input-number v-model="healthForm.leak_risk_level" :min="0" :max="3" :precision="0" controls-position="right" style="width: 100%;" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="车架损伤(0-3)"><el-input-number v-model="healthForm.frame_damage_level" :min="0" :max="3" :precision="0" controls-position="right" style="width: 100%;" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="8"><el-form-item label="外观损伤(0-3)"><el-input-number v-model="healthForm.body_damage_level" :min="0" :max="3" :precision="0" controls-position="right" style="width: 100%;" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="下次保养里程"><el-input-number v-model="healthForm.next_service_km" :min="0" :precision="0" controls-position="right" style="width: 100%;" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="下次保养日期"><el-date-picker v-model="healthForm.next_service_date" type="date" value-format="YYYY-MM-DD" style="width: 100%;" /></el-form-item></el-col>
        </el-row>

        <el-form-item label="备注"><el-input v-model="healthForm.notes" type="textarea" :rows="3" maxlength="1000" show-word-limit /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="healthDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingHealth" @click="submitHealthRecord">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="editCustomerDialogVisible" title="编辑客户" width="560px">
      <el-form :model="editCustomerForm" label-width="90px">
        <el-form-item label="姓名"><el-input v-model="editCustomerForm.name" maxlength="80" show-word-limit /></el-form-item>
        <el-form-item label="手机号"><el-input v-model="editCustomerForm.phone" maxlength="40" show-word-limit /></el-form-item>
        <el-form-item label="邮箱"><el-input v-model="editCustomerForm.email" maxlength="120" show-word-limit /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editCustomerDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingCustomerEdit" @click="submitEditCustomer">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="editVehicleDialogVisible" title="编辑车辆" width="720px">
      <el-form :model="editVehicleForm" label-width="120px">
        <el-row :gutter="12">
          <el-col :span="12"><el-form-item label="车牌"><el-input v-model="editVehicleForm.license_plate" maxlength="30" show-word-limit /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="VIN"><el-input v-model="editVehicleForm.vin" maxlength="64" show-word-limit /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="品牌">
              <el-select v-model="editVehicleForm.make" filterable allow-create default-first-option style="width: 100%;" @change="onVehicleBrandChange(editVehicleForm)">
                <el-option v-for="item in vehicleBrandOptions" :key="item" :label="item" :value="item" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="车型">
              <div class="model-editor">
                <el-select v-model="editVehicleForm.catalog_model_id" filterable clearable style="width: 100%;" @change="(id) => onVehicleModelSelect(editVehicleForm, id)">
                  <el-option
                    v-for="item in getVehicleModelOptions(editVehicleForm.make)"
                    :key="item.id"
                    :label="`${item.model_name} (${item.year_from}-${item.year_to})`"
                    :value="item.id"
                  />
                </el-select>
                <el-input v-model="editVehicleForm.model" maxlength="120" show-word-limit placeholder="库里没有时可手动填写" />
              </div>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12"><el-form-item label="年份"><el-input-number v-model="editVehicleForm.year" :min="1950" :max="2100" controls-position="right" style="width: 100%;" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="发动机号"><el-input v-model="editVehicleForm.engine_code" maxlength="80" show-word-limit /></el-form-item></el-col>
        </el-row>
        <el-form-item label="颜色"><el-input v-model="editVehicleForm.color" maxlength="40" show-word-limit /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVehicleDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingVehicleEdit" @click="submitEditVehicle">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '../utils/request'
import Sortable from 'sortablejs'
import { applyAppSettings, createAppSettingsState } from '../composables/appSettings'
import { createPageFeedbackState } from '../composables/pageFeedback'
import { EMPTY_TEXT, TABLE_LOADING_TEXT } from '../constants/uiState'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const saving = ref(false)
const savingVehicle = ref(false)
const query = ref('')
const customers = ref([])
const customerTableRef = ref(null)
const selectedCustomerIds = ref([])
const pinnedCustomerIds = ref([])
const customCustomerOrderIds = ref([])
let customerSortable = null

const createDialogVisible = ref(false)
const addVehicleDialogVisible = ref(false)
const editCustomerDialogVisible = ref(false)
const editVehicleDialogVisible = ref(false)
const profileVisible = ref(false)
const targetCustomerId = ref(null)
const profileCustomer = ref(null)
const profileVehicles = ref([])
const profileOrders = ref([])
const profileSummary = ref({
  total_orders: 0,
  done_orders: 0,
  completion_rate: 0,
  total_amount: 0,
  last_visit_at: null
})
const selectedVehiclePlate = ref('')
const healthLoading = ref(false)
const healthRecords = ref([])
const healthDialogVisible = ref(false)
const savingHealth = ref(false)
const pendingHealthJump = ref(null)
const savingCustomerEdit = ref(false)
const savingVehicleEdit = ref(false)
const vehicleBrandOptions = ref([])
const vehicleModelOptionsByBrand = ref({})
const appSettings = reactive(createAppSettingsState())
const { pageError, clearPageError, setPageError } = createPageFeedbackState()

const totalVehicleCount = computed(() => customers.value.reduce((sum, item) => sum + Number(item.vehicle_count || (item.vehicles || []).length || 0), 0))
const customersWithVehicles = computed(() => customers.value.filter((item) => Number(item.vehicle_count || (item.vehicles || []).length || 0) > 0).length)
const selectedVehicle = computed(() => (profileVehicles.value || []).find((vehicle) => vehicle.license_plate === selectedVehiclePlate.value) || null)
const selectedVehicleOrders = computed(() => {
  if (!selectedVehiclePlate.value) return profileOrders.value || []
  return (profileOrders.value || []).filter((item) => String(item.vehicle_plate || '') === String(selectedVehiclePlate.value))
})
const latestHealthRecord = computed(() => (healthRecords.value || [])[0] || null)
const normalizedStoreName = computed(() => String(appSettings.store_name || '').trim() || '机车博士')
const customerIntroText = computed(
  () => `这里统一管理 ${normalizedStoreName.value} 的客户和名下实际车辆。标准车型、标准项目和标准资料请到主数据中心维护。`,
)
const customerDomainTitle = computed(() => `${normalizedStoreName.value} 的客户库只管客户和实际到店车辆`)
const customerDomainText = computed(
  () => '品牌、车型、标准项目、套餐、配件型号和手册都统一在主数据中心维护，这里只做引用和留档。',
)
const totalMileageChange = computed(() => {
  const rows = healthRecords.value || []
  if (rows.length < 2) return '-'
  const latest = Number(rows[0]?.odometer_km || 0)
  const earliest = Number(rows[rows.length - 1]?.odometer_km || 0)
  return `${(latest - earliest).toFixed(1)} km`
})
const makeHealthDefaults = () => ({
  measured_at: '',
  odometer_km: 0,
  engine_rpm: null,
  battery_voltage: null,
  tire_front_psi: null,
  tire_rear_psi: null,
  coolant_temp_c: null,
  oil_life_percent: null,
  idle_rpm: null,
  throttle_free_play_mm: null,
  clutch_free_play_mm: null,
  chain_slack_mm: null,
  engine_noise_level: null,
  exhaust_smoke_level: null,
  front_brake_pad_mm: null,
  rear_brake_pad_mm: null,
  front_brake_fluid_level: null,
  rear_brake_fluid_level: null,
  abs_warning: null,
  front_tread_depth_mm: null,
  rear_tread_depth_mm: null,
  wheel_bearing_noise: null,
  front_shock_ok: null,
  rear_shock_ok: null,
  charging_voltage: null,
  starter_current_a: null,
  headlight_ok: null,
  taillight_ok: null,
  turn_signal_ok: null,
  horn_ok: null,
  coolant_level: null,
  oil_pressure_kpa: null,
  oil_temp_c: null,
  oil_condition: null,
  leak_risk_level: null,
  frame_damage_level: null,
  body_damage_level: null,
  next_service_km: null,
  next_service_date: '',
  notes: ''
})

const healthForm = reactive(makeHealthDefaults())

const summarizeHealthRecord = (row) => {
  const extra = row?.extra || {}
  const parts = []
  if (extra.chain_slack_mm != null) parts.push(`链条松紧 ${Number(extra.chain_slack_mm).toFixed(1)}mm`)
  if (extra.front_brake_pad_mm != null || extra.rear_brake_pad_mm != null) {
    const front = extra.front_brake_pad_mm == null ? '-' : Number(extra.front_brake_pad_mm).toFixed(1)
    const rear = extra.rear_brake_pad_mm == null ? '-' : Number(extra.rear_brake_pad_mm).toFixed(1)
    parts.push(`刹车片 前/后 ${front}/${rear}mm`)
  }
  if (extra.front_tread_depth_mm != null || extra.rear_tread_depth_mm != null) {
    const front = extra.front_tread_depth_mm == null ? '-' : Number(extra.front_tread_depth_mm).toFixed(1)
    const rear = extra.rear_tread_depth_mm == null ? '-' : Number(extra.rear_tread_depth_mm).toFixed(1)
    parts.push(`胎纹深度 前/后 ${front}/${rear}mm`)
  }
  if (extra.abs_warning === true) parts.push('ABS 告警')
  if (extra.leak_risk_level != null && Number(extra.leak_risk_level) >= 2) parts.push(`渗漏风险 ${extra.leak_risk_level}/3`)
  return parts.length ? parts.join(' | ') : '-'
}

const makeEmptyVehicle = () => ({
  catalog_model_id: null,
  license_plate: '',
  make: '',
  model: '',
  year: new Date().getFullYear(),
  engine_code: '',
  vin: '',
  color: ''
})

const createForm = reactive({
  name: '',
  phone: '',
  email: '',
  vehicles: [makeEmptyVehicle()]
})

const addVehicleForm = reactive(makeEmptyVehicle())
const editCustomerForm = reactive({ id: null, name: '', phone: '', email: '' })
const editVehicleForm = reactive({
  id: null,
  catalog_model_id: null,
  license_plate: '',
  make: '',
  model: '',
  year: new Date().getFullYear(),
  engine_code: '',
  vin: '',
  color: ''
})

const getCustomerPrefKey = () => {
  const storeId = localStorage.getItem('drmoto_store_id') || 'default'
  return `drmoto_customer_table_pref_${storeId}`
}

const loadCustomerPrefs = () => {
  try {
    const raw = localStorage.getItem(getCustomerPrefKey())
    const parsed = raw ? JSON.parse(raw) : {}
    pinnedCustomerIds.value = Array.isArray(parsed.pinned_ids) ? parsed.pinned_ids : []
    customCustomerOrderIds.value = Array.isArray(parsed.custom_order_ids) ? parsed.custom_order_ids : []
  } catch {
    pinnedCustomerIds.value = []
    customCustomerOrderIds.value = []
  }
}

const saveCustomerPrefs = () => {
  localStorage.setItem(getCustomerPrefKey(), JSON.stringify({
    pinned_ids: pinnedCustomerIds.value,
    custom_order_ids: customCustomerOrderIds.value
  }))
}

const applyCustomerPresentation = (rows) => {
  const pinnedSet = new Set(pinnedCustomerIds.value)
  const orderIndex = new Map(customCustomerOrderIds.value.map((id, idx) => [id, idx]))
  return [...rows].sort((a, b) => {
    const pinDiff = Number(pinnedSet.has(b.id)) - Number(pinnedSet.has(a.id))
    if (pinDiff !== 0) return pinDiff
    const ai = orderIndex.has(a.id) ? orderIndex.get(a.id) : Number.MAX_SAFE_INTEGER
    const bi = orderIndex.has(b.id) ? orderIndex.get(b.id) : Number.MAX_SAFE_INTEGER
    if (ai !== bi) return ai - bi
    return Number(b.id || 0) - Number(a.id || 0)
  })
}

const persistCurrentCustomerSequence = () => {
  const visibleIds = customers.value.map((row) => row.id)
  const preserved = customCustomerOrderIds.value.filter((id) => !visibleIds.includes(id))
  customCustomerOrderIds.value = [...visibleIds, ...preserved]
  saveCustomerPrefs()
}

const loadVehicleBrandOptions = async () => {
  try {
    const rows = await request.get('/mp/catalog/vehicle-models/brands', {
      params: { active_only: true }
    })
    vehicleBrandOptions.value = Array.isArray(rows) ? rows : []
  } catch (error) {
    console.error('loadVehicleBrandOptions failed', error)
    vehicleBrandOptions.value = []
  }
}

const loadVehicleModelsByBrand = async (brand) => {
  const normalizedBrand = String(brand || '').trim()
  if (!normalizedBrand) return []
  if (Array.isArray(vehicleModelOptionsByBrand.value[normalizedBrand]) && vehicleModelOptionsByBrand.value[normalizedBrand].length) {
    return vehicleModelOptionsByBrand.value[normalizedBrand]
  }
  try {
    const rows = await request.get('/mp/catalog/vehicle-models/by-brand', {
      params: { brand: normalizedBrand, active_only: true }
    })
    vehicleModelOptionsByBrand.value = {
      ...vehicleModelOptionsByBrand.value,
      [normalizedBrand]: Array.isArray(rows) ? rows : []
    }
    return vehicleModelOptionsByBrand.value[normalizedBrand]
  } catch (error) {
    console.error('loadVehicleModelsByBrand failed', error)
    vehicleModelOptionsByBrand.value = {
      ...vehicleModelOptionsByBrand.value,
      [normalizedBrand]: []
    }
    return []
  }
}

const getVehicleModelOptions = (brand) => {
  const normalizedBrand = (brand || '').trim()
  if (!normalizedBrand) return []
  return (vehicleModelOptionsByBrand.value[normalizedBrand] || [])
    .sort((a, b) => Number(b.year_to || 0) - Number(a.year_to || 0))
}

const loadAppSettings = async () => {
  try {
    const data = await request.get('/mp/settings')
    applyAppSettings(appSettings, data)
  } catch {
    applyAppSettings(appSettings)
  }
}

const onVehicleBrandChange = async (vehicleFormLike) => {
  await loadVehicleModelsByBrand(vehicleFormLike.make)
  const currentOptions = getVehicleModelOptions(vehicleFormLike.make)
  const selected = currentOptions.find((item) => item.id === vehicleFormLike.catalog_model_id)
  if (!selected) {
    vehicleFormLike.catalog_model_id = null
    vehicleFormLike.model = ''
  }
}

const onVehicleModelSelect = (vehicleFormLike, modelId) => {
  const selected = getVehicleModelOptions(vehicleFormLike.make).find((item) => item.id === modelId)
  if (!selected) return
  vehicleFormLike.catalog_model_id = selected.id
  vehicleFormLike.make = selected.brand
  vehicleFormLike.model = selected.model_name
  const nowYear = new Date().getFullYear()
  const safeFrom = Number(selected.year_from || nowYear)
  const safeTo = Number(selected.year_to || nowYear)
  const defaultYear = Math.min(Math.max(nowYear, safeFrom), safeTo)
  vehicleFormLike.year = vehicleFormLike.year || defaultYear
  if (!vehicleFormLike.engine_code && selected.default_engine_code) {
    vehicleFormLike.engine_code = selected.default_engine_code
  }
}

const applyRouteQuery = () => {
  const q = route.query || {}
  query.value = typeof q.query === 'string' ? q.query : ''
  if (q.action === 'health_update') {
    const customerId = typeof q.customer_id === 'string' ? q.customer_id : ''
    const plate = typeof q.plate === 'string' ? q.plate : ''
    if (customerId) pendingHealthJump.value = { customerId, plate }
  }
  if (q.action === 'create') {
    openCreateDialog()
    router.replace({ name: 'customers', query: query.value ? { query: query.value } : {} })
  }
}

const handleStoreChanged = async () => {
  await loadAppSettings()
  vehicleModelOptionsByBrand.value = {}
  await loadVehicleBrandOptions()
  await loadCustomers()
}

onMounted(async () => {
  loadCustomerPrefs()
  applyRouteQuery()
  await loadAppSettings()
  await loadVehicleBrandOptions()
  await loadCustomers()
  window.addEventListener('drmoto-store-changed', handleStoreChanged)
})

watch(() => route.query, async () => {
  applyRouteQuery()
  await loadCustomers()
})

onBeforeUnmount(() => {
  window.removeEventListener('drmoto-store-changed', handleStoreChanged)
  if (customerSortable) {
    customerSortable.destroy()
    customerSortable = null
  }
})

const loadCustomers = async () => {
  loading.value = true
  try {
    const res = await request.get('/mp/workorders/customers/with-vehicles', {
      params: { query: query.value || '', limit: 50 }
    })
    clearPageError()
    customers.value = applyCustomerPresentation(res || [])
    if (pendingHealthJump.value?.customerId) {
      const jump = pendingHealthJump.value
      pendingHealthJump.value = null
      const target = customers.value.find((item) => String(item.id) === String(jump.customerId))
      if (target) {
        await openProfile(target)
        if (jump.plate) {
          const found = (profileVehicles.value || []).find((v) => String(v.license_plate || '') === String(jump.plate))
          if (found) {
            selectedVehiclePlate.value = found.license_plate
            await loadHealthRecords()
          }
        }
        openHealthDialog()
        router.replace({ name: 'customers', query: query.value ? { query: query.value } : {} })
      } else {
        ElMessage.warning('未找到对应客户，请手动补录车辆体检。')
      }
    }
    await nextTick()
    initCustomerSortable()
  } catch (error) {
    setPageError('加载客户库失败，请稍后重试', error)
    ElMessage.error(error?.message || '加载客户库失败')
  } finally {
    loading.value = false
  }
}

const resetFilters = async () => {
  query.value = ''
  router.replace({ name: 'customers', query: {} })
  await loadCustomers()
}

const resetCreateForm = () => {
  createForm.name = ''
  createForm.phone = ''
  createForm.email = ''
  createForm.vehicles = [makeEmptyVehicle()]
}

const openCreateDialog = () => {
  resetCreateForm()
  createDialogVisible.value = true
}

const addVehicleRow = () => createForm.vehicles.push(makeEmptyVehicle())
const removeVehicle = (index) => {
  if (createForm.vehicles.length > 1) createForm.vehicles.splice(index, 1)
}
const validateVehicle = (vehicle) => vehicle.license_plate && vehicle.make && vehicle.model && vehicle.year

const submitCreateCustomer = async () => {
  if (!createForm.name) return ElMessage.warning('请先填写客户姓名')
  const validVehicles = createForm.vehicles.filter(validateVehicle)
  if (!validVehicles.length) return ElMessage.warning('请至少填写一辆完整车辆信息')
  saving.value = true
  try {
    const created = await request.post('/mp/workorders/customers', {
      name: createForm.name,
      phone: createForm.phone || null,
      email: createForm.email || null,
      vehicles: validVehicles
    })
    ElMessage.success('客户与车辆创建成功，已打开客户档案')
    createDialogVisible.value = false
    await loadCustomers()
    const latest = customers.value.find((item) => String(item.id) === String(created?.id))
    if (latest) await openProfile(latest)
  } finally {
    saving.value = false
  }
}

const openAddVehicleDialog = (customer) => {
  targetCustomerId.value = customer.id
  Object.assign(addVehicleForm, makeEmptyVehicle())
  addVehicleDialogVisible.value = true
}

const submitAddVehicle = async () => {
  if (!targetCustomerId.value) return
  if (!validateVehicle(addVehicleForm)) return ElMessage.warning('请填写完整车辆信息')
  savingVehicle.value = true
  try {
    await request.post(`/mp/workorders/customers/${targetCustomerId.value}/vehicles`, addVehicleForm)
    ElMessage.success('车辆新增成功')
    addVehicleDialogVisible.value = false
    await loadCustomers()
    const latest = customers.value.find((item) => item.id === targetCustomerId.value)
    if (latest && profileVisible.value) await openProfile(latest)
  } finally {
    savingVehicle.value = false
  }
}

const initCustomerSortable = () => {
  const tableVm = customerTableRef.value
  const tbody = tableVm?.$el?.querySelector('.el-table__body-wrapper tbody')
  if (!tbody) return
  if (customerSortable) {
    customerSortable.destroy()
    customerSortable = null
  }
  customerSortable = Sortable.create(tbody, {
    animation: 120,
    onEnd: ({ oldIndex, newIndex }) => {
      if (oldIndex == null || newIndex == null || oldIndex === newIndex) return
      const list = [...customers.value]
      const [moved] = list.splice(oldIndex, 1)
      list.splice(newIndex, 0, moved)
      customers.value = list
      persistCurrentCustomerSequence()
    }
  })
}

const onCustomerSelectionChange = (rows) => {
  selectedCustomerIds.value = (rows || []).map((row) => row.id)
}

const onCustomerRowDblClick = async (row) => {
  await openProfile(row)
}

const batchPinCustomers = () => {
  if (!selectedCustomerIds.value.length) return
  const set = new Set(pinnedCustomerIds.value)
  selectedCustomerIds.value.forEach((id) => set.add(id))
  pinnedCustomerIds.value = Array.from(set)
  saveCustomerPrefs()
  customers.value = applyCustomerPresentation(customers.value)
  ElMessage.success(`已置顶 ${selectedCustomerIds.value.length} 位客户`)
}

const clearCustomerPins = () => {
  pinnedCustomerIds.value = []
  saveCustomerPrefs()
  customers.value = applyCustomerPresentation(customers.value)
}

const confirmBatchDeleteCustomers = async () => {
  if (!selectedCustomerIds.value.length) return
  try {
    await ElMessageBox.confirm(
      `将删除选中的 ${selectedCustomerIds.value.length} 位客户及其车辆关联数据，此操作不可恢复。是否继续？`,
      '风险操作确认',
      { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  await batchDeleteCustomers()
}

const onCustomerMoreCommand = async (command) => {
  if (command === 'batch-pin') {
    batchPinCustomers()
    return
  }
  if (command === 'clear-pin') {
    clearCustomerPins()
    ElMessage.success('已清空置顶客户')
    return
  }
  if (command === 'batch-delete') await confirmBatchDeleteCustomers()
}
const onCustomerRowMoreCommand = async (row, command) => {
  if (!row) return
  if (command === 'add-vehicle') openAddVehicleDialog(row)
}

const batchDeleteCustomers = async () => {
  if (!selectedCustomerIds.value.length) return
  const deletingIds = [...selectedCustomerIds.value]
  const results = await Promise.allSettled(
    deletingIds.map((id) => request.delete(`/mp/workorders/customers/${id}`))
  )
  const failed = results.filter((x) => x.status === 'rejected').length
  if (failed > 0) {
    ElMessage.warning(`批量删除完成，成功 ${deletingIds.length - failed} 位，失败 ${failed} 位`)
  } else {
    ElMessage.success(`已删除 ${deletingIds.length} 位客户`)
  }
  selectedCustomerIds.value = []
  pinnedCustomerIds.value = pinnedCustomerIds.value.filter((id) => !deletingIds.includes(id))
  customCustomerOrderIds.value = customCustomerOrderIds.value.filter((id) => !deletingIds.includes(id))
  saveCustomerPrefs()
  await loadCustomers()
}

const openEditCustomerDialog = () => {
  if (!profileCustomer.value) return
  editCustomerForm.id = profileCustomer.value.id
  editCustomerForm.name = profileCustomer.value.name || ''
  editCustomerForm.phone = profileCustomer.value.phone || ''
  editCustomerForm.email = profileCustomer.value.email || ''
  editCustomerDialogVisible.value = true
}

const submitEditCustomer = async () => {
  if (!editCustomerForm.id) return
  if (!editCustomerForm.name) return ElMessage.warning('客户姓名不能为空')
  savingCustomerEdit.value = true
  try {
    const updated = await request.put(`/mp/workorders/customers/${editCustomerForm.id}`, {
      name: editCustomerForm.name,
      phone: editCustomerForm.phone || null,
      email: editCustomerForm.email || null
    })
    ElMessage.success('客户信息已更新')
    editCustomerDialogVisible.value = false
    if (profileCustomer.value && profileCustomer.value.id === updated.id) {
      profileCustomer.value = { ...profileCustomer.value, ...updated }
    }
    await loadCustomers()
    const latest = customers.value.find((item) => item.id === updated.id)
    if (latest && profileVisible.value) await openProfile(latest)
  } finally {
    savingCustomerEdit.value = false
  }
}

const openEditVehicleDialog = async (vehicle) => {
  if (!vehicle) return
  if (vehicle.make) await loadVehicleModelsByBrand(vehicle.make)
  editVehicleForm.id = vehicle.id
  editVehicleForm.catalog_model_id = vehicle.catalog_model_id || null
  editVehicleForm.license_plate = vehicle.license_plate || ''
  editVehicleForm.make = vehicle.make || ''
  editVehicleForm.model = vehicle.model || ''
  editVehicleForm.year = Number(vehicle.year || new Date().getFullYear())
  editVehicleForm.engine_code = vehicle.engine_code || ''
  editVehicleForm.vin = vehicle.vin || ''
  editVehicleForm.color = vehicle.color || ''
  editVehicleDialogVisible.value = true
}

const submitEditVehicle = async () => {
  if (!profileCustomer.value || !editVehicleForm.id) return
  if (!editVehicleForm.license_plate || !editVehicleForm.make || !editVehicleForm.model || !editVehicleForm.year) {
    return ElMessage.warning('请完整填写车牌、品牌、车型和年份')
  }
  savingVehicleEdit.value = true
  try {
    await request.put(`/mp/workorders/customers/${profileCustomer.value.id}/vehicles/${editVehicleForm.id}`, {
      catalog_model_id: editVehicleForm.catalog_model_id || null,
      license_plate: editVehicleForm.license_plate,
      make: editVehicleForm.make,
      model: editVehicleForm.model,
      year: Number(editVehicleForm.year),
      engine_code: editVehicleForm.engine_code || null,
      vin: editVehicleForm.vin || null,
      color: editVehicleForm.color || null
    })
    ElMessage.success('车辆信息已更新')
    editVehicleDialogVisible.value = false
    await loadCustomers()
    const latest = customers.value.find((item) => item.id === profileCustomer.value.id)
    if (latest && profileVisible.value) await openProfile(latest)
  } finally {
    savingVehicleEdit.value = false
  }
}

const selectVehicleTimeline = async (vehicle) => {
  selectedVehiclePlate.value = vehicle.license_plate
  await loadHealthRecords()
}

const loadHealthRecords = async () => {
  if (!profileCustomer.value || !selectedVehiclePlate.value) {
    healthRecords.value = []
    return
  }
  healthLoading.value = true
  try {
    const plate = encodeURIComponent(selectedVehiclePlate.value)
    const rows = await request.get(`/mp/workorders/customers/${profileCustomer.value.id}/vehicles/${plate}/health-records`)
    healthRecords.value = rows || []
  } finally {
    healthLoading.value = false
  }
}

const openHealthDialog = () => {
  Object.assign(healthForm, makeHealthDefaults())
  healthDialogVisible.value = true
}

const submitHealthRecord = async () => {
  if (!profileCustomer.value || !selectedVehiclePlate.value) return
  if (healthForm.odometer_km == null || Number(healthForm.odometer_km) < 0) {
    return ElMessage.warning('请输入正确的里程数')
  }
  savingHealth.value = true
  try {
    const plate = encodeURIComponent(selectedVehiclePlate.value)
    const extra = {
      idle_rpm: healthForm.idle_rpm,
      throttle_free_play_mm: healthForm.throttle_free_play_mm,
      clutch_free_play_mm: healthForm.clutch_free_play_mm,
      chain_slack_mm: healthForm.chain_slack_mm,
      engine_noise_level: healthForm.engine_noise_level,
      exhaust_smoke_level: healthForm.exhaust_smoke_level,
      front_brake_pad_mm: healthForm.front_brake_pad_mm,
      rear_brake_pad_mm: healthForm.rear_brake_pad_mm,
      front_brake_fluid_level: healthForm.front_brake_fluid_level,
      rear_brake_fluid_level: healthForm.rear_brake_fluid_level,
      abs_warning: healthForm.abs_warning,
      front_tread_depth_mm: healthForm.front_tread_depth_mm,
      rear_tread_depth_mm: healthForm.rear_tread_depth_mm,
      wheel_bearing_noise: healthForm.wheel_bearing_noise,
      front_shock_ok: healthForm.front_shock_ok,
      rear_shock_ok: healthForm.rear_shock_ok,
      charging_voltage: healthForm.charging_voltage,
      starter_current_a: healthForm.starter_current_a,
      headlight_ok: healthForm.headlight_ok,
      taillight_ok: healthForm.taillight_ok,
      turn_signal_ok: healthForm.turn_signal_ok,
      horn_ok: healthForm.horn_ok,
      coolant_level: healthForm.coolant_level,
      oil_pressure_kpa: healthForm.oil_pressure_kpa,
      oil_temp_c: healthForm.oil_temp_c,
      oil_condition: healthForm.oil_condition,
      leak_risk_level: healthForm.leak_risk_level,
      frame_damage_level: healthForm.frame_damage_level,
      body_damage_level: healthForm.body_damage_level,
      next_service_km: healthForm.next_service_km,
      next_service_date: healthForm.next_service_date || null
    }
    const filteredExtra = Object.fromEntries(
      Object.entries(extra).filter(([, value]) => value !== null && value !== '' && value !== undefined)
    )
    await request.post(`/mp/workorders/customers/${profileCustomer.value.id}/vehicles/${plate}/health-records`, {
      measured_at: healthForm.measured_at || null,
      odometer_km: Number(healthForm.odometer_km),
      engine_rpm: healthForm.engine_rpm,
      battery_voltage: healthForm.battery_voltage,
      tire_front_psi: healthForm.tire_front_psi,
      tire_rear_psi: healthForm.tire_rear_psi,
      coolant_temp_c: healthForm.coolant_temp_c,
      oil_life_percent: healthForm.oil_life_percent,
      notes: healthForm.notes || null,
      extra: Object.keys(filteredExtra).length ? filteredExtra : null
    })
    ElMessage.success('车辆体检记录已保存')
    healthDialogVisible.value = false
    await loadHealthRecords()
    const returnTo = typeof route.query.return_to === 'string' ? route.query.return_to : ''
    const orderId = typeof route.query.order_id === 'string' ? route.query.order_id : ''
    const resumeStatus = typeof route.query.resume_status === 'string' ? route.query.resume_status : ''
    if (returnTo === 'orders' && orderId) {
      await router.push({
        name: 'orders',
        query: {
          order_id: orderId,
          resume_status: resumeStatus || undefined,
          health_saved: '1'
        }
      })
      return
    }
  } finally {
    savingHealth.value = false
  }
}

const openOrderFromProfile = async (row) => {
  const orderId = String(row?.bff_uuid || '').trim()
  if (!orderId) return ElMessage.warning('当前历史工单还没有关联到工单工作台')
  await router.push({
    name: 'orders',
    query: { order_id: orderId }
  })
}

const openIntakeFromProfile = async () => {
  if (!profileCustomer.value?.id || !selectedVehiclePlate.value) return
  await router.push({
    name: 'orders',
    query: {
      action: 'intake',
      intake_customer_id: String(profileCustomer.value.id),
      intake_plate: String(selectedVehiclePlate.value)
    }
  })
}

const openProfile = async (customer) => {
  profileCustomer.value = customer
  profileVisible.value = true
  const [vehicles, orders, summary] = await Promise.all([
    request.get(`/mp/workorders/customers/${customer.id}/vehicles`),
    request.get(`/mp/workorders/customers/${customer.id}/orders`),
    request.get(`/mp/workorders/customers/${customer.id}/summary`)
  ])
  profileVehicles.value = vehicles || []
  profileOrders.value = orders || []
  profileSummary.value = summary || profileSummary.value
  selectedVehiclePlate.value = profileVehicles.value[0]?.license_plate || ''
  await loadHealthRecords()
}
</script>

<style scoped>
.customers-page { display: flex; flex-direction: column; gap: 16px; }
.overview-card, .toolbar-card { padding: 18px 20px; }
.domain-card { padding: 14px 18px; border: 1px solid #dbe7f2; background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%); display: flex; flex-direction: column; gap: 6px; }
.domain-card strong { color: #17324a; font-size: 14px; }
.domain-card span { color: #64748b; font-size: 12px; line-height: 1.7; }
.overview-title { display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; }
.overview-title h3 { margin: 0; font-size: 20px; color: #1f2a44; }
.overview-title p { margin: 8px 0 0; color: #6f7b91; line-height: 1.6; }
.overview-kpis { margin-top: 16px; display: grid; grid-template-columns: repeat(3, minmax(120px, 1fr)); gap: 12px; }
.kpi-item { background: #f6f8fc; border: 1px solid #e6ebf5; border-radius: 10px; padding: 12px 14px; display: flex; flex-direction: column; gap: 6px; }
.kpi-item span { color: #7a8599; font-size: 12px; }
.kpi-item strong { color: #1f2a44; font-size: 20px; }
.toolbar { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; }
.actions { display: flex; gap: 8px; flex-wrap: wrap; }
.vehicle-list { display: flex; flex-wrap: wrap; gap: 6px; }
.vehicle-tag { margin: 0; }
.empty-text { color: #8a94a6; }
.section-title { margin: 6px 0 12px; font-size: 15px; font-weight: 600; color: #1f2a44; }
.vehicle-editor { border: 1px solid #e6ebf5; border-radius: 10px; padding: 14px 14px 4px; margin-bottom: 12px; background: #fbfcff; }
.vehicle-editor-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.model-editor { display: flex; flex-direction: column; gap: 6px; width: 100%; }
.profile-head { margin-bottom: 16px; }
.row-between { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
.profile-name { font-size: 20px; font-weight: 700; color: #1f2a44; }
.profile-meta { margin-top: 8px; color: #6f7b91; display: flex; gap: 14px; flex-wrap: wrap; }
.profile-kpi { margin-top: 14px; display: grid; grid-template-columns: repeat(4, minmax(120px, 1fr)); gap: 8px; }
.profile-focus-card { border: 1px solid #dbe7f2; border-radius: 14px; padding: 14px; background: linear-gradient(180deg, #f5fbff 0%, #ffffff 100%); display: grid; gap: 14px; }
.profile-focus-head { margin-bottom: 0; }
.profile-focus-main { display: grid; gap: 10px; }
.profile-focus-title { font-size: 18px; font-weight: 700; color: #17324a; }
.profile-focus-tags { display: flex; flex-wrap: wrap; gap: 8px; }
.profile-focus-tags span { padding: 6px 10px; border-radius: 999px; background: rgba(255,255,255,0.92); border: 1px solid #d7e7f4; color: #486284; font-size: 12px; }
.profile-focus-grid { display: grid; grid-template-columns: repeat(4, minmax(120px, 1fr)); gap: 10px; }
.focus-box { border: 1px solid #dce8f3; border-radius: 12px; padding: 12px; background: #fff; display: flex; flex-direction: column; gap: 6px; }
.focus-box span, .focus-box small { color: #7a8599; font-size: 12px; line-height: 1.6; }
.focus-box strong { color: #162033; font-size: 20px; line-height: 1.4; }
.profile-layout { display: grid; grid-template-columns: 280px minmax(0, 1fr); gap: 16px; }
.profile-side, .profile-main { display: flex; flex-direction: column; gap: 14px; }
.section-card { border: 1px solid #e7ecf6; border-radius: 12px; padding: 14px; background: #fff; }
.section-head { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 12px; color: #1f2a44; font-weight: 600; }
.section-actions { display: flex; gap: 8px; flex-wrap: wrap; }
.vehicle-card-list { display: flex; flex-direction: column; gap: 10px; }
.vehicle-card { width: 100%; border: 1px solid #dbe3f3; border-radius: 12px; padding: 12px; text-align: left; background: #fff; cursor: pointer; transition: all 0.2s ease; }
.vehicle-card:hover, .vehicle-card.active { border-color: #2b6cb0; box-shadow: 0 8px 20px rgba(43, 108, 176, 0.12); transform: translateY(-1px); }
.vehicle-card-top { display: flex; justify-content: space-between; color: #1f2a44; }
.vehicle-card-main { margin-top: 8px; font-weight: 600; color: #1f2a44; }
.vehicle-card-meta { margin-top: 6px; color: #7a8599; font-size: 12px; }
.vehicle-summary-grid { display: grid; grid-template-columns: repeat(4, minmax(120px, 1fr)); gap: 10px; margin-bottom: 12px; }
.summary-box { border: 1px solid #e2e8f3; border-radius: 12px; padding: 12px; background: #fbfcff; display: flex; flex-direction: column; gap: 6px; }
.summary-box span, .summary-box small { color: #7a8599; font-size: 12px; }
.summary-box strong { font-size: 22px; color: #162033; }
.vehicle-info-grid { display: grid; grid-template-columns: repeat(3, minmax(120px, 1fr)); gap: 10px; }
.info-item { border: 1px solid #e6ebf5; border-radius: 10px; padding: 10px 12px; display: flex; flex-direction: column; gap: 6px; background: #fbfcff; }
.info-item span { color: #7a8599; font-size: 12px; }
.info-item strong { color: #1f2a44; }
.latest-health-card { margin-top: 12px; border: 1px solid #e3ebf6; border-radius: 12px; padding: 12px; background: #f9fbfe; }
.latest-health-head { display: flex; justify-content: space-between; gap: 12px; align-items: center; margin-bottom: 10px; color: #1f2a44; }
.latest-health-head span { color: #7a8599; font-size: 12px; }
.latest-health-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; color: #334155; }
.empty-inline { color: #7a8599; font-size: 13px; }
.empty-panel { padding: 18px; border: 1px dashed #d9e2f2; border-radius: 12px; color: #7a8599; background: #fbfcff; }
@media (max-width: 960px) {
  .profile-layout { grid-template-columns: 1fr; }
  .profile-focus-grid, .vehicle-summary-grid, .vehicle-info-grid, .profile-kpi, .overview-kpis { grid-template-columns: repeat(2, minmax(120px, 1fr)); }
  .latest-health-grid { grid-template-columns: 1fr; }
}
@media (max-width: 640px) {
  .overview-title, .row-between { flex-direction: column; align-items: stretch; }
  .profile-focus-grid, .vehicle-summary-grid, .vehicle-info-grid, .profile-kpi, .overview-kpis { grid-template-columns: 1fr; }
}
</style>
