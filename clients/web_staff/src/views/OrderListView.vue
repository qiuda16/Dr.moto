<template>
  <div class="order-list">
    <div class="card">
      <el-alert
        v-if="pageError"
        :title="pageError"
        type="error"
        show-icon
        :closable="false"
        class="page-alert"
      >
        <template #default>
          <el-button text type="primary" @click="refresh">重新加载工单中心</el-button>
        </template>
      </el-alert>

      <div class="status-tabs">
        <el-tag
          v-for="item in quickStatusesLite"
          :key="item.key"
          :type="activeStatus === item.key ? 'primary' : 'info'"
          class="status-tab"
          effect="plain"
          @click="switchStatus(item.key)"
        >
          {{ item.label }} ({{ statusCount(item.key) }})
        </el-tag>
      </div>

      <div class="toolbar">
        <el-input v-model="filters.plate" placeholder="车牌" style="width: 220px;" clearable @keyup.enter="refresh" />
        <el-input v-model="filters.customer_id" placeholder="客户 ID" style="width: 140px;" clearable @keyup.enter="refresh" />
        <el-switch v-model="simpleMode" active-text="简洁模式" inactive-text="完整模式" inline-prompt />
        <el-button type="primary" @click="openQuickIntakeDialog">快速接车</el-button>
        <el-button type="primary" plain @click="refresh">查询</el-button>
        <el-button @click="resetFilters">重置</el-button>
        <el-dropdown trigger="click" @command="onOrderMoreCommand">
          <el-button plain>更多操作</el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="manual-create">手动开单</el-dropdown-item>
              <el-dropdown-item command="batch-pin" :disabled="!selectedOrderIds.length">批量置顶</el-dropdown-item>
              <el-dropdown-item command="clear-pin" :disabled="!pinnedOrderIds.length">清空置顶</el-dropdown-item>
              <el-dropdown-item command="batch-delete" :disabled="!selectedOrderIds.length" divided>批量删除</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>

      <div class="queue-strip compact-strip">
        <span class="queue-pill">{{ `优先 ${urgentQueueCount}` }}</span>
        <span class="queue-pill">{{ `待交付 ${readyQueueCount}` }}</span>
        <span class="queue-pill">{{ `施工中 ${inProgressQueueCount}` }}</span>
        <span class="queue-pill">{{ `今日新接 ${todayCreatedCount}` }}</span>
      </div>

      <el-table
        :data="orders"
        v-loading="loading"
        :element-loading-text="TABLE_LOADING_TEXT"
        :empty-text="EMPTY_TEXT.orderList"
        style="width: 100%"
        :row-class-name="orderRowClassName"
        @selection-change="onOrderSelectionChange"
        @row-dblclick="onOrderRowDblClick"
      >
        <el-table-column type="selection" width="44" />
        <el-table-column v-if="!simpleMode" prop="id" label="工单编号" min-width="220" />
        <el-table-column prop="vehicle_plate" label="车牌" width="130" />
        <el-table-column v-if="!simpleMode" prop="customer_id" label="客户 ID" width="120" />
        <el-table-column prop="status" label="状态" width="120">
          <template #default="scope">
            <el-tag :type="getStatusType(scope.row.status)">{{ statusLabel(scope.row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column v-if="!simpleMode" label="调度提醒" min-width="180">
          <template #default="scope">
            <div class="mini-tags">
              <span v-if="scope.row.is_urgent" class="flag-tag danger">加急</span>
              <span v-if="scope.row.is_rework" class="flag-tag warn">返修</span>
              <span v-if="scope.row.priority === 'high'">优先</span>
              <span v-if="scope.row.assigned_technician">{{ scope.row.assigned_technician }}</span>
              <span v-if="scope.row.service_bay">{{ scope.row.service_bay }}</span>
              <span v-if="!scope.row.is_urgent && !scope.row.is_rework && !scope.row.assigned_technician && !scope.row.service_bay && scope.row.priority !== 'high'" class="muted">无</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="客户主诉" min-width="240" show-overflow-tooltip />
        <el-table-column v-if="!simpleMode" label="下一步" min-width="180">
          <template #default="scope">
            <div class="queue-hint-cell">
              <strong>{{ rowActionLabel(scope.row) }}</strong>
              <span>{{ rowActionHint(scope.row) }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column v-if="!simpleMode" prop="created_at" label="创建时间" width="200" />
        <el-table-column label="操作" width="220">
          <template #default="scope">
            <el-button size="small" @click="viewDetail(scope.row)">详情</el-button>
            <el-dropdown trigger="click" @command="(command) => onOrderRowMoreCommand(scope.row, command)">
              <el-button size="small" plain>更多</el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="print-work-order">打印维修工单</el-dropdown-item>
                  <el-dropdown-item command="print-quote">打印报价单</el-dropdown-item>
                  <el-dropdown-item command="print-pick-list">打印配件领料单</el-dropdown-item>
                  <el-dropdown-item command="print-delivery-note">打印交付单</el-dropdown-item>
                  <el-dropdown-item command="save-work-order" divided>保存维修工单 PDF</el-dropdown-item>
                  <el-dropdown-item command="save-quote">保存报价单 PDF</el-dropdown-item>
                  <el-dropdown-item command="save-pick-list">保存配件领料单 PDF</el-dropdown-item>
                  <el-dropdown-item command="save-delivery-note">保存交付单 PDF</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            <el-button v-if="nextStatus(scope.row.status)" size="small" type="primary" plain @click="advanceStatus(scope.row)">下一步</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrap">
        <el-pagination v-model:current-page="pagination.page" v-model:page-size="pagination.size" :total="pagination.total" layout="total, prev, pager, next" @current-change="refresh" />
      </div>
    </div>

    <el-drawer v-model="detailVisible" title="工单工作台" size="760px">
      <div v-if="currentOrder">
        <div class="detail-hero">
          <div>
            <div class="detail-hero-title">{{ currentOrder.vehicle_plate || '-' }}</div>
            <div class="detail-hero-subtitle">
              工单号 {{ currentOrder.id }} · 客户 {{ currentOrder.customer_id || '-' }} · 创建于 {{ currentOrder.created_at || '-' }}
            </div>
          </div>
          <div class="detail-hero-status">
            <el-tag :type="getStatusType(currentOrder.status)" size="large">{{ statusLabel(currentOrder.status) }}</el-tag>
            <span v-if="nextStatus(currentOrder.status)" class="next-chip">下一步：{{ statusLabel(nextStatus(currentOrder.status)) }}</span>
            <div class="hero-readiness">
              <span :class="['hero-readiness-chip', servicePlan.workflow_checks?.quote_ready ? 'ok' : 'warn']">报价{{ servicePlan.workflow_checks?.quote_ready ? '已就绪' : '未就绪' }}</span>
              <span :class="['hero-readiness-chip', latestHealthRecord ? 'ok' : 'warn']">体检{{ latestHealthRecord ? '已记录' : '未记录' }}</span>
              <span :class="['hero-readiness-chip', servicePlan.workflow_checks?.delivery_checklist_complete ? 'ok' : 'warn']">交车{{ servicePlan.workflow_checks?.delivery_checklist_complete ? '已确认' : '未确认' }}</span>
            </div>
          </div>
        </div>

        <div class="workflow-overview-card compact-workflow-card">
          <div class="workflow-overview-head">
            <div>
              <div class="detail-title">门店标准动作</div>
              <p>只保留主流程，打开工单先看当前步骤和下一步。</p>
            </div>
            <div class="workflow-overview-actions">
              <el-tag type="primary" effect="plain">当前在 {{ statusLabel(currentOrder.status) }}</el-tag>
              <el-button v-if="recommendedActionLabel" type="primary" plain @click="runRecommendedAction">
                {{ recommendedActionLabel }}
              </el-button>
            </div>
          </div>
          <div class="workflow-overview-grid">
            <div
              v-for="item in orderWorkflowSteps"
              :key="item.key"
              class="workflow-overview-step"
              :class="workflowStepClass(item)"
            >
              <div class="workflow-step-top">
                <span class="workflow-step-index">{{ item.index }}</span>
                <strong>{{ item.title }}</strong>
              </div>
              <div class="workflow-step-foot">
                <el-tag :type="workflowStepTagType(item)" effect="plain">{{ workflowStepTagLabel(item) }}</el-tag>
              </div>
            </div>
          </div>
        </div>

        <div class="drawer-actions">
          <el-tooltip
            v-if="nextStatus(currentOrder.status) && !nextTransitionReady"
            :content="nextTransitionMissingText"
            placement="bottom"
          >
            <el-button type="primary" disabled>推进到 {{ statusLabel(nextStatus(currentOrder.status)) }}</el-button>
          </el-tooltip>
          <el-button
            v-else-if="nextStatus(currentOrder.status)"
            type="primary"
            :loading="advancingFromDetail"
            @click="advanceStatusFromDetail"
          >
            推进到 {{ statusLabel(nextStatus(currentOrder.status)) }}
          </el-button>
          <el-dropdown trigger="click" @command="onDetailMoreCommand">
            <el-button plain>更多操作</el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="print-work-order">打印维修工单</el-dropdown-item>
                <el-dropdown-item command="print-quote">打印报价单</el-dropdown-item>
                <el-dropdown-item command="print-pick-list">打印配件领料单</el-dropdown-item>
                <el-dropdown-item command="print-delivery-note">打印交付单</el-dropdown-item>
                <el-dropdown-item command="save-work-order" divided>保存维修工单 PDF</el-dropdown-item>
                <el-dropdown-item command="save-quote">保存报价单 PDF</el-dropdown-item>
                <el-dropdown-item command="save-pick-list">保存配件领料单 PDF</el-dropdown-item>
                <el-dropdown-item command="save-delivery-note">保存交付单 PDF</el-dropdown-item>
                <el-dropdown-item command="copy-id" divided>复制工单号</el-dropdown-item>
                <el-dropdown-item command="refresh-timeline">刷新时间线</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>

        <div class="focus-summary">
          <div class="focus-summary-main">
            <div class="detail-title">本单重点</div>
            <div class="focus-summary-complaint">{{ currentOrder.description || '暂未记录客户主诉' }}</div>
            <div class="focus-summary-tags">
              <span>{{ servicePlan.vehicle?.make || servicePlan.catalog_model?.brand || '待确认品牌' }}</span>
              <span>{{ servicePlan.vehicle?.model || servicePlan.catalog_model?.model_name || '待确认车型' }}</span>
              <span>已选项目 {{ selectedServiceCount }}</span>
              <span>当前 {{ statusLabel(currentOrder.status) }}</span>
            </div>
          </div>
          <div class="focus-summary-grid">
            <div class="focus-kpi-card">
              <span>当前报价</span>
              <strong>{{ activeQuoteAmountLabel }}</strong>
              <small>{{ servicePlan.workflow_checks?.quote_ready ? '已形成有效报价' : '还未形成有效报价' }}</small>
            </div>
            <div class="focus-kpi-card">
              <span>工单项目</span>
              <strong>{{ selectedServiceCount }}</strong>
              <small>{{ selectedServicePreview }}</small>
            </div>
            <div class="focus-kpi-card">
              <span>最近体检</span>
              <strong>{{ latestHealthMeasuredAtLabel }}</strong>
              <small>{{ latestHealthSnapshotLabel }}</small>
            </div>
            <div class="focus-kpi-card">
              <span>当前重点</span>
              <strong>{{ currentStepTitle }}</strong>
              <small>{{ nextTransitionReady ? '已满足推进条件' : nextTransitionMissingText }}</small>
            </div>
          </div>
          <div class="focus-action-zone compact-focus-zone">
            <div v-if="firstScreenMissingItems.length" class="focus-missing-inline">
              <span class="inline-label">当前缺项</span>
              <div class="focus-missing-list">
                <span v-for="item in firstScreenMissingItems" :key="item">{{ item }}</span>
              </div>
            </div>
            <div class="focus-shortcuts compact-shortcuts">
              <el-button
                v-for="item in firstScreenActions"
                :key="item.key"
                size="small"
                :type="item.type || 'default'"
                :plain="item.type !== 'primary'"
                @click="runFirstScreenAction(item.key)"
              >
                {{ item.label }}
              </el-button>
            </div>
          </div>
        </div>

        <div class="detail-grid">
          <div class="detail-panel">
            <div class="detail-title">车辆与客户</div>
            <div class="detail-inline-tip">{{ orderVehicleTip }}</div>
            <div class="info-grid">
              <div class="info-card"><span>车牌</span><strong>{{ currentOrder.vehicle_plate || '-' }}</strong></div>
              <div class="info-card"><span>客户 ID</span><strong>{{ currentOrder.customer_id || '-' }}</strong></div>
              <div class="info-card"><span>当前状态</span><strong>{{ statusLabel(currentOrder.status) }}</strong></div>
              <div class="info-card"><span>下一状态</span><strong>{{ nextStatus(currentOrder.status) ? statusLabel(nextStatus(currentOrder.status)) : '已结束' }}</strong></div>
            </div>
          </div>

          <div class="detail-panel">
            <div class="detail-title">推进提醒</div>
            <div class="reminder-box">
              <strong>{{ currentStepTitle }}</strong>
              <p>{{ currentStepHint }}</p>
            </div>
          </div>
        </div>

        <div v-if="['in_progress', 'ready'].includes(currentOrder.status)" class="detail-block">
          <div class="detail-title">完工整车体检</div>
          <div class="inspection-workflow">
            <div class="inspection-copy">
              <strong>施工完成后，先做一次整车体检并留档，再进入待交付。</strong>
              <p>建议至少复核里程、电压、胎压、灯光、制动和油液状态。</p>
            </div>
            <div class="inspection-tags">
              <span>里程</span>
              <span>电压</span>
              <span>前后胎压</span>
              <span>灯光喇叭</span>
              <span>制动状态</span>
              <span>油液/渗漏</span>
              <span>外观复核</span>
            </div>
            <div class="inspection-actions">
              <el-button type="primary" @click="goToHealthUpdate(currentOrder)">去做整车体检并记录</el-button>
            </div>
          </div>
        </div>

        <div v-if="currentOrder.status === 'ready'" class="detail-block">
          <div class="detail-title">交付前复核</div>
          <div v-if="latestHealthRecord" class="delivery-summary">
            <div class="delivery-grid">
              <div class="delivery-card"><span>最近体检时间</span><strong>{{ latestHealthRecord.measured_at || '-' }}</strong></div>
              <div class="delivery-card"><span>体检里程</span><strong>{{ latestHealthRecord.odometer_km ?? '-' }}</strong></div>
              <div class="delivery-card"><span>电压</span><strong>{{ latestHealthRecord.battery_voltage ?? '-' }} V</strong></div>
              <div class="delivery-card"><span>前 / 后胎压</span><strong>{{ latestHealthRecord.tire_front_psi ?? '-' }} / {{ latestHealthRecord.tire_rear_psi ?? '-' }}</strong></div>
            </div>
          </div>
          <div v-else class="empty-inline">还没有整车体检记录，建议先完成体检再交付。</div>
        </div>

        <div v-if="['ready', 'done'].includes(currentOrder.status)" class="detail-block">
          <div class="detail-title">交车确认清单</div>
          <div class="delivery-checklist">
            <div v-if="deliveryMissingItems.length" class="delivery-missing-card">
              <strong>交车前还缺这些：</strong>
              <div class="delivery-missing-list">
                <span v-for="item in deliveryMissingItems" :key="item">{{ item }}</span>
              </div>
            </div>
            <div v-if="servicePlan.quote_summary?.active?.amount_total != null" class="delivery-quote-strip">
              <span>当前生效报价金额：{{ servicePlan.quote_summary.active.amount_total }}</span>
              <div class="delivery-quote-actions">
                <el-button size="small" plain @click="applyActiveQuoteAmount">带入收款金额</el-button>
                <el-button size="small" plain @click="applyDeliverySuggestions">自动生成交车备注</el-button>
                <el-button size="small" plain @click="prepareDeliveryChecklist">一键补全基础交车信息</el-button>
              </div>
            </div>
            <el-checkbox v-model="deliveryForm.explained_to_customer">已向客户说明本次维修/保养内容</el-checkbox>
            <el-checkbox v-model="deliveryForm.returned_old_parts">已确认旧件返还或与客户确认处理方式</el-checkbox>
            <el-checkbox v-model="deliveryForm.next_service_notified">已告知下次保养时间或里程建议</el-checkbox>
            <el-checkbox v-model="deliveryForm.payment_confirmed">已确认线下收款方式与金额</el-checkbox>
            <el-form label-width="110px" class="delivery-form">
              <el-form-item label="收款方式">
                <el-select v-model="deliveryForm.payment_method" placeholder="请选择收款方式" style="width: 100%;">
                  <el-option label="现金" value="cash" />
                  <el-option label="微信" value="wechat" />
                  <el-option label="支付宝" value="alipay" />
                  <el-option label="银行卡" value="bank_card" />
                  <el-option label="其他" value="other" />
                </el-select>
              </el-form-item>
              <el-form-item label="收款金额">
                <el-input-number v-model="deliveryForm.payment_amount" :min="0" :precision="2" controls-position="right" style="width: 100%;" />
              </el-form-item>
              <el-form-item label="交车备注">
                <el-input v-model="deliveryForm.notes" type="textarea" :rows="3" maxlength="1000" show-word-limit placeholder="例如：提醒客户 1000 公里后复查链条与机油状态" />
              </el-form-item>
            </el-form>
            <div class="inspection-actions">
              <el-button type="primary" :loading="savingDelivery" @click="saveDeliveryChecklist">保存交车确认</el-button>
            </div>
          </div>
        </div>

        <div class="detail-block">
          <div class="detail-title">接车记录与快速检测</div>
          <el-form label-width="110px">
            <el-form-item label="接车原话">
              <el-input v-model="processForm.symptom_draft" type="textarea" :rows="2" maxlength="1000" show-word-limit placeholder="记录客户原始主诉，尽量保留原话" />
            </el-form-item>
            <el-form-item label="确认症状">
              <el-input v-model="processForm.symptom_confirmed" type="textarea" :rows="2" maxlength="1000" show-word-limit placeholder="技师复核后的标准化故障描述" />
            </el-form-item>
            <el-row :gutter="8">
              <el-col :span="12"><el-form-item label="里程(km)"><el-input-number v-model="processForm.quick_check.odometer_km" :min="0" :precision="1" controls-position="right" style="width: 100%;" /></el-form-item></el-col>
              <el-col :span="12"><el-form-item label="电压(V)"><el-input-number v-model="processForm.quick_check.battery_voltage" :min="0" :precision="2" controls-position="right" style="width: 100%;" /></el-form-item></el-col>
            </el-row>
            <el-row :gutter="8">
              <el-col :span="12"><el-form-item label="前胎压"><el-input-number v-model="processForm.quick_check.tire_front_psi" :min="0" :precision="1" controls-position="right" style="width: 100%;" /></el-form-item></el-col>
              <el-col :span="12"><el-form-item label="后胎压"><el-input-number v-model="processForm.quick_check.tire_rear_psi" :min="0" :precision="1" controls-position="right" style="width: 100%;" /></el-form-item></el-col>
            </el-row>
            <el-form-item label="异响备注"><el-input v-model="processForm.quick_check.engine_noise_note" maxlength="200" show-word-limit placeholder="例如：冷车启动有轻微异响" /></el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="savingProcess" @click="saveProcessRecord">保存接车记录</el-button>
            </el-form-item>
          </el-form>
        </div>

        <div class="detail-block">
          <div class="detail-title">工单项目与报价清单</div>
          <div v-if="servicePlan.catalog_model" class="service-plan-head">
            <div>
              <strong>{{ servicePlan.catalog_model.brand }} {{ servicePlan.catalog_model.model_name }}</strong>
              <p>{{ servicePlanSourceText }}</p>
            </div>
            <div class="service-plan-actions">
              <el-button type="primary" plain :loading="generatingQuote" @click="generateQuoteFromPlan">按已选项目生成报价</el-button>
              <el-button plain :loading="loadingKnowledge" @click="openKnowledgeHub">标准车型资料</el-button>
            </div>
          </div>
          <div v-else class="empty-inline">当前车辆还没有匹配到车型库，请先在客户车辆档案里补齐品牌、车型和年份。</div>

          <div v-if="servicePlan.standard_items?.length" class="service-plan-grid">
            <div>
              <div v-if="servicePlan.service_packages?.length" class="package-recommend-block">
                <div class="minor-title">推荐服务套餐</div>
                <div class="package-recommend-list">
                  <div v-for="pkg in servicePlan.service_packages" :key="pkg.id" class="package-recommend-card">
                    <div class="package-recommend-head">
                      <div>
                        <strong>{{ pkg.package_name }}</strong>
                        <p>{{ pkg.description || '按车型标准保养项目自动组合，可一键带入工单。' }}</p>
                      </div>
                      <el-tag effect="plain" :type="pkg.is_fully_selected ? 'success' : 'primary'">{{ pkg.interval_label || '按需推荐' }}</el-tag>
                    </div>
                    <div class="package-recommend-meta">
                      <span>{{ pkg.item_count }} 个项目</span>
                      <span>工时 {{ pkg.labor_hours_total || 0 }}</span>
                      <span>配件 {{ pkg.parts_price_total || 0 }}</span>
                      <span>建议价 {{ pkg.suggested_price_total || 0 }}</span>
                    </div>
                    <div class="mini-tags">
                      <span v-for="item in pkg.items || []" :key="`${pkg.id}-${item.template_item_id}`">{{ item.service_name }}</span>
                    </div>
                    <div class="package-recommend-foot">
                      <span class="package-selection-hint">
                        {{ pkg.is_fully_selected ? '本套餐项目已全部加入本单' : `还可加入 ${pkg.available_count || 0} 个项目` }}
                      </span>
                      <el-button
                        size="small"
                        type="primary"
                        plain
                        :disabled="pkg.is_fully_selected"
                        :loading="applyingPackageId === pkg.id"
                        @click="applyServicePackage(pkg)"
                      >
                        {{ pkg.is_fully_selected ? '已全部加入' : '一键加入套餐' }}
                      </el-button>
                    </div>
                  </div>
                </div>
              </div>
              <div class="minor-title">标准项目</div>
              <el-table :data="servicePlan.standard_items" size="small" :empty-text="EMPTY_TEXT.standardItems" style="width: 100%">
                <el-table-column prop="service_name" label="项目" min-width="170" />
                <el-table-column prop="labor_hours" label="工时" width="80" />
                <el-table-column prop="suggested_price" label="建议价" width="100" />
                <el-table-column label="配件" min-width="160">
                  <template #default="scope">
                    <div class="mini-tags">
                      <span v-for="part in scope.row.required_parts || []" :key="`${scope.row.template_item_id}-${part.part_no || part.part_name}`">
                        {{ part.part_name }} x{{ part.qty }}
                      </span>
                      <span v-if="!(scope.row.required_parts || []).length" class="muted">无</span>
                    </div>
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="90">
                  <template #default="scope">
                    <el-button size="small" @click="addServiceSelection(scope.row)">加入</el-button>
                  </template>
                </el-table-column>
              </el-table>
            </div>

            <div>
              <div class="minor-title">本工单已选项目</div>
              <el-table :data="servicePlan.selected_items" size="small" :empty-text="EMPTY_TEXT.selectedItems" style="width: 100%">
                <el-table-column prop="service_name" label="项目" min-width="170" />
                <el-table-column prop="parts_total" label="配件费" width="90" />
                <el-table-column prop="labor_price" label="工时费" width="90" />
                <el-table-column prop="line_total" label="合计" width="90" />
                <el-table-column label="操作" width="170">
                  <template #default="scope">
                    <el-button link :disabled="scope.$index === 0" @click="moveServiceSelection(scope.$index, -1)">上移</el-button>
                    <el-button link :disabled="scope.$index === (servicePlan.selected_items?.length || 0) - 1" @click="moveServiceSelection(scope.$index, 1)">下移</el-button>
                    <el-button link @click="editServiceSelection(scope.row)">调整</el-button>
                    <el-button link type="danger" @click="removeServiceSelection(scope.row)">移除</el-button>
                  </template>
                </el-table-column>
              </el-table>
              <div v-if="servicePlan.selected_items?.length" class="selected-service-list">
                <div v-for="item in servicePlan.selected_items" :key="item.id" class="selected-service-card">
                  <div class="selected-service-head">
                    <strong>{{ item.service_name }}</strong>
                    <span>排序 {{ item.sort_order || '-' }}</span>
                  </div>
                  <p>{{ item.repair_method || '还没有补充标准施工说明，可后续在车型库里完善。' }}</p>
                  <div class="mini-tags">
                    <span v-for="part in item.required_parts || []" :key="`${item.id}-${part.part_no || part.part_name}`">{{ part.part_name }} x{{ part.qty }}</span>
                    <span v-if="!(item.required_parts || []).length" class="muted">无配件</span>
                  </div>
                  <div class="selected-service-pricing">
                    <span>配件费：{{ item.parts_total || 0 }}</span>
                    <span>工时费：{{ item.labor_price || 0 }}</span>
                    <span>项目合计：{{ item.line_total || 0 }}</span>
                  </div>
                  <div v-if="item.notes" class="selected-service-note">备注：{{ item.notes }}</div>
                </div>
              </div>
              <div class="service-plan-total">
                <span>配件费：{{ servicePlan.totals?.parts_total || 0 }}</span>
                <span>工时费：{{ servicePlan.totals?.labor_total || 0 }}</span>
                <strong>预计合计：{{ servicePlan.totals?.grand_total || 0 }}</strong>
              </div>
            </div>
          </div>
          <div class="quote-summary-card">
            <div class="quote-summary-head">
              <div>
                <div class="minor-title">报价版本状态</div>
              </div>
              <div class="quote-summary-actions">
                <el-button type="primary" plain :loading="generatingQuote" @click="generateQuoteFromPlan">生成新报价版本</el-button>
                <el-button
                  plain
                  :disabled="!canPublishLatestQuote"
                  :loading="publishingQuote"
                  @click="publishLatestQuote"
                >
                  发布最新报价
                </el-button>
                <el-button
                  plain
                  :disabled="!canConfirmActiveQuote"
                  :loading="confirmingQuote"
                  @click="confirmActiveQuote"
                >
                  确认当前报价
                </el-button>
              </div>
            </div>
            <div class="quote-kpi-grid">
              <div class="quote-kpi-card">
                <span>当前生效版本</span>
                <strong>{{ servicePlan.quote_summary?.active?.version ? `V${servicePlan.quote_summary.active.version}` : '-' }}</strong>
                <small>{{ quoteStatusLabel(servicePlan.quote_summary?.active?.status) }}</small>
              </div>
              <div class="quote-kpi-card">
                <span>最新版本</span>
                <strong>{{ servicePlan.quote_summary?.latest?.version ? `V${servicePlan.quote_summary.latest.version}` : '-' }}</strong>
                <small>{{ quoteStatusLabel(servicePlan.quote_summary?.latest?.status) }}</small>
              </div>
              <div class="quote-kpi-card">
                <span>当前报价金额</span>
                <strong>{{ servicePlan.quote_summary?.active?.amount_total ?? servicePlan.quote_summary?.latest?.amount_total ?? 0 }}</strong>
                <small>{{ servicePlan.workflow_checks?.quote_ready ? '已满足施工前报价要求' : '还未形成有效报价' }}</small>
              </div>
            </div>
            <div v-if="servicePlan.quote_summary?.versions?.length" class="quote-version-list">
              <div v-for="item in servicePlan.quote_summary.versions" :key="item.version" class="quote-version-item">
                <strong>V{{ item.version }}</strong>
                <el-tag :type="quoteStatusType(item.status)" effect="plain">{{ quoteStatusLabel(item.status) }}</el-tag>
                <span>金额 {{ item.amount_total ?? 0 }}</span>
                <span>{{ formatQuoteTime(item.created_at) }}</span>
                <span v-if="item.is_active" class="quote-active-flag">当前生效</span>
              </div>
            </div>
            <div v-else class="empty-inline">还没有生成报价版本，建议在选好工单项目后先生成一版报价。</div>
          </div>
          <div class="workflow-guard-card">
            <div class="minor-title">流程就绪检查</div>
            <div class="workflow-check-list">
              <div v-for="item in servicePlan.workflow_checks?.checkpoints || []" :key="item.key" class="workflow-check-item">
                <div class="workflow-check-main">
                  <el-tag :type="item.done ? 'success' : 'warning'" effect="plain">{{ item.done ? '已完成' : '待补充' }}</el-tag>
                  <strong>{{ item.label }}</strong>
                </div>
                <p>{{ item.hint }}</p>
              </div>
            </div>
            <div class="workflow-next-grid">
              <div v-for="(label, key) in workflowGateLabels" :key="key" class="workflow-next-card">
                <div class="workflow-next-head">
                  <strong>{{ label }}</strong>
                  <el-tag :type="servicePlan.workflow_checks?.gates?.[key]?.ready ? 'success' : 'danger'" effect="plain">
                    {{ servicePlan.workflow_checks?.gates?.[key]?.ready ? '可推进' : '未就绪' }}
                  </el-tag>
                </div>
                <div v-if="servicePlan.workflow_checks?.gates?.[key]?.missing?.length" class="workflow-missing-list">
                  <span v-for="message in servicePlan.workflow_checks.gates[key].missing" :key="message">{{ message }}</span>
                </div>
                <p v-else class="workflow-ready-copy">当前已满足这个节点的前置条件。</p>
              </div>
            </div>
          </div>
        </div>

        <el-collapse v-model="secondaryPanels" class="secondary-panels">
          <el-collapse-item name="knowledge">
            <template #title>
              <div class="collapse-title-wrap">
                <strong>标准资料与作业卡</strong>
                <span>需要查手册、扭矩和标准步骤时再展开</span>
              </div>
            </template>
            <div v-if="servicePlan.catalog_model" class="detail-block collapse-inner-block">
              <div class="knowledge-overview">
                <div class="knowledge-card">
                  <span>关联资料</span>
                  <strong>{{ knowledgeDocuments.length }}</strong>
                  <p>PDF 手册、扭矩表、线路图都可以从这里快速打开。</p>
                </div>
                <div class="knowledge-card">
                  <span>标准作业卡</span>
                  <strong>{{ manualProcedures.length }}</strong>
                  <p>施工时优先按标准步骤和扭矩要求执行。</p>
                </div>
              </div>
              <div class="knowledge-inline-actions">
                <el-button plain :loading="loadingKnowledge" @click="openKnowledgeHub">查看全部标准资料</el-button>
              </div>
            </div>
          </el-collapse-item>
          <el-collapse-item name="advanced">
            <template #title>
              <div class="collapse-title-wrap">
                <strong>高级调度信息</strong>
                <span>工位、技师、优先级、预计完工这些低频内容收在这里</span>
              </div>
            </template>
            <div class="detail-block detail-block-compact collapse-inner-block">
              <div class="advanced-panel">
                <div class="advanced-summary">
                  <span>技师：{{ advancedForm.assigned_technician || '未安排' }}</span>
                  <span>工位：{{ advancedForm.service_bay || '未安排' }}</span>
                  <span>优先级：{{ priorityLabel(advancedForm.priority) }}</span>
                  <span>预计完工：{{ advancedForm.estimated_finish_at || '未设置' }}</span>
                </div>
                <el-form label-width="110px" class="advanced-form">
                  <el-row :gutter="10">
                    <el-col :span="12"><el-form-item label="指派技师"><el-input v-model="advancedForm.assigned_technician" maxlength="40" show-word-limit placeholder="例如：张师傅" /></el-form-item></el-col>
                    <el-col :span="12"><el-form-item label="施工工位"><el-input v-model="advancedForm.service_bay" maxlength="40" show-word-limit placeholder="例如：2号工位" /></el-form-item></el-col>
                  </el-row>
                  <el-row :gutter="10">
                    <el-col :span="12">
                      <el-form-item label="优先级">
                        <el-select v-model="advancedForm.priority" style="width: 100%;">
                          <el-option label="普通" value="normal" />
                          <el-option label="优先" value="high" />
                          <el-option label="加急" value="urgent" />
                        </el-select>
                      </el-form-item>
                    </el-col>
                    <el-col :span="12"><el-form-item label="质检责任人"><el-input v-model="advancedForm.qc_owner" maxlength="40" show-word-limit placeholder="例如：李主管" /></el-form-item></el-col>
                  </el-row>
                  <el-row :gutter="10">
                    <el-col :span="12"><el-form-item label="承诺交车时间"><el-date-picker v-model="advancedForm.promised_at" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" placeholder="选择时间" style="width: 100%;" /></el-form-item></el-col>
                    <el-col :span="12"><el-form-item label="预计完工时间"><el-date-picker v-model="advancedForm.estimated_finish_at" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" placeholder="选择时间" style="width: 100%;" /></el-form-item></el-col>
                  </el-row>
                  <el-form-item label="特殊标记">
                    <div class="advanced-flags">
                      <el-checkbox v-model="advancedForm.is_rework">返修工单</el-checkbox>
                      <el-checkbox v-model="advancedForm.is_urgent">加急处理</el-checkbox>
                    </div>
                  </el-form-item>
                  <el-form-item label="内部备注">
                    <el-input v-model="advancedForm.internal_notes" type="textarea" :rows="3" maxlength="1000" show-word-limit placeholder="例如：客户下午 5 点前必须交车；先做刹车系统后做保养。" />
                  </el-form-item>
                  <el-form-item>
                    <el-button type="primary" :loading="savingAdvanced" @click="saveAdvancedProfile">保存高级信息</el-button>
                  </el-form-item>
                </el-form>
              </div>
            </div>
          </el-collapse-item>
          <el-collapse-item name="assistant">
            <template #title>
              <div class="collapse-title-wrap">
                <strong>AI 工单助理</strong>
                <span>需要让系统总结风险、生成话术或建议动作时再展开</span>
              </div>
            </template>
            <div class="detail-block ai-assistant-block collapse-inner-block">
              <div class="ai-assistant-shell">
                <div class="ai-assistant-input">
                  <el-input
                    v-model="assistantPrompt"
                    type="textarea"
                    :rows="3"
                    placeholder="例如：总结当前工单风险，并建议下一步动作；或帮我给客户生成一段交付说明。"
                  />
                  <div class="ai-assistant-actions">
                    <div class="ai-context-tags">
                      <span>{{ currentOrder.vehicle_plate || '-' }}</span>
                      <span>工单 {{ currentOrder.id }}</span>
                      <span>{{ statusLabel(currentOrder.status) }}</span>
                      <span>{{ selectedServiceCount }} 个项目</span>
                    </div>
                    <div class="ai-assistant-button-row">
                      <el-button plain @click="fillAssistantPrompt('summary')">总结本单</el-button>
                      <el-button plain @click="fillAssistantPrompt('risk')">检查风险</el-button>
                      <el-button plain @click="fillAssistantPrompt('delivery')">生成交付话术</el-button>
                      <el-button type="primary" :loading="assistantLoading" @click="askAiAssistantForOrder">询问 AI 助手</el-button>
                    </div>
                  </div>
                </div>

                <div v-if="assistantReply" class="ai-assistant-result">
                  <div class="ai-reply-copy">{{ assistantReply.response || 'AI 暂时没有返回内容。' }}</div>

                  <div v-if="assistantFormattedSections.length" class="ai-structured-sections">
                    <div v-for="section in assistantFormattedSections" :key="section.key" class="ai-structured-card">
                      <div class="ai-structured-head">
                        <strong>{{ section.title }}</strong>
                        <span>{{ section.description }}</span>
                      </div>
                      <div class="ai-structured-list">
                        <div v-for="(line, index) in section.lines" :key="`${section.key}-${index}`" class="ai-structured-line">
                          <span class="ai-structured-index">{{ index + 1 }}</span>
                          <div class="ai-structured-copy">
                            <span>{{ line.text }}</span>
                            <span v-if="line.tag" :class="['ai-source-chip', `ai-source-chip-${sourceTagTone(line.tag)}`]">{{ line.tag }}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div v-if="assistantSourceSummary.pages.length || assistantSourceSummary.items.length" class="ai-source-panel">
                    <div class="ai-source-head">
                      <strong>参考来源</strong>
                      <span v-if="assistantSourceSummary.pages.length">重点页码：{{ assistantSourceSummary.pages.join('、') }}</span>
                    </div>
                    <div v-if="assistantSourceSummary.pages.length" class="ai-source-page-list">
                      <el-button
                        v-for="page in assistantSourceSummary.pages"
                        :key="`page-${page}`"
                        link
                        type="primary"
                        class="ai-source-page-button"
                        @click="openAssistantKnowledgePage(page)"
                      >
                        页码 {{ page }}
                      </el-button>
                    </div>
                    <div v-if="assistantSourceSummary.items.length" class="ai-source-item-list">
                      <div v-for="(item, index) in assistantSourceSummary.items" :key="`${item.type || 'source'}-${index}`" class="ai-source-item">
                        <div>
                          <strong>{{ item.label || item.summary || '参考记录' }}</strong>
                          <p>{{ item.summary || sourceTypeLabel(item.type) }}</p>
                        </div>
                        <el-button
                          v-if="item.file_url || item.type === 'knowledge'"
                          link
                          type="primary"
                          @click="openAssistantSourceItem(item)"
                        >
                          打开
                        </el-button>
                      </div>
                    </div>
                  </div>

                  <div v-if="assistantReply.suggested_actions?.length" class="ai-suggestion-list">
                    <span v-for="(item, index) in assistantReply.suggested_actions" :key="`${item}-${index}`">{{ item }}</span>
                  </div>

                  <div v-if="assistantReply.action_cards?.length" class="ai-card-list">
                    <div v-for="(card, index) in assistantReply.action_cards" :key="`${card.action || 'card'}-${index}`" class="ai-card-item">
                      <div>
                        <strong>{{ card.label || '建议动作' }}</strong>
                        <p>{{ card.description || card.reason || 'AI 已经帮你准备好预填数据。' }}</p>
                      </div>
                      <div class="ai-card-actions">
                        <el-button plain @click="prefillAssistantAction(card)">先填表</el-button>
                        <el-button type="primary" :loading="assistantExecuting" @click="runAssistantActionCard(card)">直接执行</el-button>
                      </div>
                    </div>
                  </div>

                  <div v-if="assistantReply.debug" class="ai-debug-box">
                    <strong>本次推理信息</strong>
                    <div class="ai-debug-tags">
                      <span v-if="assistantReply.debug.provider">{{ assistantReply.debug.provider }}</span>
                      <span v-if="assistantReply.debug.model">{{ assistantReply.debug.model }}</span>
                      <span>{{ assistantReply.debug.fast_path_used ? '业务快答' : '大模型推理' }}</span>
                      <span v-if="assistantReply.debug.fact_guard_triggered">事实守门已触发</span>
                    </div>
                    <div class="ai-debug-grid">
                      <div>
                        <label>上下文窗口</label>
                        <strong>{{ assistantReply.debug.context_window_tokens ?? '-' }}</strong>
                      </div>
                      <div>
                        <label>本次输入估算</label>
                        <strong>{{ assistantReply.debug.estimated_input_tokens ?? '-' }}</strong>
                      </div>
                      <div>
                        <label>剩余可用上下文</label>
                        <strong>{{ assistantReply.debug.estimated_remaining_tokens ?? '-' }}</strong>
                      </div>
                      <div>
                        <label>知识补充条数</label>
                        <strong>{{ assistantReply.debug.kb_hit_count ?? '-' }}</strong>
                      </div>
                    </div>
                  </div>

                  <div v-if="assistantActionPreview" class="ai-preview-box">
                    <strong>AI 预填动作</strong>
                    <div class="ai-preview-meta">{{ assistantActionPreview.label }} · {{ assistantActionPreview.action }}</div>
                    <pre>{{ JSON.stringify(assistantActionPreview.payload || {}, null, 2) }}</pre>
                  </div>
                </div>
              </div>
            </div>
          </el-collapse-item>
          <el-collapse-item name="timeline">
            <template #title>
              <div class="collapse-title-wrap">
                <strong>工单时间线</strong>
                <span>需要追历史动作和责任人时再展开</span>
              </div>
            </template>
            <div class="detail-block collapse-inner-block">
              <el-timeline>
                <el-timeline-item v-for="(item, index) in timeline" :key="`${item.time || 't'}-${index}`" :timestamp="item.time || '-'" placement="top">
                  <div class="timeline-line"><strong>{{ item.action || '-' }}</strong><span class="timeline-actor">{{ item.actor || '-' }}</span></div>
                </el-timeline-item>
              </el-timeline>
            </div>
          </el-collapse-item>
        </el-collapse>
      </div>
    </el-drawer>
    <el-dialog v-model="createDialogVisible" title="手动开单（备用）" width="640px">
      <el-form :model="createForm" label-width="110px">
        <el-form-item label="客户">
          <el-select v-model="createForm.customer_id" filterable remote reserve-keyword placeholder="搜索客户姓名 / 手机号" :remote-method="searchCustomers" :loading="customerLoading" style="width: 100%;">
            <el-option v-for="item in customerOptions" :key="item.id" :label="`${item.name || '-'} (${item.phone || '-'})`" :value="String(item.id)" />
          </el-select>
        </el-form-item>
        <el-form-item label="车牌"><el-input v-model="createForm.vehicle_plate" maxlength="30" show-word-limit placeholder="例如：沪A12345" /></el-form-item>
        <el-form-item label="客户主诉"><el-input v-model="createForm.description" type="textarea" :rows="3" maxlength="500" show-word-limit /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="submitCreateOrder">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="quickIntakeVisible" title="快速接车" width="760px">
      <el-form label-width="120px">
        <div class="intake-summary">
          <div class="summary-pill">1. 选择客户类型</div>
          <div class="summary-pill">2. 确认车辆</div>
          <div class="summary-pill">3. 填写主诉后立即建单</div>
        </div>
        <el-form-item label="客户类型">
          <el-radio-group v-model="intakeMode">
            <el-radio-button label="existing">老客户</el-radio-button>
            <el-radio-button label="new">新客户</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <template v-if="intakeMode === 'existing'">
          <el-form-item label="客户">
            <el-select v-model="createForm.customer_id" filterable remote reserve-keyword placeholder="搜索客户姓名 / 手机号" :remote-method="searchCustomers" :loading="customerLoading" style="width: 100%;">
              <el-option v-for="item in customerOptions" :key="item.id" :label="`${item.name || '-'} (${item.phone || '-'})`" :value="String(item.id)" />
            </el-select>
          </el-form-item>
          <el-form-item label="车牌">
            <el-select v-model="createForm.vehicle_plate" filterable allow-create default-first-option placeholder="可选择已有车牌，或直接输入新车牌" style="width: 100%;">
              <el-option v-for="item in customerVehicles" :key="item.id" :label="item.license_plate" :value="item.license_plate" />
            </el-select>
          </el-form-item>
          <div class="intake-hint">适合老客户复进店，优先直接选客户和历史车辆，减少重复录入。</div>
        </template>

        <template v-else>
          <div class="intake-section-title">客户信息</div>
          <el-row :gutter="12">
            <el-col :span="8"><el-form-item label="姓名"><el-input v-model="newCustomer.name" maxlength="80" show-word-limit /></el-form-item></el-col>
            <el-col :span="8"><el-form-item label="手机号"><el-input v-model="newCustomer.phone" maxlength="40" show-word-limit /></el-form-item></el-col>
            <el-col :span="8"><el-form-item label="邮箱"><el-input v-model="newCustomer.email" maxlength="120" show-word-limit /></el-form-item></el-col>
          </el-row>

          <div class="intake-section-title">车辆信息</div>
          <el-row :gutter="12">
            <el-col :span="8"><el-form-item label="车牌"><el-input v-model="newCustomer.vehicle_plate" maxlength="30" show-word-limit /></el-form-item></el-col>
            <el-col :span="8">
              <el-form-item label="品牌">
                <el-select v-model="newCustomer.make" filterable allow-create default-first-option style="width: 100%;" @change="onQuickBrandChange">
                  <el-option v-for="item in vehicleBrandOptions" :key="item" :label="item" :value="item" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="车型">
                <div class="model-editor">
                  <el-select v-model="newCustomer.catalog_model_id" filterable clearable style="width: 100%;" @change="onQuickModelSelect">
                    <el-option
                      v-for="item in getVehicleModelOptions(newCustomer.make)"
                      :key="item.id"
                      :label="`${item.model_name} (${item.year_from}-${item.year_to})`"
                      :value="item.id"
                    />
                  </el-select>
                  <el-input v-model="newCustomer.model" maxlength="120" show-word-limit placeholder="库里没有时可手动填写" />
                </div>
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="12">
            <el-col :span="8"><el-form-item label="年份"><el-input-number v-model="newCustomer.year" :min="1950" :max="2100" controls-position="right" style="width: 100%;" /></el-form-item></el-col>
            <el-col :span="8"><el-form-item label="发动机号"><el-input v-model="newCustomer.engine_code" maxlength="80" show-word-limit /></el-form-item></el-col>
            <el-col :span="8"><el-form-item label="VIN"><el-input v-model="newCustomer.vin" maxlength="64" show-word-limit /></el-form-item></el-col>
          </el-row>
          <div class="intake-hint">新客户只填核心信息即可，后续更详细的车辆参数可以在客户档案和体检表里补充。</div>
        </template>

        <el-form-item label="客户主诉">
          <div class="complaint-editor">
            <el-input v-model="createForm.description" type="textarea" :rows="3" maxlength="500" show-word-limit />
            <div class="complaint-chips">
              <el-button
                v-for="item in quickComplaintTemplates"
                :key="item"
                size="small"
                plain
                @click="appendComplaintTemplate(item)"
              >
                {{ item }}
              </el-button>
            </div>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="quickIntakeVisible = false">取消</el-button>
        <el-button type="primary" :loading="creatingQuick" @click="submitQuickIntake">提交接车</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="knowledgeDialogVisible" title="标准车型资料与标准手册" width="920px">
      <div v-if="servicePlan.catalog_model" class="knowledge-dialog">
        <div class="knowledge-dialog-head">
          <div>
            <strong>{{ servicePlan.catalog_model.brand }} {{ servicePlan.catalog_model.model_name }}</strong>
            <p>{{ servicePlan.catalog_model.year_from }} - {{ servicePlan.catalog_model.year_to }} 年款资料与标准作业卡</p>
          </div>
          <el-button plain @click="openCatalogDetailPage">去标准车型库完善</el-button>
        </div>

        <div class="knowledge-dialog-grid">
          <div class="knowledge-panel">
            <div class="minor-title">标准资料</div>
            <div v-if="knowledgeDocuments.length" class="knowledge-list">
              <div v-for="doc in knowledgeDocuments" :key="doc.id" class="knowledge-item">
                <div>
                  <strong>{{ doc.title || doc.file_name }}</strong>
                  <p>{{ doc.category || '资料' }} · {{ doc.file_name }}</p>
                </div>
                <el-button link type="primary" @click="openKnowledgeDocument(doc)">打开</el-button>
              </div>
            </div>
            <div v-else class="empty-inline">这个车型还没有上传标准资料，后续可去标准车型库挂接 PDF 手册。</div>
          </div>

          <div class="knowledge-panel">
            <div class="minor-title">标准作业卡</div>
            <div v-if="manualProcedures.length" class="manual-list">
              <el-collapse>
                <el-collapse-item v-for="proc in manualProcedures" :key="proc.id" :title="`${proc.name}（${proc.steps?.length || 0} 步）`" :name="String(proc.id)">
                  <div class="manual-desc">{{ proc.description || '暂无补充说明' }}</div>
                  <div v-for="step in proc.steps || []" :key="step.id" class="manual-step">
                    <strong>第 {{ step.step_order }} 步</strong>
                    <p>{{ step.instruction }}</p>
                    <div class="manual-meta">
                      <span>工具：{{ step.required_tools || '未填写' }}</span>
                      <span>扭矩/规格：{{ step.torque_spec || '未填写' }}</span>
                      <span>注意事项：{{ step.hazards || '未填写' }}</span>
                    </div>
                  </div>
                </el-collapse-item>
              </el-collapse>
            </div>
            <div v-else class="empty-inline">这个车型还没有标准作业卡，后续可去标准车型库逐步补齐。</div>
          </div>
        </div>
      </div>
    </el-dialog>
    <el-dialog v-model="knowledgePreviewVisible" :title="knowledgePreviewTitle || '标准资料预览'" width="88%" top="4vh">
      <div class="knowledge-preview-shell">
        <iframe v-if="knowledgePreviewUrl" :src="knowledgePreviewUrl" class="knowledge-preview-frame" />
        <div v-else class="empty-inline">当前没有可预览的资料地址。</div>
      </div>
      <div v-if="knowledgePreviewContextItems.length" class="knowledge-preview-context">
        <div class="knowledge-preview-context-head">
          <strong>本次回答引用来源</strong>
          <span>不用回到聊天区也能快速核对</span>
        </div>
        <div class="knowledge-preview-context-list">
          <div v-for="(item, index) in knowledgePreviewContextItems" :key="`${item.type || 'context'}-${index}`" class="knowledge-preview-context-item">
            <strong>{{ item.label || item.summary || '参考记录' }}</strong>
            <p>{{ item.summary || sourceTypeLabel(item.type) }}</p>
          </div>
        </div>
      </div>
      <template #footer>
        <div class="knowledge-preview-controls">
          <span>资料：{{ knowledgePreviewTitle || '标准资料预览' }}</span>
          <span>当前页：{{ knowledgePreviewPage || '-' }}</span>
          <el-input
            v-model="knowledgePreviewPageInput"
            class="knowledge-preview-page-input"
            placeholder="输入页码"
            @keyup.enter="goToKnowledgePreviewPage"
          />
          <el-button plain :disabled="!knowledgePreviewUrl" @click="goToKnowledgePreviewPage">跳转</el-button>
          <el-button plain :disabled="!knowledgePreviewUrl" @click="jumpKnowledgePreviewPage(-1)">上一页</el-button>
          <el-button plain :disabled="!knowledgePreviewUrl" @click="jumpKnowledgePreviewPage(1)">下一页</el-button>
          <el-button plain :disabled="!knowledgePreviewUrl" @click="copyKnowledgePreviewLink">复制当前页链接</el-button>
        </div>
        <div v-if="knowledgePreviewRecentPages.length" class="knowledge-preview-history">
          <span>最近页码：</span>
          <el-button
            v-for="page in knowledgePreviewRecentPages"
            :key="`preview-page-${page}`"
            link
            type="primary"
            @click="openKnowledgePreview({ file_url: knowledgePreviewDocUrl }, page, knowledgePreviewTitle)"
          >
            {{ page }}
          </el-button>
        </div>
        <div v-if="knowledgePreviewContextPages.length" class="knowledge-preview-history">
          <span>本次引用页：</span>
          <el-button
            v-for="page in knowledgePreviewContextPages"
            :key="`context-preview-page-${page}`"
            :link="page !== knowledgePreviewPage"
            type="primary"
            @click="openKnowledgePreview({ file_url: knowledgePreviewDocUrl }, page, knowledgePreviewTitle, { pages: knowledgePreviewContextPages, items: knowledgePreviewContextItems })"
          >
            {{ page }}
          </el-button>
        </div>
        <div class="knowledge-preview-hint">左右方向键可翻页</div>
        <el-button
          plain
          :disabled="!knowledgePreviewUrl"
          @click="knowledgePreviewUrl ? window.open(knowledgePreviewUrl, '_blank') : null"
        >
          新窗口打开
        </el-button>
        <el-button type="primary" @click="knowledgePreviewVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="serviceEditVisible" title="调整工单项目" width="560px">
      <el-form label-width="100px">
        <el-form-item label="工单项目">
          <div class="service-edit-name">{{ serviceEditForm.service_name || '-' }}</div>
        </el-form-item>
        <el-form-item label="配件费">
          <div class="service-edit-name">{{ serviceEditForm.parts_total || 0 }}</div>
        </el-form-item>
        <el-form-item label="工时费">
          <el-input-number v-model="serviceEditForm.labor_price" :min="0" :precision="2" controls-position="right" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="项目合计">
          <el-input-number v-model="serviceEditForm.suggested_price" :min="0" :precision="2" controls-position="right" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="工单备注">
          <el-input v-model="serviceEditForm.notes" type="textarea" :rows="3" maxlength="1000" show-word-limit placeholder="例如：客户自带配件；本次仅先处理前轮制动。" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="serviceEditVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingServiceEdit" @click="submitServiceSelectionEdit">保存调整</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, reactive, ref, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import request from '../utils/request'
import { ElMessage, ElMessageBox } from 'element-plus'
import { applyAppSettings, createAppSettingsState } from '../composables/appSettings'
import { createPageFeedbackState } from '../composables/pageFeedback'
import { EMPTY_TEXT, TABLE_LOADING_TEXT } from '../constants/uiState'

const orders = ref([])
const loading = ref(false)
const route = useRoute()
const router = useRouter()
const detailVisible = ref(false)
const currentOrder = ref(null)
const timeline = ref([])
const advancingFromDetail = ref(false)
const savingProcess = ref(false)
const createDialogVisible = ref(false)
const creating = ref(false)
const quickIntakeVisible = ref(false)
const creatingQuick = ref(false)
const customerLoading = ref(false)
const customerOptions = ref([])
const customerVehicles = ref([])
const vehicleBrandOptions = ref([])
const vehicleModelOptionsByBrand = ref({})
const intakeMode = ref('existing')
const { pageError, clearPageError, setPageError } = createPageFeedbackState()
const selectedOrderIds = ref([])
const pinnedOrderIds = ref([])
const pendingOpenOrderId = ref('')
const pendingResumeStatus = ref('')
const pendingHealthSaved = ref(false)
const latestHealthRecord = ref(null)
const savingDelivery = ref(false)
const savingAdvanced = ref(false)
const addingService = ref(false)
const savingServiceEdit = ref(false)
const generatingQuote = ref(false)
const publishingQuote = ref(false)
const confirmingQuote = ref(false)
const loadingKnowledge = ref(false)
const knowledgeDialogVisible = ref(false)
const knowledgePreviewVisible = ref(false)
const knowledgePreviewUrl = ref('')
const knowledgePreviewTitle = ref('')
const knowledgePreviewDocUrl = ref('')
const knowledgePreviewPage = ref('')
const knowledgePreviewPageInput = ref('')
const knowledgePreviewRecentPages = ref([])
const knowledgePreviewContextPages = ref([])
const knowledgePreviewContextItems = ref([])
const serviceEditVisible = ref(false)
const assistantLoading = ref(false)
const assistantExecuting = ref(false)
const assistantPrompt = ref('')
const assistantReply = ref(null)
const assistantActionPreview = ref(null)
const applyingPackageId = ref(null)
const servicePlan = reactive({
  catalog_model: null,
  vehicle: null,
  standard_items: [],
  service_packages: [],
  selected_items: [],
  totals: { parts_total: 0, labor_total: 0, grand_total: 0 },
  quote_summary: { active_version: null, latest: null, active: null, versions: [] },
  workflow_checks: { checkpoints: [], gates: {} }
})
const appSettings = reactive(createAppSettingsState())
const knowledgeDocuments = ref([])
const manualProcedures = ref([])
const serviceEditForm = reactive({
  id: null,
  service_name: '',
  parts_total: 0,
  labor_price: 0,
  suggested_price: 0,
  notes: ''
})

const processForm = reactive({ symptom_draft: '', symptom_confirmed: '', quick_check: { odometer_km: null, battery_voltage: null, tire_front_psi: null, tire_rear_psi: null, engine_noise_note: '' } })
const deliveryForm = reactive({
  explained_to_customer: false,
  returned_old_parts: false,
  next_service_notified: false,
  payment_confirmed: false,
  payment_method: '',
  payment_amount: null,
  notes: ''
})
const advancedForm = reactive({
  assigned_technician: '',
  service_bay: '',
  priority: 'normal',
  promised_at: '',
  estimated_finish_at: '',
  is_rework: false,
  is_urgent: false,
  qc_owner: '',
  internal_notes: ''
})
const filters = reactive({ status: '', customer_id: '', plate: '' })
const pagination = reactive({ page: 1, size: 20, total: 0 })
const statusCounts = ref({})
const simpleMode = ref(true)
const createForm = reactive({ customer_id: '', vehicle_plate: '', description: '' })
const newCustomer = reactive({ name: '', phone: '', email: '', vehicle_plate: '', make: '', model: '', catalog_model_id: null, year: new Date().getFullYear(), engine_code: '', vin: '' })
const quickStatusesLite = [{ key: '', label: '全部' }, { key: 'draft', label: '草稿' }, { key: 'confirmed', label: '已接车' }, { key: 'diagnosing', label: '症状+检测' }, { key: 'quoted', label: '待施工' }, { key: 'in_progress', label: '施工中' }, { key: 'ready', label: '待交付' }, { key: 'done', label: '已完成' }]
const secondaryPanels = ref([])
const fallbackComplaintTemplates = [
  '常规保养，检查机油与机滤',
  '前刹车异响，顺便做安全检查',
  '更换机油机滤，检查链条状态',
  '发动机启动异常，需要检查',
  '车辆跑偏，检查轮胎与减震',
  '更换刹车油并检查制动手感',
  '检查电瓶状态与充电系统',
  '洗护后做一次整车体检'
]
const quickComplaintTemplates = computed(() => {
  const items = Array.isArray(appSettings.common_complaint_phrases) ? appSettings.common_complaint_phrases : []
  return items.length ? items : fallbackComplaintTemplates
})
const normalizedStoreName = computed(() => String(appSettings.store_name || '').trim() || '机车博士')
const orderVehicleTip = computed(() => `这里展示的是 ${normalizedStoreName.value} 当前这张工单的实际到店车辆；标准车型、标准项目和标准资料来源于主数据中心的标准车型库。`)
const servicePlanSourceText = computed(() => `以下标准项目、标准套餐和标准资料，均来自 ${normalizedStoreName.value} 主数据中心中的标准车型库。`)
const activeStatus = ref('')
const orderWorkflowSteps = [
  { key: 'intake', index: '01', title: '接车建档', desc: '快速接车，确认客户、车辆和本次来店原因。', statuses: ['draft'] },
  { key: 'checkin', index: '02', title: '主诉与快检', desc: '记录客户原话、确认症状，补里程、电压和胎压。', statuses: ['confirmed', 'diagnosing'] },
  { key: 'quote', index: '03', title: '选项目与报价', desc: '加入工单项目，生成并发布有效报价版本。', statuses: ['quoted'] },
  { key: 'repair', index: '04', title: '施工执行', desc: '按已确认项目施工，必要时调整项目顺序、备注和金额。', statuses: ['in_progress'] },
  { key: 'health', index: '05', title: '完工体检', desc: '施工完成后先做整车体检，确认最终状态后再交付。', statuses: ['ready'] },
  { key: 'delivery', index: '06', title: '交车归档', desc: '填写交车确认、打印或保存单据，最后完成工单。', statuses: ['done'] }
]
const workflowStatusOrder = ['draft', 'confirmed', 'diagnosing', 'quoted', 'in_progress', 'ready', 'done']
const getStatusType = (state) => ({ draft: 'info', confirmed: 'warning', diagnosing: 'warning', quoted: 'primary', in_progress: 'primary', ready: 'success', done: 'success', cancel: 'danger' }[state] || '')
const statusLabel = (state) => ({ draft: '草稿', confirmed: '已接车', diagnosing: '症状登记+快速检测', quoted: '待施工', in_progress: '施工中', ready: '待交付', done: '已完成', cancel: '已取消' }[state] || state)
const nextStatus = (status) => ({ draft: 'confirmed', confirmed: 'quoted', diagnosing: 'quoted', quoted: 'in_progress', in_progress: 'ready', ready: 'done' }[status] || '')
const currentStepTitle = computed(() => {
  const state = currentOrder.value?.status || ''
  return ({
    draft: '先完成接车登记',
    confirmed: '补齐症状确认与快速检测',
    diagnosing: '确认检测结果后进入待施工',
    quoted: '准备开工并安排工位',
    in_progress: '施工完成后先做整车体检',
    ready: '确认体检已记录后再交付打印',
    done: '该工单已完成归档'
  }[state] || '按实际业务继续推进')
})
const currentStepHint = computed(() => {
  const state = currentOrder.value?.status || ''
  return ({
    draft: '适合前台快速记录客户原话、车牌和基础故障现象，确认无误后再正式接车。',
    confirmed: '这一步建议技师补齐里程、电压、胎压和异响备注，避免后面重复回填。',
    diagnosing: '如果症状和检测已经明确，可以直接进入待施工，不必把流程拉得太长。',
    quoted: '报价确认后就可以安排施工，优先处理已经等待较久的车辆。',
    in_progress: '施工结束后不要直接交车，先去做整车体检并把最新数据留档，再推进到待交付。',
    ready: '交车前请确认已经完成整车体检记录，最终打印的交付单会读取最新体检信息。',
    done: '此时以查阅、打印和历史追踪为主，不再承担主要录入。'
  }[state] || '按照门店实际流程继续处理。')
})
const statusCount = (key) => !key ? Object.values(statusCounts.value).reduce((sum, val) => sum + Number(val || 0), 0) : Number(statusCounts.value[key] || 0)
const urgentQueueCount = computed(() => (orders.value || []).filter((row) => row?.is_urgent || row?.is_rework || row?.priority === 'high').length)
const readyQueueCount = computed(() => (orders.value || []).filter((row) => row?.status === 'ready').length)
const inProgressQueueCount = computed(() => (orders.value || []).filter((row) => row?.status === 'in_progress').length)
const todayCreatedCount = computed(() => {
  const today = new Date().toLocaleDateString('sv-SE')
  return (orders.value || []).filter((row) => {
    const raw = String(row?.created_at || '')
    return raw.startsWith(today)
  }).length
})
const priorityLabel = (value) => ({
  normal: '普通',
  high: '优先',
  urgent: '加急'
}[value] || '普通')
const rowActionLabel = (row) => {
  const status = row?.status || ''
  if (status === 'draft') return '先完成接车建档'
  if (status === 'confirmed' || status === 'diagnosing') return '补快检并确认症状'
  if (status === 'quoted') return '先确认报价再施工'
  if (status === 'in_progress') return '完工后记得做体检'
  if (status === 'ready') return '先交车确认再完成'
  if (status === 'done') return '已归档，可打印查阅'
  return '按流程继续推进'
}
const rowActionHint = (row) => {
  if (row?.is_urgent) return '加急工单，建议优先处理'
  if (row?.is_rework) return '返修工单，建议先核对历史记录'
  if (row?.priority === 'high') return '优先级较高，建议尽快安排'
  if (row?.assigned_technician || row?.service_bay) return `${row?.assigned_technician || '已安排技师'} ${row?.service_bay ? `· ${row.service_bay}` : ''}`.trim()
  return '双击可直接进入工单工作台'
}
const orderRowClassName = ({ row }) => {
  if (row?.is_urgent) return 'order-row-urgent'
  if (row?.is_rework) return 'order-row-rework'
  if (row?.status === 'ready') return 'order-row-ready'
  return ''
}
const assistantSourceTagPattern = /\[(手册原文|结构化提炼|经验\/推断)\]/g
const sourceTypeLabel = (value) => ({
  customer: '客户档案',
  vehicle: '车辆档案',
  work_order: '当前工单',
  health_record: '最近体检',
  recent_work_order: '相关工单',
  knowledge: '知识库',
  vehicle_catalog_model: '车型目录'
}[String(value || '').trim()] || '参考来源')
const sourceTagTone = (tag) => ({
  '手册原文': 'primary',
  '结构化提炼': 'success',
  '经验/推断': 'warning'
}[String(tag || '').trim()] || 'info')
const normalizeAssistantLine = (text) => String(text || '').replace(/\s+/g, ' ').replace(/^[\d\.\)\(、\-\s]+/, '').trim()
const parseAssistantLine = (text) => {
  const raw = String(text || '').trim()
  if (!raw) return null
  const matches = [...raw.matchAll(assistantSourceTagPattern)]
  const lastTag = matches.length ? matches[matches.length - 1][1] : ''
  return {
    text: raw.replace(assistantSourceTagPattern, '').trim(),
    tag: lastTag
  }
}
const assistantFormattedSections = computed(() => {
  const response = String(assistantReply.value?.response || '').trim()
  if (!response) return []
  const sections = []
  let current = {
    key: 'summary',
    title: '关键结论/快查参数',
    description: '先看能直接下手的值和判断',
    lines: []
  }
  const pushCurrent = () => {
    if (current.lines.length) sections.push(current)
  }
  const mapHeader = (line) => {
    if (line.includes('关键结论') || line.includes('快查参数')) return ['summary', '关键结论/快查参数', '先看能直接下手的值和判断']
    if (line.includes('施工步骤') || line.includes('可执行步骤')) return ['steps', '施工步骤', '尽量按手册顺序执行']
    if (line.includes('风险与缺口') || line.includes('风险提示')) return ['risks', '风险与缺口', '缺值、冲突项和复核提醒']
    return null
  }
  response.split('\n').forEach((line) => {
    const compact = normalizeAssistantLine(line)
    if (!compact) return
    const header = mapHeader(compact)
    if (header) {
      pushCurrent()
      current = {
        key: header[0],
        title: header[1],
        description: header[2],
        lines: []
      }
      return
    }
    const parsed = parseAssistantLine(compact)
    if (parsed?.text) current.lines.push(parsed)
  })
  pushCurrent()
  return sections
})
const assistantSourceSummary = computed(() => {
  const sources = Array.isArray(assistantReply.value?.sources) ? assistantReply.value.sources : []
  const pages = []
  const pageSeen = new Set()
  const items = []
  sources.forEach((item) => {
    if (!item || typeof item !== 'object') return
    const row = {
      type: String(item.type || '').trim(),
      label: String(item.label || '').trim(),
      summary: String(item.summary || '').trim(),
      file_url: String(item.file_url || '').trim()
    }
    if (row.label || row.summary) items.push(row)
    ;(Array.isArray(item.pages) ? item.pages : []).forEach((page) => {
      const normalized = String(page || '').trim()
      if (!normalized || pageSeen.has(normalized)) return
      pageSeen.add(normalized)
      pages.push(normalized)
    })
  })
  return {
    pages,
    items: items.slice(0, 6)
  }
})
const preferredKnowledgeDocument = computed(() => {
  const docs = Array.isArray(knowledgeDocuments.value) ? knowledgeDocuments.value : []
  const score = (doc) => {
    const fileName = String(doc?.file_name || '').toLowerCase()
    const title = String(doc?.title || '').toLowerCase()
    const category = String(doc?.category || '').toLowerCase()
    let total = 0
    if (fileName.endsWith('.pdf')) total += 5
    if (title.includes('手册') || title.includes('manual')) total += 3
    if (category.includes('手册') || category.includes('manual')) total += 2
    return total
  }
  return [...docs].sort((a, b) => score(b) - score(a))[0] || null
})
const loadVehicleBrandOptions = async () => {
  try {
    const rows = await request.get('/mp/catalog/vehicle-models/brands', { params: { active_only: true } })
    vehicleBrandOptions.value = Array.isArray(rows)
      ? rows.map((item) => String(item || '').trim()).filter(Boolean).sort((a, b) => a.localeCompare(b, 'zh-CN'))
      : []
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
const onQuickBrandChange = async () => {
  await loadVehicleModelsByBrand(newCustomer.make)
  const currentOptions = getVehicleModelOptions(newCustomer.make)
  const selected = currentOptions.find((item) => item.id === newCustomer.catalog_model_id)
  if (!selected) {
    newCustomer.catalog_model_id = null
    newCustomer.model = ''
  }
}
const onQuickModelSelect = (modelId) => {
  const selected = getVehicleModelOptions(newCustomer.make).find((item) => item.id === modelId)
  if (!selected) return
  newCustomer.catalog_model_id = selected.id
  newCustomer.make = selected.brand
  newCustomer.model = selected.model_name
  const nowYear = new Date().getFullYear()
  const safeFrom = Number(selected.year_from || nowYear)
  const safeTo = Number(selected.year_to || nowYear)
  newCustomer.year = Math.min(Math.max(nowYear, safeFrom), safeTo)
  if (!newCustomer.engine_code && selected.default_engine_code) newCustomer.engine_code = selected.default_engine_code
}
const loadStatusCounts = async () => { const res = await request.get('/mp/dashboard/summary'); statusCounts.value = res?.orders?.status_counts || {} }
const applyRouteQuery = async () => {
  const qs = route.query || {}
  filters.status = typeof qs.status === 'string' ? qs.status : ''
  filters.plate = typeof qs.plate === 'string' ? qs.plate : ''
  filters.customer_id = typeof qs.customer_id === 'string' ? qs.customer_id : ''
  pendingOpenOrderId.value = typeof qs.order_id === 'string' ? qs.order_id : ''
  pendingResumeStatus.value = typeof qs.resume_status === 'string' ? qs.resume_status : ''
  pendingHealthSaved.value = qs.health_saved === '1'
  activeStatus.value = filters.status || ''
  pagination.page = 1
  if (qs.action === 'create' || qs.action === 'intake') {
    await openQuickIntakeDialog()
    if (qs.action === 'intake') {
      const routeCustomerId = typeof qs.intake_customer_id === 'string' ? qs.intake_customer_id : ''
      const routePlate = typeof qs.intake_plate === 'string' ? qs.intake_plate : ''
      const routeDescription = typeof qs.intake_description === 'string' ? qs.intake_description : ''
      if (routeCustomerId) {
        createForm.customer_id = routeCustomerId
        await loadCustomerVehicles(routeCustomerId)
      }
      if (routePlate) createForm.vehicle_plate = routePlate
      if (routeDescription) createForm.description = routeDescription
    }
    router.replace({
      name: 'orders',
      query: {
        status: filters.status || undefined,
        plate: filters.plate || undefined,
        customer_id: filters.customer_id || undefined
      }
    })
  }
}
const clearRouteAssistQuery = () => {
  router.replace({
    name: 'orders',
    query: {
      status: filters.status || undefined,
      plate: filters.plate || undefined,
      customer_id: filters.customer_id || undefined
    }
  })
}
const handlePendingOrderFocus = async () => {
  if (!pendingOpenOrderId.value) return
  const orderId = pendingOpenOrderId.value
  const resumeStatus = pendingResumeStatus.value
  const showSavedHint = pendingHealthSaved.value
  pendingOpenOrderId.value = ''
  pendingResumeStatus.value = ''
  pendingHealthSaved.value = false
  await openOrderDetail(orderId)
  if (resumeStatus && currentOrder.value?.status !== resumeStatus && nextStatus(currentOrder.value?.status) === resumeStatus) {
    await request.post(`/mp/workorders/${orderId}/status?status=${resumeStatus}`)
    await refresh()
    await openOrderDetail(orderId)
    ElMessage.success(`体检已保存，工单已推进到 ${statusLabel(resumeStatus)}`)
  } else if (showSavedHint) {
    ElMessage.success('整车体检已保存，已回到原工单')
  }
  await clearRouteAssistQuery()
}
const appendComplaintTemplate = (text) => {
  const normalized = String(text || '').trim()
  if (!normalized) return
  const current = String(createForm.description || '').trim()
  if (!current) {
    createForm.description = normalized
    return
  }
  if (current.includes(normalized)) return
  createForm.description = `${current}；${normalized}`
}
const loadLatestHealthRecord = async (customerId, plate) => {
  latestHealthRecord.value = null
  if (!customerId || !plate) return
  try {
    const encodedPlate = encodeURIComponent(String(plate))
    const rows = await request.get(`/mp/workorders/customers/${customerId}/vehicles/${encodedPlate}/health-records`)
    latestHealthRecord.value = Array.isArray(rows) && rows.length ? rows[0] : null
  } catch {
    latestHealthRecord.value = null
  }
}
const resetServicePlan = () => {
  servicePlan.catalog_model = null
  servicePlan.vehicle = null
  servicePlan.standard_items = []
  servicePlan.service_packages = []
  servicePlan.selected_items = []
  servicePlan.totals = { parts_total: 0, labor_total: 0, grand_total: 0 }
  servicePlan.quote_summary = { active_version: null, latest: null, active: null, versions: [] }
  servicePlan.workflow_checks = { checkpoints: [], gates: {} }
}
const loadServicePlan = async (orderId) => {
  if (!orderId) return resetServicePlan()
  try {
    const res = await request.get(`/mp/workorders/${orderId}/service-plan`)
    servicePlan.catalog_model = res?.catalog_model || null
    servicePlan.vehicle = res?.vehicle || null
    servicePlan.standard_items = res?.standard_items || []
    servicePlan.service_packages = res?.service_packages || []
    servicePlan.selected_items = res?.selected_items || []
    servicePlan.totals = res?.totals || { parts_total: 0, labor_total: 0, grand_total: 0 }
    servicePlan.quote_summary = res?.quote_summary || { active_version: null, latest: null, active: null, versions: [] }
    servicePlan.workflow_checks = res?.workflow_checks || { checkpoints: [], gates: {} }
  } catch (error) {
    console.error('loadServicePlan failed', error)
    resetServicePlan()
  }
}
const workflowGateLabels = {
  quoted: '进入已报价',
  in_progress: '进入施工中',
  ready: '进入待交付',
  done: '进入已完成'
}
const quoteStatusLabel = (status) => ({
  draft: '草稿',
  published: '已发布',
  confirmed: '已确认',
  rejected: '已作废'
}[status] || '未生成')
const quoteStatusType = (status) => ({
  draft: 'info',
  published: 'primary',
  confirmed: 'success',
  rejected: 'danger'
}[status] || 'info')
const canPublishLatestQuote = computed(() => servicePlan.quote_summary?.latest?.status === 'draft')
const canConfirmActiveQuote = computed(() => servicePlan.quote_summary?.active?.status === 'published')
const selectedServiceCount = computed(() => Number(servicePlan.selected_items?.length || 0))
const activeQuoteAmountLabel = computed(() => {
  const amount = servicePlan.quote_summary?.active?.amount_total
  if (amount == null || amount === '') return '未生成'
  return String(amount)
})
const selectedServicePreview = computed(() => {
  const names = (servicePlan.selected_items || [])
    .map((item) => String(item?.service_name || '').trim())
    .filter(Boolean)
  if (!names.length) return '还未选择工单项目'
  const preview = names.slice(0, 3).join(' / ')
  return names.length > 3 ? `${preview} 等 ${names.length} 项` : preview
})
const latestHealthMeasuredAtLabel = computed(() => {
  if (!latestHealthRecord.value?.measured_at) return '未记录'
  return String(latestHealthRecord.value.measured_at)
})
const latestHealthSnapshotLabel = computed(() => {
  if (!latestHealthRecord.value) return '施工完成后建议先补整车体检'
  const parts = []
  if (latestHealthRecord.value.odometer_km != null) parts.push(`里程 ${latestHealthRecord.value.odometer_km} km`)
  if (latestHealthRecord.value.battery_voltage != null) parts.push(`电压 ${latestHealthRecord.value.battery_voltage} V`)
  if (latestHealthRecord.value.tire_front_psi != null || latestHealthRecord.value.tire_rear_psi != null) {
    parts.push(`胎压 ${latestHealthRecord.value.tire_front_psi ?? '-'} / ${latestHealthRecord.value.tire_rear_psi ?? '-'}`)
  }
  return parts.join(' · ') || '已记录整车体检'
})
const assistantDefaultPrompts = {
  summary: '请总结当前工单、客户关注点、已选项目、报价状态和下一步建议。',
  risk: '请检查当前工单还缺什么，哪些风险需要现在补齐，并给出优先级最高的下一步动作。',
  delivery: '请基于当前工单、已选项目和最近体检，生成一段可以直接对客户说的交付说明。'
}
const formatQuoteTime = (value) => {
  if (!value) return '-'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString('zh-CN', { hour12: false })
}
const workflowStepState = (item) => {
  const currentStatus = currentOrder.value?.status || 'draft'
  const currentIndex = workflowStatusOrder.indexOf(currentStatus)
  const itemIndices = item.statuses.map((status) => workflowStatusOrder.indexOf(status)).filter((idx) => idx >= 0)
  const itemIndex = itemIndices.length ? Math.min(...itemIndices) : -1
  const isCurrent = item.statuses.includes(currentStatus)
  if (isCurrent) return 'current'
  if (itemIndex >= 0 && itemIndex < currentIndex) return 'done'
  return 'pending'
}
const workflowStepClass = (item) => ({
  current: workflowStepState(item) === 'current',
  done: workflowStepState(item) === 'done',
  pending: workflowStepState(item) === 'pending'
})
const workflowStepTagType = (item) => ({
  current: 'primary',
  done: 'success',
  pending: 'info'
}[workflowStepState(item)] || 'info')
const workflowStepTagLabel = (item) => ({
  current: '当前步骤',
  done: '已完成',
  pending: '待进行'
}[workflowStepState(item)] || '待进行')
const recommendedActionLabel = computed(() => {
  const status = currentOrder.value?.status || ''
  if (status === 'draft' || status === 'confirmed' || status === 'diagnosing') return '保存接车与快检记录'
  if (status === 'quoted' && !servicePlan.quote_summary?.latest?.version) return '先生成报价版本'
  if (status === 'quoted' && servicePlan.quote_summary?.latest?.status === 'draft') return '发布最新报价'
  if (status === 'quoted' && servicePlan.quote_summary?.active?.status === 'published') return '确认当前报价'
  if (status === 'quoted') return '推进到施工中'
  if (status === 'in_progress') return '去做整车体检'
  if (status === 'ready') return '填写交车确认'
  if (status === 'done') return '保存交付单 PDF'
  return ''
})
const deliveryMissingItems = computed(() => {
  const items = []
  if (!deliveryForm.explained_to_customer) items.push('还未勾选“已向客户说明维修/保养内容”')
  if (!deliveryForm.payment_confirmed) items.push('还未确认线下收款')
  if (!deliveryForm.payment_method) items.push('还未选择收款方式')
  if (deliveryForm.payment_amount == null || deliveryForm.payment_amount === '') items.push('还未填写收款金额')
  if (!deliveryForm.notes) items.push('还未填写交车备注')
  return items
})
const firstScreenMissingItems = computed(() => {
  const items = [...(nextTransitionGate.value?.missing || [])]
  const status = currentOrder.value?.status || ''
  if (!processForm.symptom_draft && ['draft', 'confirmed', 'diagnosing'].includes(status)) items.push('还未补接车原话')
  if (!processForm.symptom_confirmed && ['confirmed', 'diagnosing', 'quoted', 'in_progress', 'ready'].includes(status)) items.push('还未补确认症状')
  if (!servicePlan.catalog_model?.id) items.push('还未匹配标准车型')
  return Array.from(new Set(items)).slice(0, 6)
})
const firstScreenActions = computed(() => {
  const actions = []
  const status = currentOrder.value?.status || ''
  if (recommendedActionLabel.value) actions.push({ key: 'recommended', label: recommendedActionLabel.value, type: 'primary' })
  if (['draft', 'confirmed', 'diagnosing'].includes(status)) actions.push({ key: 'save-process', label: '保存接车记录' })
  if (status === 'quoted') actions.push({ key: 'quote', label: '生成报价' })
  if (['in_progress', 'ready'].includes(status)) actions.push({ key: 'health', label: '去做整车体检' })
  if (servicePlan.catalog_model?.id) actions.push({ key: 'knowledge', label: '看标准资料' })
  if (['ready', 'done'].includes(status)) actions.push({ key: 'delivery', label: '交车确认' })
  return actions.slice(0, 5)
})
const nextTransitionGate = computed(() => {
  const target = nextStatus(currentOrder.value?.status || '')
  if (!target) return { ready: true, missing: [] }
  return servicePlan.workflow_checks?.gates?.[target] || { ready: true, missing: [] }
})
const nextTransitionReady = computed(() => Boolean(nextTransitionGate.value?.ready))
const nextTransitionMissingText = computed(() => (nextTransitionGate.value?.missing || []).join('；') || '当前还未满足推进条件')
const resetKnowledgeHub = () => {
  knowledgeDocuments.value = []
  manualProcedures.value = []
}
const resetAssistantState = () => {
  assistantPrompt.value = assistantDefaultPrompts.summary
  assistantReply.value = null
  assistantActionPreview.value = null
}
const fillAssistantPrompt = (mode = 'summary') => {
  assistantPrompt.value = assistantDefaultPrompts[mode] || assistantDefaultPrompts.summary
}
const buildAssistantContext = () => ({
  matched_customer: currentOrder.value?.customer_id
    ? { id: currentOrder.value.customer_id }
    : null,
  matched_vehicle: {
    ...(servicePlan.vehicle || {}),
    plate_number: servicePlan.vehicle?.plate_number || currentOrder.value?.vehicle_plate || '',
    vehicle_plate: servicePlan.vehicle?.vehicle_plate || currentOrder.value?.vehicle_plate || ''
  },
  matched_work_order: {
    ...(currentOrder.value || {}),
    selected_items: servicePlan.selected_items || [],
    quote_summary: servicePlan.quote_summary || {},
    workflow_checks: servicePlan.workflow_checks || {}
  },
  latest_health_record: latestHealthRecord.value || null,
  knowledge_documents: knowledgeDocuments.value || [],
  manual_procedures: manualProcedures.value || []
})
const prefillAssistantAction = (card) => {
  const action = String(card?.action || '').trim()
  const payload = card?.payload || {}
  if (!action) return ElMessage.warning('这个建议动作缺少 action 标识')
  assistantActionPreview.value = {
    label: card?.label || '建议动作',
    action,
    payload
  }
  if (action === 'append_work_order_internal_note') {
    advancedForm.internal_notes = String(payload.note || '').trim()
    ElMessage.success('已把 AI 备注预填到“高级调度信息”里')
    return
  }
  if (action === 'create_quote_draft') {
    ElMessage.success('报价草稿会按 AI 预填参数直接生成，确认后可执行')
    return
  }
  if (action === 'create_work_order') {
    createForm.customer_id = String(payload.customer_id || currentOrder.value?.customer_id || '')
    createForm.vehicle_plate = String(payload.vehicle_plate || currentOrder.value?.vehicle_plate || '')
    createForm.description = String(payload.description || '')
    ElMessage.success('已把 AI 建议预填到手动开单表单')
    createDialogVisible.value = true
    return
  }
  ElMessage.success('AI 预填数据已准备好，可直接执行')
}
const runAssistantActionCard = async (card) => {
  const action = String(card?.action || '').trim()
  if (!action) return ElMessage.warning('这个建议动作暂时无法执行')
  try {
    if (action === 'create_work_order') {
      prefillAssistantAction(card)
      return
    }
    await ElMessageBox.confirm(`将执行“${card?.label || action}”，是否继续？`, 'AI 建议动作确认', {
      type: 'warning',
      confirmButtonText: '确认执行',
      cancelButtonText: '取消'
    })
  } catch {
    return
  }
  assistantExecuting.value = true
  try {
    const result = await request.post('/ai/ops/actions', {
      action,
      payload: card?.payload || {}
    })
    assistantActionPreview.value = {
      label: card?.label || '建议动作',
      action,
      payload: card?.payload || {},
      result
    }
    ElMessage.success(`${card?.label || '动作'}已执行`)
    if (currentOrder.value?.id) {
      await openOrderDetail(currentOrder.value.id)
    } else {
      await refresh()
    }
  } finally {
    assistantExecuting.value = false
  }
}
const askAiAssistantForOrder = async () => {
  if (!currentOrder.value?.id) return ElMessage.warning('请先打开工单详情')
  const message = String(assistantPrompt.value || '').trim()
  if (!message) return ElMessage.warning('请先输入问题或让 AI 帮你做的事')
  assistantLoading.value = true
  try {
    assistantReply.value = await request.post('/ai/assistant/chat', {
      message,
      context: buildAssistantContext()
    }, { timeout: 45000 })
    if (!assistantReply.value?.response) {
      ElMessage.warning('AI 已返回，但暂时没有可展示的文字结果')
    }
  } finally {
    assistantLoading.value = false
  }
}
const loadKnowledgeHub = async (modelId) => {
  resetKnowledgeHub()
  if (!modelId) return
  loadingKnowledge.value = true
  try {
    const [docs, manuals] = await Promise.all([
      request.get(`/mp/knowledge/catalog-models/${modelId}/documents`).catch(() => []),
      request.get(`/mp/knowledge/catalog-models/${modelId}/procedures`).catch(() => [])
    ])
    knowledgeDocuments.value = Array.isArray(docs) ? docs : []
    manualProcedures.value = Array.isArray(manuals) ? manuals : []
  } finally {
    loadingKnowledge.value = false
  }
}
const addServiceSelection = async (row) => {
  if (!currentOrder.value?.id || !row?.template_item_id) return
  addingService.value = true
  try {
    await request.post(`/mp/workorders/${currentOrder.value.id}/service-selections`, { template_item_id: row.template_item_id })
  ElMessage.success('工单项目已加入工单')
    await loadServicePlan(currentOrder.value.id)
  } finally {
    addingService.value = false
  }
}
const applyServicePackage = async (pkg) => {
  if (!currentOrder.value?.id || !pkg?.id) return
  applyingPackageId.value = pkg.id
  try {
    const res = await request.post(`/mp/workorders/${currentOrder.value.id}/service-packages/${pkg.id}/apply`)
    const addedCount = Number(res?.added_count || 0)
    const skippedCount = Number(res?.skipped_count || 0)
    if (addedCount > 0 && skippedCount > 0) {
      ElMessage.success(`${pkg.package_name} 已加入 ${addedCount} 个项目，跳过 ${skippedCount} 个已存在项目`)
    } else if (addedCount > 0) {
      ElMessage.success(`${pkg.package_name} 已加入工单`)
    } else {
      ElMessage.info(`${pkg.package_name} 的项目已全部存在，无需重复加入`)
    }
    await loadServicePlan(currentOrder.value.id)
  } finally {
    applyingPackageId.value = null
  }
}
const editServiceSelection = (row) => {
  serviceEditForm.id = row?.id || null
  serviceEditForm.service_name = row?.service_name || ''
  serviceEditForm.parts_total = Number(row?.parts_total || 0)
  serviceEditForm.labor_price = Number(row?.labor_price || 0)
  serviceEditForm.suggested_price = Number(row?.line_total || row?.suggested_price || 0)
  serviceEditForm.notes = row?.notes || ''
  serviceEditVisible.value = true
}
const submitServiceSelectionEdit = async () => {
  if (!currentOrder.value?.id || !serviceEditForm.id) return
  savingServiceEdit.value = true
  try {
    await request.put(`/mp/workorders/${currentOrder.value.id}/service-selections/${serviceEditForm.id}`, {
      labor_price: Number(serviceEditForm.labor_price || 0),
      suggested_price: Number(serviceEditForm.suggested_price || 0),
      notes: serviceEditForm.notes || ''
    })
  ElMessage.success('工单项目已调整')
    serviceEditVisible.value = false
    await loadServicePlan(currentOrder.value.id)
  } finally {
    savingServiceEdit.value = false
  }
}
const moveServiceSelection = async (index, offset) => {
  if (!currentOrder.value?.id) return
  const rows = [...(servicePlan.selected_items || [])]
  const targetIndex = index + offset
  if (targetIndex < 0 || targetIndex >= rows.length) return
  const [moved] = rows.splice(index, 1)
  rows.splice(targetIndex, 0, moved)
  await request.put(`/mp/workorders/${currentOrder.value.id}/service-selections/reorder`, {
    selection_ids: rows.map((item) => item.id)
  })
  ElMessage.success('项目顺序已更新')
  await loadServicePlan(currentOrder.value.id)
}
const removeServiceSelection = async (row) => {
  if (!currentOrder.value?.id || !row?.id) return
  await request.delete(`/mp/workorders/${currentOrder.value.id}/service-selections/${row.id}`)
  ElMessage.success('已移除工单项目')
  await loadServicePlan(currentOrder.value.id)
}
const generateQuoteFromPlan = async () => {
  if (!currentOrder.value?.id) return
  generatingQuote.value = true
  try {
    const res = await request.post(`/mp/workorders/${currentOrder.value.id}/service-plan/generate-quote`)
    ElMessage.success(`报价版本 V${res?.version || ''} 已生成`)
    await loadServicePlan(currentOrder.value.id)
  } finally {
    generatingQuote.value = false
  }
}
const publishLatestQuote = async () => {
  const latestVersion = servicePlan.quote_summary?.latest?.version
  if (!currentOrder.value?.id || !latestVersion) return
  publishingQuote.value = true
  try {
    await request.post(`/mp/quotes/${currentOrder.value.id}/${latestVersion}/publish`)
    ElMessage.success(`报价版本 V${latestVersion} 已发布`)
    await loadServicePlan(currentOrder.value.id)
  } finally {
    publishingQuote.value = false
  }
}
const confirmActiveQuote = async () => {
  const activeVersion = servicePlan.quote_summary?.active?.version
  if (!currentOrder.value?.id || !activeVersion) return
  confirmingQuote.value = true
  try {
    await request.post(`/mp/quotes/${currentOrder.value.id}/${activeVersion}/confirm`)
    ElMessage.success(`报价版本 V${activeVersion} 已确认`)
    await loadServicePlan(currentOrder.value.id)
  } finally {
    confirmingQuote.value = false
  }
}
const applyActiveQuoteAmount = () => {
  const amount = servicePlan.quote_summary?.active?.amount_total
  if (amount == null) return
  deliveryForm.payment_amount = Number(amount)
  if (!deliveryForm.payment_confirmed) deliveryForm.payment_confirmed = true
  ElMessage.success('已带入当前生效报价金额')
}
const loadAppSettings = async () => {
  try {
    const data = await request.get('/mp/settings')
    applyAppSettings(appSettings, data)
  } catch {
    applyAppSettings(appSettings)
  }
}
const buildDeliverySuggestionText = () => {
  const serviceNames = (servicePlan.selected_items || [])
    .map((item) => String(item?.service_name || '').trim())
    .filter(Boolean)
  const uniqueServiceNames = Array.from(new Set(serviceNames))
  const latestExtra = latestHealthRecord.value?.extra || {}
  const parts = []

  if (uniqueServiceNames.length) {
    parts.push(`本次已完成：${uniqueServiceNames.join('、')}。`)
  }

  const nextKm = latestExtra.next_service_km
  const nextDate = latestExtra.next_service_date
  if (nextKm != null && nextKm !== '') {
    parts.push(`建议在约 ${nextKm} km 时回店复查或保养。`)
  } else if (nextDate) {
    parts.push(`建议在 ${nextDate} 前后安排下次复查或保养。`)
  } else if (uniqueServiceNames.length) {
    parts.push('建议客户按日常使用情况按时回店复查。')
  }

  if (latestHealthRecord.value?.odometer_km != null) {
    parts.push(`本次交车里程记录为 ${latestHealthRecord.value.odometer_km} km。`)
  }

  if (!parts.length && appSettings.default_delivery_note) return appSettings.default_delivery_note
  const merged = parts.join('')
  if (appSettings.default_delivery_note && !merged.includes(appSettings.default_delivery_note)) {
    return `${merged}${appSettings.default_delivery_note}`
  }
  return merged
}
const applyDeliverySuggestions = () => {
  const suggestion = buildDeliverySuggestionText()
  if (!suggestion) {
    ElMessage.warning('当前还没有足够的信息可自动生成交车备注')
    return
  }
  deliveryForm.notes = suggestion
  if (!deliveryForm.explained_to_customer) deliveryForm.explained_to_customer = true
  if (latestHealthRecord.value?.extra?.next_service_km != null || latestHealthRecord.value?.extra?.next_service_date) {
    deliveryForm.next_service_notified = true
  }
  ElMessage.success('已自动生成交车备注')
}
const prepareDeliveryChecklist = () => {
  applyActiveQuoteAmount()
  if (!deliveryForm.notes) applyDeliverySuggestions()
  if (!deliveryForm.explained_to_customer) deliveryForm.explained_to_customer = true
  if (deliveryForm.payment_amount != null && !deliveryForm.payment_confirmed) deliveryForm.payment_confirmed = true
  ElMessage.success('已补齐基础交车信息，请再确认收款方式和旧件返还情况')
}
const runFirstScreenAction = async (key) => {
  if (key === 'recommended') return runRecommendedAction()
  if (key === 'save-process') return saveProcessRecord()
  if (key === 'quote') return generateQuoteFromPlan()
  if (key === 'health') return goToHealthUpdate(currentOrder.value)
  if (key === 'knowledge') return openKnowledgeHub()
  if (key === 'delivery') return prepareDeliveryChecklist()
}
const runRecommendedAction = async () => {
  const status = currentOrder.value?.status || ''
  if (status === 'draft' || status === 'confirmed' || status === 'diagnosing') return saveProcessRecord()
  if (status === 'quoted' && !servicePlan.quote_summary?.latest?.version) return generateQuoteFromPlan()
  if (status === 'quoted' && servicePlan.quote_summary?.latest?.status === 'draft') return publishLatestQuote()
  if (status === 'quoted' && servicePlan.quote_summary?.active?.status === 'published') return confirmActiveQuote()
  if (status === 'quoted') return advanceStatusFromDetail()
  if (status === 'in_progress') return goToHealthUpdate(currentOrder.value)
  if (status === 'ready') {
    prepareDeliveryChecklist()
    return saveDeliveryChecklist()
  }
  if (status === 'done') return saveCurrentDocument('delivery-note')
}
const loadDeliveryChecklist = (orderId) => {
  deliveryForm.explained_to_customer = false
  deliveryForm.returned_old_parts = false
  deliveryForm.next_service_notified = false
  deliveryForm.payment_confirmed = false
  deliveryForm.payment_method = ''
  deliveryForm.payment_amount = null
  deliveryForm.notes = appSettings.default_delivery_note || ''
  if (!orderId) return Promise.resolve()
  return request.get(`/mp/workorders/${orderId}/delivery-checklist`).then((parsed) => {
    deliveryForm.explained_to_customer = Boolean(parsed?.explained_to_customer)
    deliveryForm.returned_old_parts = Boolean(parsed?.returned_old_parts)
    deliveryForm.next_service_notified = Boolean(parsed?.next_service_notified)
    deliveryForm.payment_confirmed = Boolean(parsed?.payment_confirmed)
    deliveryForm.payment_method = parsed?.payment_method || ''
    deliveryForm.payment_amount = parsed?.payment_amount == null ? null : Number(parsed.payment_amount)
    deliveryForm.notes = parsed?.notes || ''
    if ((currentOrder.value?.status === 'ready' || currentOrder.value?.status === 'done') && !parsed?.payment_method && parsed?.payment_amount == null && !parsed?.notes) {
      prepareDeliveryChecklist()
    }
  }).catch(() => {})
}
const loadAdvancedProfile = (orderId) => {
  Object.assign(advancedForm, {
    assigned_technician: '',
    service_bay: '',
    priority: 'normal',
    promised_at: '',
    estimated_finish_at: '',
    is_rework: false,
    is_urgent: false,
    qc_owner: '',
    internal_notes: ''
  })
  if (!orderId) return Promise.resolve()
  return request.get(`/mp/workorders/${orderId}/advanced-profile`).then((parsed) => {
    advancedForm.assigned_technician = parsed?.assigned_technician || ''
    advancedForm.service_bay = parsed?.service_bay || ''
    advancedForm.priority = parsed?.priority || 'normal'
    advancedForm.promised_at = parsed?.promised_at || ''
    advancedForm.estimated_finish_at = parsed?.estimated_finish_at || ''
    advancedForm.is_rework = Boolean(parsed?.is_rework)
    advancedForm.is_urgent = Boolean(parsed?.is_urgent)
    advancedForm.qc_owner = parsed?.qc_owner || ''
    advancedForm.internal_notes = parsed?.internal_notes || ''
  }).catch(() => {})
}
const openKnowledgeHub = async () => {
  const modelId = servicePlan.catalog_model?.id
  if (!modelId) return ElMessage.warning('当前工单还没有匹配到标准车型资料')
  await loadKnowledgeHub(modelId)
  knowledgeDialogVisible.value = true
}
const normalizePreviewPage = (value) => {
  const digits = String(value || '').replace(/[^\d]/g, '')
  const num = Number.parseInt(digits, 10)
  return Number.isFinite(num) && num > 0 ? String(num) : ''
}
const updateKnowledgePreviewUrl = () => {
  if (!knowledgePreviewDocUrl.value) return
  knowledgePreviewUrl.value = buildKnowledgeDocumentUrl(
    { file_url: knowledgePreviewDocUrl.value },
    knowledgePreviewPage.value
  )
}
const pushKnowledgePreviewHistory = (page) => {
  const normalized = normalizePreviewPage(page)
  if (!normalized) return
  const next = [normalized, ...knowledgePreviewRecentPages.value.filter((item) => item !== normalized)]
  knowledgePreviewRecentPages.value = next.slice(0, 8)
}
const openKnowledgePreview = (doc, page = '', title = '', sourceSummary = null) => {
  const fileUrl = String(doc?.file_url || '').trim()
  if (!fileUrl) return ElMessage.warning('这个资料还没有可打开的文件地址')
  knowledgePreviewDocUrl.value = fileUrl.split('#')[0]
  knowledgePreviewPage.value = normalizePreviewPage(page)
  knowledgePreviewPageInput.value = knowledgePreviewPage.value
  knowledgePreviewContextPages.value = Array.isArray(sourceSummary?.pages) ? sourceSummary.pages.slice(0, 8) : []
  knowledgePreviewContextItems.value = Array.isArray(sourceSummary?.items) ? sourceSummary.items.slice(0, 6) : []
  pushKnowledgePreviewHistory(knowledgePreviewPage.value)
  knowledgePreviewTitle.value = title || doc?.title || doc?.file_name || '标准资料预览'
  updateKnowledgePreviewUrl()
  knowledgePreviewVisible.value = true
}
const buildKnowledgeDocumentUrl = (doc, page = '') => {
  const fileUrl = String(doc?.file_url || '').trim()
  if (!fileUrl) return ''
  const normalizedPage = String(page || '').trim()
  if (!normalizedPage) return fileUrl
  return `${fileUrl}${fileUrl.includes('#') ? '&' : '#'}page=${encodeURIComponent(normalizedPage)}`
}
const openKnowledgeDocument = (doc, page = '') => {
  if (!doc?.file_url) return ElMessage.warning('这个资料还没有可打开的文件地址')
  openKnowledgePreview(doc, page)
}
const jumpKnowledgePreviewPage = (delta = 0) => {
  if (!knowledgePreviewDocUrl.value) return
  const current = Number.parseInt(normalizePreviewPage(knowledgePreviewPage.value) || '1', 10)
  const next = Math.max(1, current + Number(delta || 0))
  knowledgePreviewPage.value = String(next)
  knowledgePreviewPageInput.value = knowledgePreviewPage.value
  pushKnowledgePreviewHistory(knowledgePreviewPage.value)
  updateKnowledgePreviewUrl()
}
const goToKnowledgePreviewPage = () => {
  if (!knowledgePreviewDocUrl.value) return
  const normalized = normalizePreviewPage(knowledgePreviewPageInput.value)
  if (!normalized) return ElMessage.warning('请输入有效页码')
  knowledgePreviewPage.value = normalized
  knowledgePreviewPageInput.value = normalized
  pushKnowledgePreviewHistory(knowledgePreviewPage.value)
  updateKnowledgePreviewUrl()
}
const copyKnowledgePreviewLink = async () => {
  if (!knowledgePreviewUrl.value) return ElMessage.warning('当前没有可复制的资料链接')
  try {
    await navigator.clipboard.writeText(knowledgePreviewUrl.value)
    ElMessage.success('当前页链接已复制')
  } catch (error) {
    ElMessage.warning('复制失败，请手动复制浏览器地址')
  }
}
const openAssistantSourceItem = (item) => {
  const fileUrl = String(item?.file_url || '').trim()
  if (fileUrl) {
    openKnowledgePreview({ file_url: fileUrl }, '', item?.label || '参考来源资料', assistantSourceSummary.value)
    return
  }
  if (String(item?.type || '') === 'knowledge') {
    const firstPage = assistantSourceSummary.value.pages[0]
    if (firstPage) {
      openAssistantKnowledgePage(firstPage)
      return
    }
  }
  ElMessage.warning('这个来源当前没有可直接打开的资料链接')
}
const openAssistantKnowledgePage = async (page) => {
  const normalizedPage = String(page || '').trim()
  if (!normalizedPage) return
  if (!knowledgeDocuments.value.length && servicePlan.catalog_model?.id) {
    await loadKnowledgeHub(servicePlan.catalog_model.id)
  }
  const targetDoc = preferredKnowledgeDocument.value
  if (targetDoc?.file_url) {
    openKnowledgePreview(targetDoc, normalizedPage, targetDoc?.title || targetDoc?.file_name || '标准资料预览', assistantSourceSummary.value)
    return
  }
  if (servicePlan.catalog_model?.id) {
    knowledgeDialogVisible.value = true
    ElMessage.warning(`当前没有可直接定位的 PDF，已为你打开标准资料，请手动查看第 ${normalizedPage} 页`)
    return
  }
  ElMessage.warning(`当前没有可打开的标准资料，无法定位到第 ${normalizedPage} 页`)
}
const openCatalogDetailPage = async () => {
  knowledgeDialogVisible.value = false
  await router.push({
    name: 'inventory',
    query: {
      tab: 'vehicles',
      model_id: String(servicePlan.catalog_model?.id || '')
    }
  })
}
const handleKnowledgePreviewHotkey = (event) => {
  if (!knowledgePreviewVisible.value || !knowledgePreviewUrl.value) return
  if (event.key === 'ArrowLeft') {
    event.preventDefault()
    jumpKnowledgePreviewPage(-1)
    return
  }
  if (event.key === 'ArrowRight') {
    event.preventDefault()
    jumpKnowledgePreviewPage(1)
  }
}
const saveDeliveryChecklist = async () => {
  if (!currentOrder.value?.id) return
  savingDelivery.value = true
  try {
    await request.put(`/mp/workorders/${currentOrder.value.id}/delivery-checklist`, {
      explained_to_customer: deliveryForm.explained_to_customer,
      returned_old_parts: deliveryForm.returned_old_parts,
      next_service_notified: deliveryForm.next_service_notified,
      payment_confirmed: deliveryForm.payment_confirmed,
      payment_method: deliveryForm.payment_method || '',
      payment_amount: deliveryForm.payment_amount,
      notes: deliveryForm.notes || ''
    })
    ElMessage.success('交车确认清单已保存')
  } finally {
    savingDelivery.value = false
  }
}
const saveAdvancedProfile = async () => {
  if (!currentOrder.value?.id) return
  savingAdvanced.value = true
  try {
    await request.put(`/mp/workorders/${currentOrder.value.id}/advanced-profile`, {
      assigned_technician: advancedForm.assigned_technician || '',
      service_bay: advancedForm.service_bay || '',
      priority: advancedForm.priority || 'normal',
      promised_at: advancedForm.promised_at || null,
      estimated_finish_at: advancedForm.estimated_finish_at || null,
      is_rework: advancedForm.is_rework,
      is_urgent: advancedForm.is_urgent,
      qc_owner: advancedForm.qc_owner || '',
      internal_notes: advancedForm.internal_notes || ''
    })
    ElMessage.success('高级调度信息已保存')
  } finally {
    savingAdvanced.value = false
  }
}
const refresh = async () => {
  loading.value = true
  try {
    const res = await request.get('/mp/workorders/list/page', { params: { page: pagination.page, size: pagination.size, status: filters.status || '', customer_id: filters.customer_id || '', plate: filters.plate || '' } })
    clearPageError()
    const rows = res.items || []
    const pinned = rows.filter((row) => pinnedOrderIds.value.includes(row.id))
    const normal = rows.filter((row) => !pinnedOrderIds.value.includes(row.id))
    orders.value = [...pinned, ...normal]
    pagination.total = res.total || 0
    await loadStatusCounts()
    await handlePendingOrderFocus()
  } catch (error) {
    setPageError('加载工单中心失败，请稍后重试', error)
    ElMessage.error(error?.message || '加载工单中心失败')
  } finally { loading.value = false }
}
const resetFilters = () => { filters.status = ''; filters.customer_id = ''; filters.plate = ''; activeStatus.value = ''; pagination.page = 1; router.replace({ query: {} }) }
const switchStatus = (status) => { activeStatus.value = status; filters.status = status; pagination.page = 1; router.replace({ query: { ...route.query, status: filters.status || undefined } }) }
const onOrderSelectionChange = (rows) => { selectedOrderIds.value = (rows || []).map((row) => row.id) }
const onOrderRowDblClick = (row) => viewDetail(row)
const onOrderMoreCommand = async (command) => {
  if (command === 'manual-create') return openCreateDialog()
  if (command === 'batch-pin') { pinnedOrderIds.value = Array.from(new Set([...pinnedOrderIds.value, ...selectedOrderIds.value])); ElMessage.success(`已置顶 ${selectedOrderIds.value.length} 条工单`); return refresh() }
  if (command === 'clear-pin') { pinnedOrderIds.value = []; ElMessage.success('已清空置顶工单'); return refresh() }
  if (command === 'batch-delete') return confirmBatchDeleteOrders()
}
const onOrderRowMoreCommand = async (row, command) => {
  if (!row) return
  if (command.startsWith('print-')) return printDocument(row, command.replace('print-', ''))
  if (command.startsWith('save-')) return saveDocument(row, command.replace('save-', ''))
}
const onDetailMoreCommand = async (command) => {
  if (!currentOrder.value) return
  if (command === 'copy-id') return copyOrderId()
  if (command === 'refresh-timeline') return loadTimeline()
  if (command.startsWith('print-')) return printCurrentDocument(command.replace('print-', ''))
  if (command.startsWith('save-')) return saveCurrentDocument(command.replace('save-', ''))
}
const confirmBatchDeleteOrders = async () => {
  if (!selectedOrderIds.value.length) return
  try { await ElMessageBox.confirm(`将删除选中的 ${selectedOrderIds.value.length} 条工单，此操作不可恢复。是否继续？`, '风险操作确认', { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消' }) } catch { return }
  const count = selectedOrderIds.value.length
  const res = await request.post('/mp/workorders/batch-delete', { order_ids: [...selectedOrderIds.value] })
  const failed = Number(res?.failed || 0)
  selectedOrderIds.value = []
  if (failed > 0) ElMessage.warning(`批量删除完成，成功 ${count - failed} 条，失败 ${failed} 条`)
  else ElMessage.success(`已删除 ${count} 条工单`)
  await refresh()
}
const fillProcessForm = (record = null) => {
  const quick = record?.quick_check || {}
  processForm.symptom_draft = record?.symptom_draft || ''
  processForm.symptom_confirmed = record?.symptom_confirmed || ''
  processForm.quick_check.odometer_km = quick.odometer_km ?? null
  processForm.quick_check.battery_voltage = quick.battery_voltage ?? null
  processForm.quick_check.tire_front_psi = quick.tire_front_psi ?? null
  processForm.quick_check.tire_rear_psi = quick.tire_rear_psi ?? null
  processForm.quick_check.engine_noise_note = quick.engine_noise_note || ''
}
const openOrderDetail = async (orderId) => {
  const detail = await request.get(`/mp/workorders/${orderId}`)
  const data = detail?.data || {}
  currentOrder.value = { id: detail?.id || orderId, status: detail?.status || '', vehicle_plate: data?.vehicle_plate || '', customer_id: data?.customer_id || '', description: data?.description || '', created_at: data?.odoo?.create_date || data?.created_at || '' }
  resetAssistantState()
  fillProcessForm(data?.process_record || null)
  await loadLatestHealthRecord(currentOrder.value.customer_id, currentOrder.value.vehicle_plate)
  await loadServicePlan(currentOrder.value.id)
  await loadKnowledgeHub(servicePlan.catalog_model?.id)
  await loadAdvancedProfile(currentOrder.value.id)
  await loadDeliveryChecklist(currentOrder.value.id)
  secondaryPanels.value = []
  detailVisible.value = true
  await loadTimeline()
}
const viewDetail = (row) => openOrderDetail(row?.id || row)
const saveProcessRecord = async () => {
  if (!currentOrder.value?.id) return
  savingProcess.value = true
  try {
    await request.put(`/mp/workorders/${currentOrder.value.id}/process-record`, { symptom_draft: processForm.symptom_draft || null, symptom_confirmed: processForm.symptom_confirmed || null, quick_check: { odometer_km: processForm.quick_check.odometer_km == null ? null : Number(processForm.quick_check.odometer_km), battery_voltage: processForm.quick_check.battery_voltage == null ? null : Number(processForm.quick_check.battery_voltage), tire_front_psi: processForm.quick_check.tire_front_psi == null ? null : Number(processForm.quick_check.tire_front_psi), tire_rear_psi: processForm.quick_check.tire_rear_psi == null ? null : Number(processForm.quick_check.tire_rear_psi), engine_noise_note: processForm.quick_check.engine_noise_note || '' } })
    if (processForm.symptom_draft) currentOrder.value.description = processForm.symptom_draft
    ElMessage.success('症状与检测记录已保存')
    await refresh()
  } finally { savingProcess.value = false }
}
const loadTimeline = async () => { if (!currentOrder.value?.id) return; try { timeline.value = await request.get(`/mp/workorders/${currentOrder.value.id}/timeline`) || [] } catch { timeline.value = [] } }
const renderPrintableHtml = (rawHtml) => {
  const printScript = `\n<script>window.addEventListener('load', function () { setTimeout(function () { window.print() }, 200) })<\/script>`
  if (typeof rawHtml !== 'string') return ''
  return rawHtml.includes('</body>') ? rawHtml.replace('</body>', `${printScript}</body>`) : `${rawHtml}${printScript}`
}
const buildDocumentFileName = (row, docType) => {
  const plate = String(row?.vehicle_plate || '未命名车辆').replace(/[\\/:*?"<>|]+/g, '-')
  const orderId = String(row?.id || 'unknown').slice(0, 8)
  return `${plate}-${documentLabel(docType)}-${orderId}`
}
const fetchDocumentHtml = async (row, docType = 'work-order') => (
  request.get(`/mp/workorders/${row.id}/documents/${docType}`, { responseType: 'text', headers: { Accept: 'text/html' } })
)
const documentLabel = (docType) => ({
  'work-order': '维修工单',
  quote: '报价单',
  'pick-list': '配件领料单',
  'delivery-note': '交付单'
}[docType] || '单据')
const printDocument = async (row, docType = 'work-order') => {
  const html = await fetchDocumentHtml(row, docType)
  const win = window.open('', '_blank')
  if (!win) return ElMessage.warning(`浏览器拦截了弹窗，请允许弹窗后重试打印${documentLabel(docType)}`)
  win.document.open(); win.document.write(renderPrintableHtml(html)); win.document.close()
}
const saveDocument = async (row, docType = 'work-order') => {
  const blob = await request.get(`/mp/workorders/${row.id}/documents/${docType}/pdf`, {
    responseType: 'blob',
    headers: { Accept: 'application/pdf' }
  })
  const fileName = `${buildDocumentFileName(row, docType)}.pdf`
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = fileName
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
  ElMessage.success(`${documentLabel(docType)}已下载为 PDF`)
}
const printOrder = async (row) => printDocument(row, 'work-order')
const printCurrentDocument = async (docType = 'work-order') => { if (currentOrder.value) await printDocument(currentOrder.value, docType) }
const saveCurrentDocument = async (docType = 'work-order') => { if (currentOrder.value) await saveDocument(currentOrder.value, docType) }
const goToHealthUpdate = async (row, silent = false) => {
  const customerId = String(row?.customer_id || '').trim(); const plate = String(row?.vehicle_plate || '').trim()
  if (!customerId || !plate) { if (!silent) ElMessage.warning('无法自动定位客户或车辆，请到客户中心手动更新体检表'); return }
  await router.push({
    name: 'customers',
    query: {
      action: 'health_update',
      customer_id: customerId,
      plate,
      return_to: 'orders',
      order_id: String(row?.id || ''),
      resume_status: row?.status === 'in_progress' ? 'ready' : undefined
    }
  })
}
const advanceStatus = async (row) => {
  const target = nextStatus(row.status)
  if (!target) return
  if (row.status === 'in_progress' && target === 'ready') {
    try {
      await ElMessageBox.alert(
        '施工完成后，请先做整车体检并记录，确认车辆最终状态后再推进到待交付。',
        '完工体检提醒',
        { confirmButtonText: '去做整车体检', type: 'warning' }
      )
    } catch {}
    await goToHealthUpdate(row)
    return
  }
  await request.post(`/mp/workorders/${row.id}/status?status=${target}`)
  ElMessage.success(`已进入 ${statusLabel(target)}`)
  if (target === 'ready') {
    let shouldUpdateHealth = false
    try {
      await ElMessageBox.confirm('已进入待交付，是否现在更新体检表后直接打印工单？', '待交付提醒', { type: 'info', confirmButtonText: '更新体检并打印', cancelButtonText: '仅打印工单', distinguishCancelAndClose: true })
      shouldUpdateHealth = true
    } catch (action) {
      if (action === 'close') { await refresh(); return }
    }
    await printOrder(row)
    if (shouldUpdateHealth) await goToHealthUpdate(row)
  }
  if (target === 'done') await goToHealthUpdate(row, true)
  await refresh()
}
const advanceStatusFromDetail = async () => { if (!currentOrder.value) return; advancingFromDetail.value = true; try { await advanceStatus(currentOrder.value); await openOrderDetail(currentOrder.value.id) } finally { advancingFromDetail.value = false } }
const copyOrderId = async () => { try { await navigator.clipboard.writeText(currentOrder.value?.id || ''); ElMessage.success('工单号已复制') } catch { ElMessage.warning('复制失败，请手动复制') } }
const searchCustomers = async (keyword) => { customerLoading.value = true; try { customerOptions.value = await request.get('/mp/workorders/customers/search', { params: { query: keyword || '', limit: 20 } }) || [] } finally { customerLoading.value = false } }
const loadCustomerVehicles = async (partnerId) => { try { customerVehicles.value = await request.get(`/mp/workorders/customers/${partnerId}/vehicles`) || []; if (customerVehicles.value.length && !createForm.vehicle_plate) createForm.vehicle_plate = customerVehicles.value[0].license_plate } catch { customerVehicles.value = [] } }
const openCreateDialog = async () => { createForm.customer_id = ''; createForm.vehicle_plate = ''; createForm.description = ''; customerVehicles.value = []; createDialogVisible.value = true; await searchCustomers('') }
const resetQuickIntake = () => { intakeMode.value = 'existing'; createForm.customer_id = ''; createForm.vehicle_plate = ''; createForm.description = ''; customerVehicles.value = []; newCustomer.name = ''; newCustomer.phone = ''; newCustomer.email = ''; newCustomer.vehicle_plate = ''; newCustomer.make = ''; newCustomer.model = ''; newCustomer.catalog_model_id = null; newCustomer.year = new Date().getFullYear(); newCustomer.engine_code = ''; newCustomer.vin = '' }
const openQuickIntakeDialog = async () => { resetQuickIntake(); quickIntakeVisible.value = true; await searchCustomers('') }
const finalizeCreatedOrder = async (result, successMessage, dialogKey) => {
  const createdId = String(result?.id || '').trim()
  ElMessage.success(successMessage)
  if (dialogKey === 'quick') {
    quickIntakeVisible.value = false
    resetQuickIntake()
  } else {
    createDialogVisible.value = false
    createForm.customer_id = ''
    createForm.vehicle_plate = ''
    createForm.description = ''
    customerVehicles.value = []
  }
  await refresh()
  if (createdId) await openOrderDetail(createdId)
}
const submitCreateOrder = async () => {
  if (!createForm.customer_id || !createForm.vehicle_plate || !createForm.description) return ElMessage.warning('请填写客户、车牌和客户主诉')
  creating.value = true
  try {
    const result = await request.post('/mp/workorders/', createForm)
    await finalizeCreatedOrder(result, '工单已创建，已打开工单详情', 'create')
  } finally { creating.value = false }
}
const submitQuickIntake = async () => {
  if (!createForm.description) return ElMessage.warning('请填写客户主诉')
  creatingQuick.value = true
  try {
    let customerId = createForm.customer_id; let plate = createForm.vehicle_plate
    if (intakeMode.value === 'new') {
      if (!newCustomer.name || !newCustomer.vehicle_plate || !newCustomer.make || !newCustomer.model || !newCustomer.year) return ElMessage.warning('请至少填写新客户姓名、车牌、品牌、车型和年份')
      const newCustomerResp = await request.post('/mp/workorders/customers', { name: newCustomer.name, phone: newCustomer.phone || null, email: newCustomer.email || null, vehicles: [{ catalog_model_id: newCustomer.catalog_model_id || null, license_plate: newCustomer.vehicle_plate, make: newCustomer.make, model: newCustomer.model, year: newCustomer.year, engine_code: newCustomer.engine_code || null, vin: newCustomer.vin || null }] })
      customerId = String(newCustomerResp.id); plate = newCustomer.vehicle_plate
    } else if (!customerId || !plate) return ElMessage.warning('请选择客户和车牌')
    const result = await request.post('/mp/workorders/', { customer_id: customerId, vehicle_plate: plate, description: createForm.description })
    await finalizeCreatedOrder(result, '接车建单完成，已打开工单详情', 'quick')
  } finally { creatingQuick.value = false }
}
const handleStoreChanged = async () => {
  vehicleModelOptionsByBrand.value = {}
  await loadAppSettings()
  await loadVehicleBrandOptions()
  await loadStatusCounts()
  await refresh()
}
onMounted(async () => {
  await applyRouteQuery()
  await loadAppSettings()
  window.addEventListener('drmoto-store-changed', handleStoreChanged)
  window.addEventListener('keydown', handleKnowledgePreviewHotkey)
  await loadVehicleBrandOptions()
  await loadStatusCounts()
  await refresh()
})
onBeforeUnmount(() => {
  window.removeEventListener('drmoto-store-changed', handleStoreChanged)
  window.removeEventListener('keydown', handleKnowledgePreviewHotkey)
})
watch(() => route.query, async () => { await applyRouteQuery(); await refresh() })
watch(() => createForm.customer_id, async (partnerId) => { if (!partnerId) { customerVehicles.value = []; createForm.vehicle_plate = ''; return } await loadCustomerVehicles(partnerId) })
watch(() => knowledgePreviewVisible.value, (visible) => {
  if (visible) return
  knowledgePreviewUrl.value = ''
  knowledgePreviewDocUrl.value = ''
  knowledgePreviewTitle.value = ''
  knowledgePreviewPage.value = ''
  knowledgePreviewPageInput.value = ''
  knowledgePreviewRecentPages.value = []
  knowledgePreviewContextPages.value = []
  knowledgePreviewContextItems.value = []
})
</script>

<style scoped>
.order-list { display: flex; flex-direction: column; gap: 16px; }
.status-tabs { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; }
.status-tab { cursor: pointer; }
.toolbar { margin-bottom: 16px; display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.queue-strip { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; }
.queue-pill { padding: 7px 12px; border-radius: 999px; background: #f6f9fd; border: 1px solid #dce8f3; color: #486284; font-size: 12px; }
.queue-hint-cell { display: flex; flex-direction: column; gap: 4px; }
.queue-hint-cell strong { color: #17324a; font-size: 13px; }
.queue-hint-cell span { color: #64748b; font-size: 12px; line-height: 1.6; }
.pagination-wrap { margin-top: 14px; display: flex; justify-content: flex-end; }
.drawer-actions { display: flex; gap: 8px; margin: 14px 0 0; flex-wrap: wrap; }
.detail-hero { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; padding: 14px 16px; border-radius: 14px; background: linear-gradient(135deg, #f7faff, #eef4ff); border: 1px solid #dbe5f6; }
.detail-hero-title { font-size: 24px; font-weight: 700; color: #162033; }
.detail-hero-subtitle { margin-top: 6px; color: #6f7b91; font-size: 13px; line-height: 1.6; }
.detail-hero-status { display: flex; flex-direction: column; align-items: flex-end; gap: 8px; }
.next-chip { padding: 6px 12px; border-radius: 999px; background: #fff; border: 1px solid #d8e2f2; color: #486284; font-size: 12px; }
.hero-readiness { display: flex; gap: 6px; flex-wrap: wrap; justify-content: flex-end; }
.hero-readiness-chip { padding: 5px 10px; border-radius: 999px; font-size: 12px; border: 1px solid #d8e2f2; background: #fff; color: #486284; }
.hero-readiness-chip.ok { background: #ecfdf5; border-color: #b7ebc6; color: #17603d; }
.hero-readiness-chip.warn { background: #fff7ed; border-color: #f5d0a8; color: #9a4d00; }
.workflow-overview-card { margin-top: 14px; border: 1px solid #dbe7f2; border-radius: 14px; padding: 14px; background: linear-gradient(180deg, #fbfdff 0%, #f5f9fd 100%); display: grid; gap: 14px; }
.compact-workflow-card { gap: 10px; }
.workflow-overview-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; flex-wrap: wrap; }
.workflow-overview-head p { margin: 6px 0 0; color: #64748b; font-size: 12px; line-height: 1.6; }
.workflow-overview-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }
.workflow-overview-step { border: 1px solid #dbe7f2; border-radius: 12px; padding: 10px 12px; background: #fff; display: grid; gap: 8px; transition: all 0.2s ease; }
.workflow-overview-step.current { border-color: #2a8bc9; box-shadow: 0 8px 20px rgba(42, 139, 201, 0.12); background: #f4fbff; }
.workflow-overview-step.done { border-color: #cfe7da; background: #f6fcf8; }
.workflow-overview-step.pending { opacity: 0.92; }
.workflow-step-top { display: flex; align-items: center; gap: 10px; }
.workflow-step-index { width: 32px; height: 32px; border-radius: 10px; background: #eaf4fb; color: #17608f; display: inline-flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700; }
.workflow-overview-step.done .workflow-step-index { background: #e8f7ee; color: #177245; }
.workflow-overview-step p { margin: 0; color: #64748b; font-size: 12px; line-height: 1.7; }
.workflow-step-foot { display: flex; justify-content: flex-end; }
.focus-summary { margin-top: 14px; border: 1px solid #dbe7f2; border-radius: 16px; padding: 16px; background: linear-gradient(180deg, #f5fbff 0%, #ffffff 100%); display: grid; gap: 14px; }
.focus-summary-main { display: grid; gap: 10px; }
.focus-summary-complaint { font-size: 16px; font-weight: 600; color: #17324a; line-height: 1.7; }
.focus-summary-tags { display: flex; flex-wrap: wrap; gap: 8px; }
.focus-summary-tags span { padding: 6px 10px; border-radius: 999px; background: rgba(255, 255, 255, 0.9); border: 1px solid #d7e7f4; color: #42637b; font-size: 12px; }
.focus-summary-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
.focus-kpi-card { border: 1px solid #dce8f3; border-radius: 12px; padding: 12px; background: #fff; display: flex; flex-direction: column; gap: 8px; min-height: 108px; }
.focus-kpi-card span { color: #688097; font-size: 12px; }
.focus-kpi-card strong { color: #113049; font-size: 20px; line-height: 1.4; }
.focus-kpi-card small { color: #64748b; font-size: 12px; line-height: 1.6; }
.focus-action-zone { display: grid; grid-template-columns: 1.2fr 0.8fr; gap: 12px; }
.compact-focus-zone { align-items: start; }
.focus-missing-card, .focus-shortcuts-card { border: 1px solid #dce8f3; border-radius: 12px; padding: 12px; background: #fff; display: grid; gap: 10px; }
.focus-missing-inline { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.inline-label { color: #64748b; font-size: 12px; white-space: nowrap; }
.focus-missing-list { display: flex; flex-wrap: wrap; gap: 8px; }
.focus-missing-list span { padding: 6px 10px; border-radius: 999px; background: #fff7ec; border: 1px solid #f3d1a8; color: #8a5720; font-size: 12px; }
.focus-ready-copy { color: #5e7f72; font-size: 12px; line-height: 1.7; }
.focus-shortcuts { display: flex; flex-wrap: wrap; gap: 8px; }
.compact-shortcuts { justify-content: flex-end; }
.detail-grid { display: grid; grid-template-columns: 1.1fr 0.9fr; gap: 14px; margin-top: 14px; }
.detail-panel { border: 1px solid #e2e8f3; border-radius: 14px; padding: 14px; background: #fbfcff; }
.detail-inline-tip { margin-bottom: 10px; color: #6f7b91; font-size: 12px; line-height: 1.7; }
.detail-block { margin-top: 14px; border: 1px solid #e7edf5; border-radius: 14px; padding: 14px; background: #fff; }
.detail-block-compact { background: linear-gradient(180deg, #fbfcff 0%, #ffffff 100%); }
.ai-assistant-block { background: linear-gradient(180deg, #f7fbff 0%, #ffffff 100%); border-color: #d7e4f2; }
.secondary-panels { margin-top: 14px; }
.collapse-inner-block { margin-top: 0; border: none; padding: 0; background: transparent; }
.ai-assistant-shell { display: grid; gap: 14px; }
.ai-assistant-input { display: grid; gap: 12px; }
.ai-assistant-actions { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; flex-wrap: wrap; }
.ai-context-tags { display: flex; gap: 8px; flex-wrap: wrap; }
.ai-context-tags span { padding: 6px 10px; border-radius: 999px; background: #fff; border: 1px solid #d9e5f5; color: #486284; font-size: 12px; }
.ai-assistant-button-row { display: flex; gap: 8px; flex-wrap: wrap; }
.ai-assistant-result { display: grid; gap: 12px; }
.ai-reply-copy { padding: 14px; border-radius: 12px; background: #fff; border: 1px solid #dbe7f2; color: #1f2d3d; line-height: 1.8; white-space: pre-wrap; }
.ai-structured-sections { display: grid; gap: 10px; }
.ai-structured-card { border: 1px solid #dbe7f2; border-radius: 12px; background: linear-gradient(180deg, #fbfdff 0%, #ffffff 100%); padding: 12px; display: grid; gap: 10px; }
.ai-structured-head { display: flex; justify-content: space-between; align-items: baseline; gap: 10px; flex-wrap: wrap; }
.ai-structured-head strong { color: #12344d; }
.ai-structured-head span { color: #6b7f91; font-size: 12px; }
.ai-structured-list { display: grid; gap: 8px; }
.ai-structured-line { display: grid; grid-template-columns: 28px minmax(0, 1fr); gap: 10px; align-items: flex-start; }
.ai-structured-index { width: 28px; height: 28px; border-radius: 999px; background: #edf5ff; color: #2f5d88; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700; }
.ai-structured-copy { display: flex; gap: 8px; align-items: center; justify-content: space-between; flex-wrap: wrap; color: #1f2d3d; line-height: 1.7; }
.ai-source-chip { padding: 4px 8px; border-radius: 999px; font-size: 12px; border: 1px solid transparent; white-space: nowrap; }
.ai-source-chip-primary { background: #eef6ff; border-color: #cfe2fb; color: #24527d; }
.ai-source-chip-success { background: #eefbf3; border-color: #c9e8d4; color: #256145; }
.ai-source-chip-warning { background: #fff6e8; border-color: #f2d3a6; color: #9a5d00; }
.ai-source-chip-info { background: #f4f7fb; border-color: #d8e2ee; color: #52657a; }
.ai-source-panel { border: 1px dashed #c6d9ec; border-radius: 12px; background: #f8fbff; padding: 12px; display: grid; gap: 10px; }
.ai-source-head { display: flex; justify-content: space-between; align-items: baseline; gap: 10px; flex-wrap: wrap; }
.ai-source-head strong { color: #17324a; }
.ai-source-head span { color: #5f7891; font-size: 12px; }
.ai-source-page-list { display: flex; gap: 8px; flex-wrap: wrap; }
.ai-source-page-button { padding: 5px 10px; border-radius: 999px; background: #fff; border: 1px solid #dbe7f2; color: #35546b; font-size: 12px; }
.ai-source-item-list { display: grid; gap: 8px; }
.ai-source-item { border: 1px solid #dbe7f2; border-radius: 10px; background: #fff; padding: 10px; display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; }
.ai-source-item strong { color: #17324a; font-size: 13px; }
.ai-source-item p { margin: 0; color: #64748b; font-size: 12px; line-height: 1.6; }
.ai-suggestion-list { display: flex; gap: 8px; flex-wrap: wrap; }
.ai-suggestion-list span { padding: 6px 10px; border-radius: 999px; background: #eef6ff; border: 1px solid #d5e6fb; color: #2f5d88; font-size: 12px; }
.ai-card-list { display: grid; gap: 10px; }
.ai-card-item { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; border: 1px solid #dbe7f2; border-radius: 12px; background: #fff; padding: 12px; }
.ai-card-item p { margin: 6px 0 0; color: #64748b; font-size: 12px; line-height: 1.7; }
.ai-card-actions { display: flex; gap: 8px; flex-wrap: wrap; }
.ai-debug-box { border: 1px dashed #bdd4eb; border-radius: 12px; background: #f8fbff; padding: 12px; display: grid; gap: 10px; }
.ai-debug-tags { display: flex; gap: 8px; flex-wrap: wrap; }
.ai-debug-tags span { padding: 5px 10px; border-radius: 999px; background: #fff; border: 1px solid #d9e5f5; color: #486284; font-size: 12px; }
.ai-debug-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.ai-debug-grid div { border: 1px solid #dbe7f2; border-radius: 10px; background: #fff; padding: 10px; display: grid; gap: 4px; }
.ai-debug-grid label { color: #6b7f91; font-size: 12px; }
.ai-debug-grid strong { color: #17324a; font-size: 15px; }
.ai-preview-box { border: 1px dashed #bdd4eb; border-radius: 12px; background: #f8fbff; padding: 12px; display: grid; gap: 8px; }
.ai-preview-meta { color: #5a7187; font-size: 12px; }
.ai-preview-box pre { margin: 0; white-space: pre-wrap; word-break: break-word; color: #24384c; font-size: 12px; line-height: 1.7; font-family: Consolas, Monaco, monospace; }
.detail-title { font-weight: 700; margin-bottom: 10px; color: #162033; }
.detail-title-inline { display: flex; align-items: baseline; justify-content: space-between; gap: 10px; flex-wrap: wrap; }
.detail-title-tip { color: #7a8599; font-size: 12px; font-weight: 400; }
.detail-content { background: #f6f8fc; border-radius: 10px; padding: 12px; color: #334155; }
.info-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.info-card { border: 1px solid #e1e8f3; border-radius: 12px; padding: 12px; background: #fff; display: flex; flex-direction: column; gap: 6px; }
.info-card span { font-size: 12px; color: #7a8599; }
.info-card strong { color: #1d273d; }
.collapse-title-wrap { display: flex; flex-direction: column; gap: 4px; line-height: 1.5; padding: 4px 0; }
.collapse-title-wrap span { color: #7a8599; font-size: 12px; }
.advanced-panel { padding-top: 6px; }
.advanced-summary { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }
.advanced-summary span { padding: 6px 10px; border-radius: 999px; background: #f4f8ff; border: 1px solid #d9e5f8; color: #486284; font-size: 12px; }
.advanced-form { padding-top: 4px; }
.advanced-flags { display: flex; gap: 14px; flex-wrap: wrap; }
.intake-summary { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 14px; }
.summary-pill { padding: 7px 12px; border-radius: 999px; background: #f5f8fd; border: 1px solid #dbe4f2; color: #51627d; font-size: 12px; }
.intake-section-title { margin: 6px 0 10px; font-size: 14px; font-weight: 700; color: #162033; }
.intake-hint { margin: -2px 0 12px 120px; color: #7a8599; font-size: 12px; line-height: 1.6; }
.complaint-editor { display: flex; flex-direction: column; gap: 10px; width: 100%; }
.complaint-chips { display: flex; gap: 8px; flex-wrap: wrap; }
.model-editor { display: flex; flex-direction: column; gap: 6px; width: 100%; }
.inspection-workflow { display: flex; flex-direction: column; gap: 12px; }
.inspection-copy strong { color: #1d273d; font-size: 15px; }
.inspection-copy p { margin: 8px 0 0; color: #6f7b91; line-height: 1.7; font-size: 13px; }
.inspection-tags { display: flex; flex-wrap: wrap; gap: 8px; }
.inspection-tags span { padding: 6px 10px; border-radius: 999px; background: #f4f8ff; border: 1px solid #d9e5f8; color: #486284; font-size: 12px; }
.inspection-actions { display: flex; flex-direction: column; align-items: flex-start; gap: 8px; }
.inspection-hint { color: #7a8599; font-size: 12px; line-height: 1.6; }
.delivery-summary { display: flex; flex-direction: column; gap: 12px; }
.delivery-grid { display: grid; grid-template-columns: repeat(4, minmax(120px, 1fr)); gap: 10px; }
.delivery-card { border: 1px solid #e2e8f3; border-radius: 12px; padding: 12px; background: #fbfcff; display: flex; flex-direction: column; gap: 6px; }
.delivery-card span { font-size: 12px; color: #7a8599; }
.delivery-card strong { color: #162033; font-size: 18px; }
.delivery-note { padding: 10px 12px; border-radius: 10px; background: #f8fbff; color: #486284; line-height: 1.7; font-size: 13px; }
.delivery-checklist { display: flex; flex-direction: column; gap: 10px; }
.delivery-missing-card { border: 1px solid #f3d1a8; background: #fff8ee; border-radius: 10px; padding: 10px 12px; display: grid; gap: 8px; }
.delivery-missing-card strong { color: #9a4d00; font-size: 13px; }
.delivery-missing-list { display: flex; flex-wrap: wrap; gap: 8px; }
.delivery-missing-list span { padding: 5px 10px; border-radius: 999px; background: #fff; border: 1px solid #f3d1a8; color: #9a4d00; font-size: 12px; }
.delivery-quote-strip { display: flex; align-items: center; justify-content: space-between; gap: 10px; flex-wrap: wrap; padding: 10px 12px; border: 1px solid #dbe7f2; border-radius: 10px; background: #f8fbff; color: #36546c; font-size: 13px; }
.delivery-quote-actions { display: flex; gap: 8px; flex-wrap: wrap; }
.delivery-form { margin-top: 6px; }
.reminder-box { padding: 2px 2px 0; }
.reminder-box strong { display: block; color: #1d273d; font-size: 15px; }
.reminder-box p { margin: 8px 0 0; color: #6f7b91; line-height: 1.7; font-size: 13px; }
.service-plan-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; margin-bottom: 12px; }
.service-plan-actions { display: flex; gap: 8px; flex-wrap: wrap; justify-content: flex-end; }
.service-plan-head p { margin: 6px 0 0; color: #6f7b91; font-size: 13px; }
.service-plan-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.package-recommend-block { margin-bottom: 14px; display: grid; gap: 10px; }
.package-recommend-list { display: grid; gap: 10px; }
.package-recommend-card { border: 1px solid #dce8f3; border-radius: 12px; background: linear-gradient(180deg, #f9fcff 0%, #ffffff 100%); padding: 12px; display: grid; gap: 10px; }
.package-recommend-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; }
.package-recommend-head p { margin: 6px 0 0; color: #64748b; font-size: 12px; line-height: 1.6; }
.package-recommend-meta { display: flex; flex-wrap: wrap; gap: 10px; color: #4c647b; font-size: 12px; }
.package-recommend-foot { display: flex; justify-content: space-between; align-items: center; gap: 10px; flex-wrap: wrap; }
.package-selection-hint { color: #64748b; font-size: 12px; }
.minor-title { margin-bottom: 8px; font-weight: 700; color: #334155; }
.mini-tags { display: flex; flex-wrap: wrap; gap: 6px; font-size: 12px; color: #64748b; }
.flag-tag { padding: 2px 8px; border-radius: 999px; background: #eef4ff; border: 1px solid #d6e3fb; color: #35548d; }
.flag-tag.warn { background: #fff6e8; border-color: #f3d7a3; color: #a66800; }
.flag-tag.danger { background: #fff0f0; border-color: #f0c0c0; color: #c0392b; }
.selected-service-list { margin-top: 10px; display: flex; flex-direction: column; gap: 8px; }
.selected-service-card { padding: 10px 12px; border: 1px solid #e2e8f3; border-radius: 10px; background: #fbfcff; }
.selected-service-head { display: flex; justify-content: space-between; gap: 8px; align-items: center; }
.selected-service-head span { color: #7a8599; font-size: 12px; }
.selected-service-card p { margin: 6px 0; color: #64748b; font-size: 12px; line-height: 1.7; }
.selected-service-pricing { display: flex; flex-wrap: wrap; gap: 10px; color: #475569; font-size: 12px; }
.selected-service-note { color: #7c5c12; background: #fff8e8; border-radius: 10px; padding: 8px 10px; font-size: 12px; line-height: 1.6; }
.service-plan-total { margin-top: 10px; display: flex; justify-content: flex-end; gap: 14px; color: #475569; }
.service-plan-total strong { color: #0f172a; }
.quote-summary-card { margin-top: 14px; border: 1px solid #dbe7f2; border-radius: 14px; padding: 14px; background: #fff; display: grid; gap: 14px; }
.quote-summary-head { display: flex; justify-content: space-between; gap: 12px; align-items: flex-start; flex-wrap: wrap; }
.quote-summary-head p { margin: 6px 0 0; color: #64748b; font-size: 12px; line-height: 1.6; }
.quote-summary-actions { display: flex; gap: 8px; flex-wrap: wrap; justify-content: flex-end; }
.quote-kpi-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
.quote-kpi-card { border: 1px solid #e2e8f3; border-radius: 12px; padding: 12px; background: #fbfcff; display: flex; flex-direction: column; gap: 6px; }
.quote-kpi-card span { color: #6b7f91; font-size: 12px; }
.quote-kpi-card strong { color: #12344d; font-size: 24px; }
.quote-kpi-card small { color: #64748b; font-size: 12px; }
.quote-version-list { display: grid; gap: 8px; }
.quote-version-item { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; border: 1px solid #e2e8f3; background: #fbfcff; border-radius: 10px; padding: 10px 12px; color: #475569; font-size: 12px; }
.quote-active-flag { color: #0f766e; background: #ecfdf5; border-radius: 999px; padding: 4px 8px; }
.workflow-guard-card { margin-top: 14px; border: 1px solid #dbe7f2; background: linear-gradient(180deg, #fbfdff 0%, #f4f9fd 100%); border-radius: 14px; padding: 14px; display: grid; gap: 14px; }
.workflow-check-list { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
.workflow-check-item { border: 1px solid #d8e5ef; border-radius: 12px; background: #fff; padding: 12px; display: grid; gap: 8px; }
.workflow-check-main { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.workflow-check-item p { margin: 0; color: #637f98; font-size: 12px; line-height: 1.6; }
.workflow-next-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.workflow-next-card { border: 1px dashed #c7d9e8; border-radius: 12px; padding: 12px; background: rgba(255, 255, 255, 0.76); display: grid; gap: 8px; }
.workflow-next-head { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.workflow-missing-list { display: grid; gap: 6px; }
.workflow-missing-list span { color: #8a5720; background: #fff7ec; border-radius: 999px; padding: 6px 10px; font-size: 12px; }
.workflow-ready-copy { margin: 0; color: #5e7f72; font-size: 12px; }
.knowledge-overview { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.knowledge-card { border: 1px solid #e2e8f3; border-radius: 12px; padding: 12px; background: #fbfcff; display: flex; flex-direction: column; gap: 6px; }
.knowledge-card span { font-size: 12px; color: #7a8599; }
.knowledge-card strong { color: #162033; font-size: 22px; }
.knowledge-card p { margin: 0; color: #64748b; font-size: 12px; line-height: 1.7; }
.knowledge-inline-actions { margin-top: 12px; display: flex; align-items: center; justify-content: space-between; gap: 10px; flex-wrap: wrap; }
.knowledge-dialog { display: flex; flex-direction: column; gap: 14px; }
.knowledge-dialog-head { display: flex; justify-content: space-between; gap: 12px; align-items: flex-start; }
.knowledge-dialog-head p { margin: 6px 0 0; color: #6f7b91; font-size: 13px; }
.knowledge-dialog-grid { display: grid; grid-template-columns: 0.95fr 1.05fr; gap: 14px; }
.knowledge-panel { border: 1px solid #e2e8f3; border-radius: 14px; padding: 14px; background: #fbfcff; min-height: 240px; }
.knowledge-preview-shell { width: 100%; height: min(78vh, 960px); border: 1px solid #dbe7f2; border-radius: 12px; background: #f7fbff; overflow: hidden; }
.knowledge-preview-frame { width: 100%; height: 100%; border: none; background: #fff; }
.knowledge-preview-controls { display: inline-flex; align-items: center; gap: 8px; margin-right: 12px; color: #4c647b; font-size: 12px; }
.knowledge-preview-page-input { width: 120px; }
.knowledge-preview-history { display: inline-flex; align-items: center; gap: 6px; margin-right: 12px; color: #5f7891; font-size: 12px; }
.knowledge-preview-hint { display: inline-flex; align-items: center; margin-right: 12px; color: #7a8ea3; font-size: 12px; }
.knowledge-preview-context { margin-top: 12px; border: 1px solid #dbe7f2; border-radius: 12px; background: #f9fbff; padding: 12px; display: grid; gap: 10px; }
.knowledge-preview-context-head { display: flex; justify-content: space-between; gap: 10px; flex-wrap: wrap; }
.knowledge-preview-context-head strong { color: #17324a; }
.knowledge-preview-context-head span { color: #6f849a; font-size: 12px; }
.knowledge-preview-context-list { display: grid; gap: 8px; }
.knowledge-preview-context-item { border: 1px solid #e3ebf5; border-radius: 10px; background: #fff; padding: 10px; }
.knowledge-preview-context-item strong { color: #17324a; font-size: 13px; }
.knowledge-preview-context-item p { margin: 4px 0 0; color: #64748b; font-size: 12px; line-height: 1.6; }
.knowledge-list, .manual-list { display: flex; flex-direction: column; gap: 10px; }
.knowledge-item { display: flex; justify-content: space-between; gap: 10px; align-items: flex-start; padding: 10px 12px; border: 1px solid #e2e8f3; border-radius: 12px; background: #fff; }
.knowledge-item p { margin: 6px 0 0; color: #64748b; font-size: 12px; line-height: 1.6; }
.manual-desc { margin-bottom: 10px; color: #64748b; font-size: 13px; line-height: 1.7; }
.manual-step { padding: 10px 0; border-top: 1px dashed #d7dfeb; }
.manual-step:first-of-type { border-top: none; padding-top: 0; }
.manual-step p { margin: 6px 0; color: #334155; line-height: 1.7; font-size: 13px; }
.manual-meta { display: flex; flex-direction: column; gap: 4px; color: #64748b; font-size: 12px; }
.empty-inline { color: #7a8599; font-size: 13px; line-height: 1.7; }
.timeline-line { display: flex; justify-content: space-between; gap: 8px; }
.timeline-actor { color: #7a8599; }
.service-edit-name { min-height: 32px; display: flex; align-items: center; color: #334155; }
:deep(.order-row-urgent td) { background: #fff5f5 !important; }
:deep(.order-row-rework td) { background: #fff8ec !important; }
:deep(.order-row-ready td) { background: #f5fbf7 !important; }
@media (max-width: 900px) {
  .detail-hero,
  .detail-grid { grid-template-columns: 1fr; display: grid; }
  .detail-hero-status { align-items: flex-start; }
  .hero-readiness { justify-content: flex-start; }
  .workflow-overview-grid { grid-template-columns: 1fr; }
  .info-grid { grid-template-columns: 1fr; }
  .ai-debug-grid { grid-template-columns: 1fr; }
  .ai-structured-line { grid-template-columns: 1fr; }
  .intake-hint { margin-left: 0; }
  .delivery-grid { grid-template-columns: 1fr; }
  .focus-action-zone { grid-template-columns: 1fr; }
  .compact-shortcuts { justify-content: flex-start; }
  .service-plan-grid { grid-template-columns: 1fr; }
  .package-recommend-head,
  .package-recommend-foot { flex-direction: column; align-items: flex-start; }
  .quote-kpi-grid { grid-template-columns: 1fr; }
  .workflow-check-list,
  .workflow-next-grid { grid-template-columns: 1fr; }
  .knowledge-overview { grid-template-columns: 1fr; }
  .knowledge-dialog-grid { grid-template-columns: 1fr; }
  .knowledge-preview-shell { height: 72vh; }
  .knowledge-preview-controls { display: flex; flex-wrap: wrap; margin: 0 0 8px; }
  .knowledge-preview-history { display: flex; flex-wrap: wrap; margin: 0 0 8px; }
  .knowledge-preview-hint { display: flex; margin: 0 0 8px; }
}
</style>
