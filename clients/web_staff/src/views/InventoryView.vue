
<template>
  <div class="inventory-page">
    <div class="card page-head">
      <div>
        <h2>主数据中心</h2>
      <p>{{ inventoryHeadText }}</p>
      </div>
      <el-button type="primary" plain :loading="syncing" @click="syncCatalog">同步车型基础库</el-button>
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
        <el-button text type="primary" @click="retryActiveTabLoad">重新加载当前数据</el-button>
      </template>
    </el-alert>

    <div class="summary-grid">
      <div class="card summary-card"><span>车型数</span><strong>{{ vehiclePager.total }}</strong></div>
      <div class="card summary-card"><span>配件数</span><strong>{{ partPager.total }}</strong></div>
      <div class="card summary-card"><span>品牌数</span><strong>{{ vehicleBrands.length }}</strong></div>
      <div class="card summary-card"><span>标准资料数</span><strong>{{ libraryDocuments.length }}</strong></div>
    </div>

    <div class="quick-workbench">
      <div class="card quick-workbench-card">
        <span>先补标准车型</span>
        <strong>{{ vehiclePager.total }}</strong>
        <p>{{ vehicleWorkbenchText }}</p>
        <el-button text type="primary" @click="focusWorkbench('vehicle-create')">新增标准车型</el-button>
      </div>
      <div class="card quick-workbench-card">
        <span>再补标准配件</span>
        <strong>{{ partPager.total }}</strong>
        <p>{{ partWorkbenchText }}</p>
        <el-button text type="primary" @click="focusWorkbench('part-create')">新增标准配件</el-button>
      </div>
      <div class="card quick-workbench-card">
        <span>待审核资料</span>
        <strong>{{ pendingReviewDocumentCount }}</strong>
        <p>{{ documentWorkbenchText }}</p>
        <el-button text type="primary" @click="focusWorkbench('documents-pending')">去处理资料</el-button>
      </div>
      <div class="card quick-workbench-card">
        <span>识别中</span>
        <strong>{{ processingDocumentCount }}</strong>
        <p>{{ processingWorkbenchText }}</p>
        <el-button text type="primary" @click="focusWorkbench('documents-processing')">查看识别进度</el-button>
      </div>
    </div>

    <div class="card">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="标准车型库" name="vehicle">
          <div class="domain-hint-card">
            <strong>这里维护标准车型</strong>
              <span>{{ vehicleDomainText }}</span>
          </div>
          <div class="toolbar">
            <el-select v-model="vehicleFilters.brand" clearable filterable placeholder="品牌" style="width: 180px" @change="onVehicleBrandChange">
              <el-option v-for="item in vehicleBrands" :key="item" :label="item" :value="item" />
            </el-select>
            <el-select v-model="vehicleFilters.model_name" clearable filterable placeholder="车型" style="width: 220px" @change="loadVehicleModels">
              <el-option v-for="item in vehicleBrandModels" :key="item.id" :label="`${item.model_name} (${item.year_from}-${item.year_to})`" :value="item.model_name" />
            </el-select>
            <el-select v-model="vehicleFilters.category" clearable filterable placeholder="分类" style="width: 160px" @change="loadVehicleModels">
              <el-option v-for="item in vehicleCategories" :key="item" :label="item" :value="item" />
            </el-select>
            <el-input v-model="vehicleFilters.keyword" clearable placeholder="搜索品牌/车型" style="width: 220px" @keyup.enter="loadVehicleModels" />
            <el-button type="primary" @click="loadVehicleModels">查询</el-button>
            <el-button @click="resetVehicleFilters">重置</el-button>
            <el-button type="success" @click="openVehicleDialog()">新增标准车型</el-button>
          </div>

          <el-table :data="vehicleRows" v-loading="vehicleLoading" :element-loading-text="TABLE_LOADING_TEXT" :empty-text="EMPTY_TEXT.vehicleCatalog" style="width: 100%" @row-dblclick="openVehicleDetail">
            <el-table-column prop="brand" label="品牌" width="140" />
            <el-table-column prop="model_name" label="车型" min-width="180" />
            <el-table-column label="年份" width="140">
              <template #default="scope">{{ scope.row.year_from }} - {{ scope.row.year_to }}</template>
            </el-table-column>
            <el-table-column prop="category" label="分类" width="120" />
            <el-table-column prop="displacement_cc" label="排量(cc)" width="110" />
            <el-table-column label="操作" width="210">
              <template #default="scope">
                <el-button link type="primary" @click="openVehicleDetail(scope.row)">标准项目</el-button>
                <el-button link type="primary" @click="openVehicleDialog(scope.row)">编辑</el-button>
                <el-button link type="danger" @click="removeVehicle(scope.row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="标准配件库" name="parts">
          <div class="domain-hint-card">
            <strong>这里维护标准配件</strong>
            <span>{{ partDomainText }}</span>
          </div>
          <div class="toolbar">
            <el-select v-model="partFilters.category" clearable filterable placeholder="分类" style="width: 180px" @change="loadParts">
              <el-option v-for="item in partCategories" :key="item" :label="item" :value="item" />
            </el-select>
            <el-input v-model="partFilters.keyword" clearable placeholder="搜索料号/名称/品牌" style="width: 260px" @keyup.enter="loadParts" />
            <el-button type="primary" @click="loadParts">查询</el-button>
            <el-button @click="resetPartFilters">重置</el-button>
            <el-button type="success" @click="openPartDialog()">新增标准配件</el-button>
          </div>

          <el-table :data="partRows" v-loading="partLoading" :element-loading-text="TABLE_LOADING_TEXT" :empty-text="EMPTY_TEXT.parts" style="width: 100%" @row-dblclick="openPartDialog">
            <el-table-column prop="part_no" label="料号" width="160" />
            <el-table-column prop="name" label="名称" min-width="180" />
            <el-table-column prop="brand" label="品牌" width="120" />
            <el-table-column prop="category" label="分类" width="120" />
            <el-table-column prop="sale_price" label="售价" width="100" />
            <el-table-column prop="stock_qty" label="库存" width="100" />
            <el-table-column label="操作" width="160">
              <template #default="scope">
                <el-button link type="primary" @click="openPartDialog(scope.row)">编辑</el-button>
                <el-button link type="danger" @click="removePart(scope.row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="标准资料库" name="documents">
          <div class="domain-hint-card">
            <strong>这里维护标准资料</strong>
            <span>{{ documentDomainText }}</span>
          </div>
          <div class="library-quick-filters">
            <el-button :type="libraryQuickFilter === 'all' ? 'primary' : 'default'" plain @click="applyLibraryQuickFilter('all')">全部资料</el-button>
            <el-button :type="libraryQuickFilter === 'pending_review' ? 'primary' : 'default'" plain @click="applyLibraryQuickFilter('pending_review')">待审核</el-button>
            <el-button :type="libraryQuickFilter === 'ready' ? 'primary' : 'default'" plain @click="applyLibraryQuickFilter('ready')">可入库</el-button>
            <el-button :type="libraryQuickFilter === 'needs_fix' ? 'primary' : 'default'" plain @click="applyLibraryQuickFilter('needs_fix')">需补录</el-button>
            <el-button :type="libraryQuickFilter === 'processing' ? 'primary' : 'default'" plain @click="applyLibraryQuickFilter('processing')">识别中</el-button>
          </div>
          <div class="library-focus-strip">
            <div class="library-focus-item">
              <span>待审核</span>
              <strong>{{ pendingReviewDocumentCount }}</strong>
              <small>优先确认车型和审核状态</small>
            </div>
            <div class="library-focus-item">
              <span>识别中</span>
              <strong>{{ processingDocumentCount }}</strong>
              <small>系统会自动刷新进度</small>
            </div>
            <div class="library-focus-item">
              <span>可直接入库</span>
              <strong>{{ readyDocumentCount }}</strong>
              <small>已确认车型且模板覆盖达标</small>
            </div>
            <div class="library-focus-actions">
              <el-button plain @click="applyLibraryQuickFilter('pending_review')">只看待审核</el-button>
              <el-button plain @click="applyLibraryQuickFilter('processing')">只看识别中</el-button>
              <el-button type="primary" plain @click="applyLibraryQuickFilter('ready')">只看可入库</el-button>
            </div>
          </div>
          <div class="toolbar">
            <el-select v-model="libraryFilters.category" clearable filterable placeholder="资料分类" style="width: 180px" @change="loadLibraryDocuments">
              <el-option v-for="item in documentCategories" :key="item" :label="item" :value="item" />
            </el-select>
            <el-select v-model="libraryFilters.parse_status" clearable placeholder="识别状态" style="width: 160px" @change="loadLibraryDocuments">
              <el-option label="待解析" value="pending" />
              <el-option label="排队中" value="queued" />
              <el-option label="解析中" value="processing" />
              <el-option label="已完成" value="completed" />
              <el-option label="失败" value="failed" />
            </el-select>
            <el-select v-model="libraryFilters.review_status" clearable placeholder="审核状态" style="width: 160px" @change="loadLibraryDocuments">
              <el-option label="待审核" value="pending_review" />
              <el-option label="已确认" value="confirmed" />
              <el-option label="需补录" value="needs_fix" />
            </el-select>
            <el-input v-model="libraryFilters.keyword" clearable placeholder="搜索资料名/文件名/车型" style="width: 280px" @keyup.enter="loadLibraryDocuments" />
            <el-button type="primary" @click="loadLibraryDocuments">查询</el-button>
            <el-button @click="resetLibraryFilters">重置</el-button>
          </div>

          <el-table :data="libraryDocuments" v-loading="libraryLoading" :element-loading-text="TABLE_LOADING_TEXT" :empty-text="EMPTY_TEXT.documents" style="width: 100%" @row-dblclick="openLibraryRow">
            <el-table-column prop="title" label="资料名称" min-width="220" show-overflow-tooltip />
            <el-table-column prop="category" label="分类" width="120" />
            <el-table-column prop="file_name" label="文件名" min-width="200" show-overflow-tooltip />
            <el-table-column label="关联车型" min-width="180">
              <template #default="scope">
                <span v-if="scope.row.model_info">{{ scope.row.model_info.brand }} {{ scope.row.model_info.model_name }}</span>
                <span v-else class="muted">未关联</span>
              </template>
            </el-table-column>
            <el-table-column label="识别总览" min-width="220">
              <template #default="scope">
                <div class="list-overview-cell">
                  <strong>{{ libraryOverview(scope.row).modelLabel }}</strong>
                  <span>{{ `模板 ${libraryOverview(scope.row).templateCompletion}` }}</span>
                  <span>{{ libraryOverview(scope.row).specSummary }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="识别状态" width="140">
              <template #default="scope">
                <el-tag :type="parseStatusTagType(scope.row.latest_parse_job?.status)">
                  {{ parseStatusText(scope.row.latest_parse_job?.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="审核状态" width="140">
              <template #default="scope">
                <el-tag :type="reviewStatusTagType(scope.row.review_status)">
                  {{ reviewStatusText(scope.row.review_status) }}
                </el-tag>
              </template>
            </el-table-column>
                <el-table-column label="标准车型确认" width="140">
              <template #default="scope">
                <el-tag :type="catalogConfirmationStatusTagType(scope.row.catalog_confirmation_status)">
                  {{ catalogConfirmationStatusText(scope.row.catalog_confirmation_status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="识别进度" min-width="220">
              <template #default="scope">
                <span v-if="scope.row.latest_parse_job">
                  <template v-if="['queued', 'processing'].includes(scope.row.latest_parse_job.status)">
                    <div class="parse-progress-inline">
                      <el-progress
                        :percentage="Number(scope.row.latest_parse_job.progress_percent || 0)"
                        :stroke-width="8"
                        :show-text="false"
                      />
                      <span class="muted">{{ formatParseProgress(scope.row.latest_parse_job) }}</span>
                    </div>
                  </template>
                  <template v-else>
                    {{ Number(scope.row.latest_parse_job.page_count || 0) }} 页 /
                    {{ Number(scope.row.latest_parse_job.extracted_specs || 0) }} 条规格 /
                    {{ Number(scope.row.latest_parse_job.summary_json?.procedures?.length || 0) }} 条步骤
                  </template>
                </span>
                <span v-else class="muted">尚未解析</span>
              </template>
            </el-table-column>
            <el-table-column label="入库准备度" min-width="220">
              <template #default="scope">
                <div class="parse-chip-list">
                  <el-tag
                    v-for="item in libraryReadiness(scope.row)"
                    :key="item.key"
                    :type="item.ready ? 'success' : 'warning'"
                    effect="plain"
                  >
                    {{ `${item.label}${item.ready ? ' 可执行' : ' 待补充'}` }}
                  </el-tag>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="notes" label="备注" min-width="220" show-overflow-tooltip />
            <el-table-column label="操作" width="320">
              <template #default="scope">
                <el-button link type="primary" @click="openKnowledgeDocument(scope.row)">打开</el-button>
                <el-button link type="primary" :loading="parsingDocumentId === scope.row.id" @click="parseKnowledgeDocument(scope.row)">解析</el-button>
                <el-button link @click="openParseResultDialog(scope.row)" :disabled="!scope.row.latest_parse_job">结果</el-button>
                <el-button
                  link
                  v-if="scope.row.latest_parse_job && ['failed', 'processing', 'queued'].includes(scope.row.latest_parse_job.status)"
                  @click="retryParseJob(scope.row)"
                >
                  重试
                </el-button>
                <el-dropdown trigger="click" @command="(command) => applyReviewStatus(scope.row, command)">
                  <el-button link>审核</el-button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item command="confirmed">标记已确认</el-dropdown-item>
                      <el-dropdown-item command="needs_fix">标记需补录</el-dropdown-item>
                      <el-dropdown-item command="pending_review">恢复待审核</el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
                <el-button link @click="openLinkedModel(scope.row)" :disabled="!scope.row.model_info">车型</el-button>
                <el-button link type="danger" @click="removeKnowledgeDocument(scope.row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </div>

    <el-dialog v-model="vehicleDialogVisible" :title="vehicleForm.id ? '编辑车型' : '新增车型'" width="720px">
      <el-form :model="vehicleForm" label-width="110px">
        <el-row :gutter="12">
          <el-col :span="12"><el-form-item label="品牌"><el-input v-model="vehicleForm.brand" maxlength="80" show-word-limit /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="车型"><el-input v-model="vehicleForm.model_name" maxlength="120" show-word-limit /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12"><el-form-item label="起始年份"><el-input-number v-model="vehicleForm.year_from" :min="1950" :max="2100" style="width: 100%" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="截止年份"><el-input-number v-model="vehicleForm.year_to" :min="1950" :max="2100" style="width: 100%" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12"><el-form-item label="排量(cc)"><el-input-number v-model="vehicleForm.displacement_cc" :min="0" :max="2500" style="width: 100%" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="分类"><el-input v-model="vehicleForm.category" maxlength="80" show-word-limit /></el-form-item></el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="vehicleDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="vehicleSaving" @click="saveVehicle">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="partDialogVisible" :title="partForm.id ? '编辑配件' : '新增配件'" width="760px">
      <el-form :model="partForm" label-width="110px">
        <el-row :gutter="12">
          <el-col :span="12"><el-form-item label="料号"><el-input v-model="partForm.part_no" maxlength="80" show-word-limit /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="名称"><el-input v-model="partForm.name" maxlength="120" show-word-limit /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12"><el-form-item label="品牌"><el-input v-model="partForm.brand" maxlength="80" show-word-limit /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="分类"><el-input v-model="partForm.category" maxlength="80" show-word-limit /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="6"><el-form-item label="单位"><el-input v-model="partForm.unit" maxlength="20" show-word-limit /></el-form-item></el-col>
          <el-col :span="6"><el-form-item label="最低库存"><el-input-number v-model="partForm.min_stock" :min="0" style="width: 100%" /></el-form-item></el-col>
          <el-col :span="6"><el-form-item label="售价"><el-input-number v-model="partForm.sale_price" :min="0" :precision="2" style="width: 100%" /></el-form-item></el-col>
          <el-col :span="6"><el-form-item label="成本"><el-input-number v-model="partForm.cost_price" :min="0" :precision="2" style="width: 100%" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12"><el-form-item label="库存数量"><el-input-number v-model="partForm.stock_qty" :min="0" :precision="1" style="width: 100%" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="供应商"><el-input v-model="partForm.supplier_name" maxlength="120" show-word-limit /></el-form-item></el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="partDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="partSaving" @click="savePart">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="vehicleDetailVisible" :title="vehicleDetailTitle" width="1100px" destroy-on-close>
      <div class="detail-head">
        <div>
          <strong>{{ vehicleDetail.brand }} {{ vehicleDetail.model_name }}</strong>
          <p>{{ vehicleDetail.year_from }} - {{ vehicleDetail.year_to }} 年</p>
        </div>
        <div class="head-actions">
          <el-button :loading="servicePartSyncing" @click="syncServiceItemPartsFromManual()">按手册同步配件</el-button>
          <el-button @click="openManualProcedureDialog()">新增标准手册条目</el-button>
          <el-button type="primary" @click="openServiceItemDialog()">新增标准项目</el-button>
        </div>
      </div>
      <el-table :data="serviceItems" v-loading="serviceLoading" :element-loading-text="TABLE_LOADING_TEXT" :empty-text="EMPTY_TEXT.serviceItems" style="width: 100%">
        <el-table-column prop="service_name" label="标准项目" min-width="180" />
        <el-table-column prop="service_code" label="编码" width="120" />
        <el-table-column prop="labor_hours" label="工时(h)" width="90" />
        <el-table-column prop="labor_price" label="工时费" width="100" />
        <el-table-column prop="suggested_price" label="建议售价" width="110" />
        <el-table-column label="所需配件" min-width="220">
          <template #default="scope">
            <div class="part-tags">
              <el-tooltip
                v-for="part in scope.row.required_parts || []"
                :key="`${scope.row.id}-${part.part_no || part.part_name}`"
                placement="top"
                :content="part.notes || `${part.part_no || part.part_name}`"
              >
                <el-tag size="small" effect="plain">
                  {{ part.part_name }} x{{ part.qty }}
                </el-tag>
              </el-tooltip>
              <span v-if="!(scope.row.required_parts || []).length" class="muted">未配置</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="repair_method" label="方法说明" min-width="240" show-overflow-tooltip />
        <el-table-column label="操作" width="290">
          <template #default="scope">
            <el-button link type="primary" @click="openServiceManualLocator(scope.row)">手册定位</el-button>
            <el-button link type="primary" :loading="servicePartSyncingItemId === scope.row.id" @click="syncServiceItemPartsFromManual(scope.row)">同步配件</el-button>
            <el-button link type="primary" @click="openServiceItemDialog(scope.row)">编辑</el-button>
            <el-button link type="danger" @click="removeServiceItem(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="manual-section">
        <div class="manual-head doc-head">
          <div>
            <strong>标准服务套餐</strong>
            <p>把常见保养和维修组合成菜单式套餐，前台报价、顾问推荐和后续工单都可以直接复用。</p>
          </div>
          <div class="head-actions">
            <el-button @click="seedServicePackages">生成推荐套餐</el-button>
            <el-button type="primary" @click="openServicePackageDialog()">新增套餐</el-button>
          </div>
        </div>
        <el-table :data="servicePackages" v-loading="servicePackageLoading" :element-loading-text="TABLE_LOADING_TEXT" :empty-text="EMPTY_TEXT.servicePackages" style="width: 100%">
          <el-table-column prop="package_name" label="套餐名称" min-width="180" />
          <el-table-column prop="package_code" label="编码" width="140" />
          <el-table-column label="建议周期" min-width="160">
            <template #default="scope">
              <span>{{ packageIntervalText(scope.row) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="包含项目" min-width="260">
            <template #default="scope">
              <div class="part-tags">
                <el-tag v-for="item in scope.row.items || []" :key="`${scope.row.id}-${item.id}`" size="small" effect="plain">
                  {{ item.service_item?.service_name || `项目#${item.template_item_id}` }}
                </el-tag>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="套餐汇总" min-width="220">
            <template #default="scope">
              <div class="list-overview-cell">
                <span>{{ `工时 ${Number(scope.row.labor_hours_total || 0).toFixed(1)}h` }}</span>
                <span>{{ `工时费 ¥${Number(scope.row.labor_price_total || 0).toFixed(2)}` }}</span>
                <span>{{ `配件 ¥${Number(scope.row.parts_price_total || 0).toFixed(2)}` }}</span>
                <strong>{{ `建议售价 ¥${Number(scope.row.suggested_price_total || 0).toFixed(2)}` }}</strong>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="description" label="说明" min-width="220" show-overflow-tooltip />
          <el-table-column label="操作" width="160">
            <template #default="scope">
              <el-button link type="primary" @click="openServicePackageDialog(scope.row)">编辑</el-button>
              <el-button link type="danger" @click="removeServicePackage(scope.row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="manual-section">
        <div class="manual-head doc-head">
          <div>
                  <strong>标准车型参数</strong>
            <p>沉淀这台车的标准扭矩、油液、胎压、电气等核心规格，后续工单、资料审核和维修导师都复用这里。</p>
          </div>
          <el-button @click="openVehicleSpecDialog()">新增参数</el-button>
        </div>
        <el-table :data="vehicleSpecs" :empty-text="EMPTY_TEXT.vehicleSpecs" style="width: 100%">
          <el-table-column prop="spec_label" label="参数名称" min-width="180" />
          <el-table-column prop="spec_type" label="类型" width="120" />
          <el-table-column label="参数值" width="160">
            <template #default="scope">{{ `${scope.row.spec_value || '-'} ${scope.row.spec_unit || ''}` }}</template>
          </el-table-column>
          <el-table-column prop="source_page" label="来源页码" width="100" />
          <el-table-column prop="source_text" label="来源文本" min-width="220" show-overflow-tooltip />
          <el-table-column label="状态" width="110">
            <template #default="scope">
              <el-tag :type="itemReviewTagType(scope.row.review_status)" effect="plain">{{ itemReviewText(scope.row.review_status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="160">
            <template #default="scope">
              <el-button link type="primary" @click="openVehicleSpecDialog(scope.row)">编辑</el-button>
              <el-button link type="danger" @click="removeVehicleSpec(scope.row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="manual-section">
        <div class="manual-head doc-head">
          <div>
            <strong>标准手册分段</strong>
            <p>按维修手册目录自动切成章节 PDF，并同步生成对应的维修条目。以后看不懂文字时，可以直接打开对应章节 PDF 快速定位。</p>
          </div>
        </div>
        <div class="segment-toolbar">
          <div class="segment-toolbar__filters">
            <el-select v-model="segmentFilters.chapter" clearable placeholder="全部章节" style="width: 140px">
              <el-option v-for="item in segmentChapterOptions" :key="item" :label="item" :value="item" />
            </el-select>
            <el-input v-model="segmentFilters.keyword" clearable placeholder="搜索章节名 / 步骤" style="width: 260px" />
          </div>
          <div class="segment-toolbar__summary">
            共 {{ knowledgeSegments.length }} 条，当前显示 {{ filteredKnowledgeSegments.length }} 条
          </div>
        </div>
        <el-table :data="filteredKnowledgeSegments" :empty-text="EMPTY_TEXT.knowledgeSegments" style="width: 100%">
          <el-table-column prop="chapter_no" label="章节号" width="90" />
          <el-table-column prop="title" label="章节名称" min-width="220" />
          <el-table-column label="页码范围" width="120">
            <template #default="scope">{{ `${scope.row.start_page || '-'} - ${scope.row.end_page || '-'}` }}</template>
          </el-table-column>
          <el-table-column label="分段 PDF" min-width="180">
            <template #default="scope">
              <span v-if="scope.row.segment_document">{{ scope.row.segment_document.title }}</span>
              <span v-else class="muted">未生成</span>
            </template>
          </el-table-column>
          <el-table-column label="对应维修条目" min-width="180">
            <template #default="scope">
              <span v-if="scope.row.procedure">{{ scope.row.procedure.name }}</span>
              <span v-else class="muted">未生成</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="220">
            <template #default="scope">
              <el-button link type="primary" @click="scope.row.segment_document && openKnowledgeDocument(scope.row.segment_document)" :disabled="!scope.row.segment_document">打开 PDF</el-button>
              <el-button link type="primary" @click="scope.row.procedure && openManualStepDialog(scope.row.procedure)" :disabled="!scope.row.procedure">查看步骤</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="manual-section">
        <div class="manual-head">
          <div>
            <strong>标准作业卡</strong>
            <p>把原厂手册里的标准步骤、扭矩、工具和注意事项整理成标准作业卡，后面可进一步接到工单和打印单据里。</p>
          </div>
        </div>
        <el-table :data="manualProcedures" :empty-text="EMPTY_TEXT.manualCards" style="width: 100%">
          <el-table-column prop="name" label="作业卡名称" min-width="220" />
          <el-table-column prop="description" label="说明" min-width="260" show-overflow-tooltip />
          <el-table-column prop="steps_count" label="步骤数" width="90" />
          <el-table-column label="操作" width="220">
            <template #default="scope">
              <el-button link type="primary" @click="openManualProcedureDialog(scope.row)">编辑</el-button>
              <el-button link type="primary" @click="openManualStepDialog(scope.row)">步骤</el-button>
              <el-button link type="danger" @click="removeManualProcedure(scope.row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="manual-section">
        <div class="manual-head doc-head">
          <div>
            <strong>标准资料</strong>
            <p>上传并审核和这个标准车型相关的 PDF 维修手册、扭矩表、线路图、保养标准，后面工单和技师查询都从这里引用。</p>
          </div>
          <el-button @click="openDocumentDialog()">上传标准资料</el-button>
        </div>
        <el-table :data="knowledgeDocuments" style="width: 100%">
          <el-table-column prop="title" label="资料名称" min-width="220" />
          <el-table-column prop="category" label="分类" width="120" />
          <el-table-column prop="file_name" label="文件名" min-width="200" show-overflow-tooltip />
          <el-table-column label="审核状态" width="120">
            <template #default="scope">
              <el-tag :type="reviewStatusTagType(scope.row.review_status)">
                {{ reviewStatusText(scope.row.review_status) }}
              </el-tag>
            </template>
          </el-table-column>
                    <el-table-column label="标准车型确认" width="120">
            <template #default="scope">
              <el-tag :type="catalogConfirmationStatusTagType(scope.row.catalog_confirmation_status)">
                {{ catalogConfirmationStatusText(scope.row.catalog_confirmation_status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="解析状态" width="140">
            <template #default="scope">
              <el-tag :type="parseStatusTagType(scope.row.latest_parse_job?.status)">
                {{ parseStatusText(scope.row.latest_parse_job?.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="解析概况" min-width="220">
            <template #default="scope">
              <span v-if="scope.row.latest_parse_job">
                <template v-if="['queued', 'processing'].includes(scope.row.latest_parse_job.status)">
                  <div class="parse-progress-inline">
                    <el-progress
                      :percentage="Number(scope.row.latest_parse_job.progress_percent || 0)"
                      :stroke-width="8"
                      :show-text="false"
                    />
                    <span class="muted">{{ formatParseProgress(scope.row.latest_parse_job) }}</span>
                  </div>
                </template>
                <template v-else>
                  {{ Number(scope.row.latest_parse_job.page_count || 0) }} 页 /
                  {{ Number(scope.row.latest_parse_job.extracted_specs || 0) }} 条规格 /
                  {{ Number(scope.row.latest_parse_job.summary_json?.procedures?.length || 0) }} 条步骤
                </template>
              </span>
              <span v-else class="muted">尚未解析</span>
            </template>
          </el-table-column>
          <el-table-column prop="notes" label="备注" min-width="220" show-overflow-tooltip />
          <el-table-column label="操作" width="340">
            <template #default="scope">
              <el-button link type="primary" @click="openKnowledgeDocument(scope.row)">打开</el-button>
              <el-button link type="primary" :loading="parsingDocumentId === scope.row.id" @click="parseKnowledgeDocument(scope.row)">解析</el-button>
              <el-button link @click="openParseResultDialog(scope.row)" :disabled="!scope.row.latest_parse_job">结果</el-button>
              <el-dropdown trigger="click" @command="(command) => applyReviewStatus(scope.row, command)">
                <el-button link>审核</el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="confirmed">标记已确认</el-dropdown-item>
                    <el-dropdown-item command="needs_fix">标记需补录</el-dropdown-item>
                    <el-dropdown-item command="pending_review">恢复待审核</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
              <el-button link type="danger" @click="removeKnowledgeDocument(scope.row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-dialog>

    <el-dialog v-model="serviceItemDialogVisible" :title="serviceItemForm.id ? '编辑标准项目' : '新增标准项目'" width="880px" destroy-on-close>
      <el-form :model="serviceItemForm" label-width="110px">
        <el-row :gutter="12">
          <el-col :span="12"><el-form-item label="标准项目名称"><el-input v-model="serviceItemForm.service_name" maxlength="120" show-word-limit /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="标准项目编码"><el-input v-model="serviceItemForm.service_code" maxlength="60" show-word-limit /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="8"><el-form-item label="标准工时"><el-input-number v-model="serviceItemForm.labor_hours" :min="0" :step="0.1" style="width: 100%" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="工时费"><el-input-number v-model="serviceItemForm.labor_price" :min="0" :precision="2" style="width: 100%" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="建议售价"><el-input-number v-model="serviceItemForm.suggested_price" :min="0" :precision="2" style="width: 100%" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="维修方法"><el-input v-model="serviceItemForm.repair_method" type="textarea" :rows="3" maxlength="1000" show-word-limit /></el-form-item>
        <el-form-item label="备注"><el-input v-model="serviceItemForm.notes" type="textarea" :rows="2" maxlength="1000" show-word-limit /></el-form-item>
        <div class="parts-editor-head">
          <strong>所需配件</strong>
          <el-button size="small" @click="addRequiredPart">新增配件</el-button>
        </div>
        <div v-for="(item, index) in serviceItemForm.required_parts" :key="index" class="required-part-row">
          <el-select v-model="item.part_id" filterable clearable placeholder="选择配件" style="width: 240px" @change="(value) => onRequiredPartChange(item, value)">
            <el-option v-for="part in partOptions" :key="part.id" :label="`${part.name} (${part.part_no})`" :value="part.id" />
          </el-select>
          <el-input v-model="item.part_name" maxlength="120" show-word-limit placeholder="配件名称" style="width: 180px" />
          <el-input v-model="item.part_no" maxlength="80" show-word-limit placeholder="料号" style="width: 140px" />
          <el-input-number v-model="item.qty" :min="0.1" :step="1" style="width: 120px" />
          <el-input-number v-model="item.unit_price" :min="0" :precision="2" style="width: 140px" />
          <el-button link type="danger" @click="removeRequiredPart(index)">移除</el-button>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="serviceItemDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="serviceItemSaving" @click="saveServiceItem">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="servicePackageDialogVisible" :title="servicePackageForm.id ? '编辑服务套餐' : '新增服务套餐'" width="820px" destroy-on-close>
      <el-form :model="servicePackageForm" label-width="110px">
        <el-row :gutter="12">
          <el-col :span="12"><el-form-item label="套餐名称"><el-input v-model="servicePackageForm.package_name" maxlength="120" show-word-limit /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="套餐编码"><el-input v-model="servicePackageForm.package_code" maxlength="60" show-word-limit /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12"><el-form-item label="建议里程"><el-input-number v-model="servicePackageForm.recommended_interval_km" :min="0" style="width: 100%" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="建议月数"><el-input-number v-model="servicePackageForm.recommended_interval_months" :min="0" style="width: 100%" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="套餐说明"><el-input v-model="servicePackageForm.description" type="textarea" :rows="3" maxlength="1000" show-word-limit /></el-form-item>
        <el-form-item label="包含标准项目">
                    <el-select v-model="servicePackageForm.service_item_ids" multiple filterable placeholder="选择标准项目" style="width: 100%">
            <el-option v-for="item in serviceItems" :key="item.id" :label="item.service_name" :value="item.id" />
          </el-select>
        </el-form-item>
        <div class="package-preview" v-if="servicePackagePreview.items.length">
          <strong>套餐预览</strong>
          <div class="package-preview-grid">
            <span>{{ `标准项目数 ${servicePackagePreview.items.length}` }}</span>
            <span>{{ `工时 ${servicePackagePreview.labor_hours_total.toFixed(1)}h` }}</span>
            <span>{{ `工时费 ¥${servicePackagePreview.labor_price_total.toFixed(2)}` }}</span>
            <span>{{ `配件 ¥${servicePackagePreview.parts_price_total.toFixed(2)}` }}</span>
            <span>{{ `建议售价 ¥${servicePackagePreview.suggested_price_total.toFixed(2)}` }}</span>
          </div>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="servicePackageDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="servicePackageSaving" @click="saveServicePackage">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="manualProcedureDialogVisible" :title="manualProcedureForm.id ? '编辑标准作业卡' : '新增标准作业卡'" width="720px">
      <el-form :model="manualProcedureForm" label-width="110px">
        <el-form-item label="作业卡名称"><el-input v-model="manualProcedureForm.name" maxlength="120" show-word-limit placeholder="例如：更换前刹车片标准作业" /></el-form-item>
        <el-form-item label="专业说明"><el-input v-model="manualProcedureForm.description" type="textarea" :rows="4" maxlength="1000" show-word-limit placeholder="这里可以写作业目的、质量要求、可向客户说明的专业点" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="manualProcedureDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="manualSaving" @click="saveManualProcedure">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="vehicleSpecDialogVisible" :title="vehicleSpecForm.id ? '编辑标准规格' : '新增标准规格'" width="760px">
      <el-form :model="vehicleSpecForm" label-width="100px">
        <el-row :gutter="12">
          <el-col :span="12"><el-form-item label="规格名称"><el-input v-model="vehicleSpecForm.spec_label" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="规格键"><el-input v-model="vehicleSpecForm.spec_key" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="8"><el-form-item label="类型"><el-input v-model="vehicleSpecForm.spec_type" placeholder="torque / fluid / pressure" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="规格值"><el-input v-model="vehicleSpecForm.spec_value" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="单位"><el-input v-model="vehicleSpecForm.spec_unit" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="8"><el-form-item label="来源页码"><el-input v-model="vehicleSpecForm.source_page" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="状态">
            <el-select v-model="vehicleSpecForm.review_status" style="width: 100%">
              <el-option label="待审核" value="pending_review" />
              <el-option label="已确认" value="confirmed" />
              <el-option label="已忽略" value="ignored" />
            </el-select>
          </el-form-item></el-col>
          <el-col :span="8"><el-form-item label="来源"><el-input v-model="vehicleSpecForm.source" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="来源文本"><el-input v-model="vehicleSpecForm.source_text" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="vehicleSpecForm.notes" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="vehicleSpecDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="vehicleSpecSaving" @click="saveVehicleSpec">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="manualStepDialogVisible" :title="manualStepDialogTitle" width="900px" destroy-on-close>
      <div class="parts-editor-head">
        <strong>标准步骤</strong>
        <el-button size="small" @click="appendManualStep()">新增步骤</el-button>
      </div>
      <div v-for="(item, index) in manualStepForm.steps" :key="item.id || index" class="manual-step-row">
        <el-input-number v-model="item.step_order" :min="1" style="width: 90px" />
        <el-input v-model="item.instruction" placeholder="标准步骤描述" style="width: 260px" />
        <el-input v-model="item.required_tools" placeholder="所需工具" style="width: 160px" />
        <el-input v-model="item.torque_spec" placeholder="扭矩/规格，如 45Nm" style="width: 160px" />
        <el-input v-model="item.hazards" placeholder="检查点/注意事项" style="width: 180px" />
        <el-button link type="danger" @click="removeManualStep(index, item)">移除</el-button>
      </div>
      <template #footer>
        <el-button @click="manualStepDialogVisible = false">关闭</el-button>
        <el-button type="primary" :loading="manualSaving" @click="saveManualSteps">保存步骤</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="serviceManualLocatorVisible" :title="serviceManualLocatorTitle" width="920px" destroy-on-close>
      <div class="locator-summary" v-if="currentServiceManualItem">
        <div class="locator-summary__title">推荐章节</div>
        <div class="locator-summary__text">
          根据“{{ currentServiceManualItem.service_name }}”和项目说明，系统优先匹配了这些标准手册分段。你可以直接打开 PDF 或查看该段对应的标准步骤。
        </div>
      </div>
      <el-table :data="serviceManualMatches" style="width: 100%">
        <el-table-column prop="chapter_no" label="章节号" width="90" />
        <el-table-column prop="title" label="章节名称" min-width="220" />
        <el-table-column label="页码范围" width="120">
          <template #default="scope">{{ `${scope.row.start_page || '-'} - ${scope.row.end_page || '-'}` }}</template>
        </el-table-column>
        <el-table-column label="匹配原因" min-width="220">
          <template #default="scope">
            <div class="locator-reasons">
              <el-tag
                v-for="reason in scope.row._match_reasons || []"
                :key="`${scope.row.id}-${reason}`"
                size="small"
                effect="plain"
              >
                {{ reason }}
              </el-tag>
              <span v-if="!(scope.row._match_reasons || []).length" class="muted">章节关键词相近</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220">
          <template #default="scope">
            <el-button link type="primary" @click="scope.row.segment_document && openKnowledgeDocument(scope.row.segment_document)" :disabled="!scope.row.segment_document">打开 PDF</el-button>
            <el-button link type="primary" @click="scope.row.procedure && openManualStepDialog(scope.row.procedure)" :disabled="!scope.row.procedure">查看步骤</el-button>
            <el-button link @click="focusSegment(scope.row)">在分段表中定位</el-button>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="serviceManualLocatorVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="documentDialogVisible" title="上传标准资料" width="680px">
      <el-form :model="documentForm" label-width="100px">
        <el-form-item label="资料名称"><el-input v-model="documentForm.title" maxlength="160" show-word-limit placeholder="例如：CBR650R 原厂维修手册（发动机部分）" /></el-form-item>
        <el-form-item label="资料分类">
          <el-select v-model="documentForm.category" style="width: 100%">
            <el-option label="维修手册" value="维修手册" />
            <el-option label="扭矩表" value="扭矩表" />
            <el-option label="线路图" value="线路图" />
            <el-option label="保养标准" value="保养标准" />
            <el-option label="故障诊断" value="故障诊断" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注"><el-input v-model="documentForm.notes" type="textarea" :rows="3" maxlength="2000" show-word-limit /></el-form-item>
        <el-form-item label="PDF文件">
          <input ref="documentFileInput" type="file" accept=".pdf,application/pdf" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="documentDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="documentSaving" @click="uploadKnowledgeDocument">上传</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="parseResultDialogVisible" title="OCR 解析结果" width="980px">
      <template v-if="parseResultLoading">
        <div class="parse-loading">正在加载解析结果...</div>
      </template>
      <template v-else-if="parseResultDetail">
        <div class="parse-result-actions">
          <el-button
            :disabled="!canMaterializeSegments"
            @click="materializeParseSegments"
          >
            生成目录分段
          </el-button>
          <el-button
            :loading="importingConfirmedSpecs"
            :disabled="!canImportConfirmedSpecs"
            @click="importConfirmedSpecsToCatalog"
          >
            导入已确认规格
          </el-button>
          <el-button
            :loading="importingCatalogModel"
            :disabled="!canBindParseResultToCatalog"
            @click="openCatalogConfirmationDialog('create_new')"
          >
            确认车型
          </el-button>
          <el-button
            type="primary"
            :loading="importingParseResult"
            :disabled="!canImportParseResultToManual"
            @click="importParseResultToManual"
          >
            导入到标准作业卡
          </el-button>
        </div>
        <div class="parse-review-banner">
          <div>
            <strong>{{ `当前审核状态：${reviewStatusText(parseResultDocument?.review_status)}` }}</strong>
            <p>{{ parseResultDocument?.review_notes || '还没有填写审核备注。' }}</p>
          </div>
          <div class="head-actions">
            <el-button size="small" @click="applyReviewStatus(parseResultDocument, 'pending_review')" :disabled="!parseResultDocument?.id">标记待审核</el-button>
            <el-button size="small" type="success" plain @click="applyReviewStatus(parseResultDocument, 'confirmed')" :disabled="!parseResultDocument?.id">标记已确认</el-button>
            <el-button size="small" type="warning" plain @click="applyReviewStatus(parseResultDocument, 'needs_fix')" :disabled="!parseResultDocument?.id">标记需补录</el-button>
          </div>
        </div>
        <div class="parse-confirmation-banner">
          <div>
            <strong>{{ `标准车型确认：${catalogConfirmationStatusText(parseResultDocument?.catalog_confirmation_status)}` }}</strong>
            <p>
              <template v-if="isCatalogConfirmed && parseResultConfirmedModel">
                已确认到 {{ parseResultConfirmedModel.brand }} {{ parseResultConfirmedModel.model_name }}（{{ parseResultConfirmedModel.year_from }}-{{ parseResultConfirmedModel.year_to }}）
              </template>
              <template v-else-if="parseResultSuggestedModel">
                当前资料暂时挂在 {{ parseResultSuggestedModel.brand }} {{ parseResultSuggestedModel.model_name }} 下，请确认是否就是这台车，或改绑到其他车型。
              </template>
              <template v-else>
                先确认这份手册对应的品牌、年款和车型，再继续生成目录分段、导入规格和标准作业卡。
              </template>
            </p>
          </div>
          <div class="head-actions">
            <el-button size="small" :loading="importingCatalogModel" :disabled="!canConfirmCurrentCatalog" @click="confirmCurrentCatalogBinding">确认当前车型</el-button>
            <el-button size="small" type="primary" plain :disabled="!canBindParseResultToCatalog" @click="openCatalogConfirmationDialog('bind_existing')">绑定现有车型</el-button>
            <el-button size="small" type="success" plain :disabled="!canBindParseResultToCatalog" @click="openCatalogConfirmationDialog('create_new')">新建并确认</el-button>
            <el-button size="small" type="warning" plain :loading="importingCatalogModel" @click="resetCatalogConfirmation" :disabled="!parseResultDocument?.id || !isCatalogConfirmed">恢复待确认</el-button>
          </div>
        </div>
        <div class="parse-summary-grid">
          <div class="parse-summary-card">
            <span>解析状态</span>
            <strong>{{ parseStatusText(parseResultDetail.status) }}</strong>
          </div>
          <div class="parse-summary-card" v-if="['queued', 'processing'].includes(parseResultDetail.status)">
            <span>当前进度</span>
            <strong>{{ `${Number(parseResultDetail.progress_percent || 0)}%` }}</strong>
          </div>
          <div class="parse-summary-card" v-if="['queued', 'processing'].includes(parseResultDetail.status)">
            <span>批次进度</span>
            <strong>{{ formatBatchProgress(parseResultDetail) }}</strong>
          </div>
          <div class="parse-summary-card">
            <span>解析引擎</span>
            <strong>{{ parseResultDetail.provider || '未记录' }}</strong>
          </div>
          <div class="parse-summary-card">
            <span>页数</span>
            <strong>{{ parseResultDetail.page_count || 0 }}</strong>
          </div>
          <div class="parse-summary-card">
            <span>规格候选</span>
            <strong>{{ parseResultDetail.extracted_specs || 0 }}</strong>
          </div>
          <div class="parse-summary-card">
            <span>步骤候选</span>
            <strong>{{ parseResultDetail.summary_json?.procedures?.length || 0 }}</strong>
          </div>
        </div>
        <div v-if="['queued', 'processing'].includes(parseResultDetail.status)" class="parse-section-block">
          <div class="section-title-row">
            <strong>后台解析进度</strong>
            <el-tag type="warning" effect="plain">{{ formatBatchProgress(parseResultDetail) }}</el-tag>
          </div>
          <el-progress
            :percentage="Number(parseResultDetail.progress_percent || 0)"
            :stroke-width="12"
            style="margin-top: 10px"
          />
          <p>{{ parseResultDetail.progress_message || '系统正在后台解析资料，请稍候。' }}</p>
        </div>
        <el-alert
          v-if="parseResultDetail.error_message"
          :title="parseResultDetail.error_message"
          type="error"
          show-icon
          :closable="false"
          style="margin-bottom: 12px"
        />
        <el-tabs v-model="parseViewTab" class="parse-view-tabs">
          <el-tab-pane label="总览" name="overview">
            <div class="quick-overview-grid">
              <div class="quick-overview-card">
                <span>识别车型</span>
                <strong>{{ quickOverview.modelLabel }}</strong>
              </div>
              <div class="quick-overview-card">
                <span>模板完成度</span>
                <strong>{{ quickOverview.templateCompletion }}</strong>
              </div>
              <div class="quick-overview-card">
                <span>关键规格</span>
                <strong>{{ quickOverview.specSummary }}</strong>
              </div>
              <div class="quick-overview-card">
                <span>步骤结构</span>
                <strong>{{ quickOverview.procedureSummary }}</strong>
              </div>
              <div class="quick-overview-card">
                <span>页面类型</span>
                <strong>{{ quickOverview.pageTypeSummary }}</strong>
              </div>
            </div>
            <div class="parse-section-block">
              <strong>快速结论</strong>
              <div class="parse-chip-list">
                <el-tag v-for="item in quickOverview.highlights" :key="item" effect="plain">
                  {{ item }}
                </el-tag>
              </div>
            </div>
            <div class="parse-section-block">
              <strong>入库准备度</strong>
              <div class="readiness-list">
                <div v-for="item in quickOverview.readinessItems" :key="item.key" class="readiness-item">
                  <div class="section-title-row">
                    <strong>{{ item.label }}</strong>
                    <el-tag :type="item.ready ? 'success' : 'warning'" effect="plain">
                      {{ item.ready ? '可执行' : '待补充' }}
                    </el-tag>
                  </div>
                  <p>{{ item.reason }}</p>
                </div>
              </div>
            </div>
            <div class="parse-section-block">
              <strong>推荐动作</strong>
              <div class="readiness-list">
                <div class="readiness-item">
                  <div class="section-title-row">
                    <strong>确认车型</strong>
                    <el-tag :type="isCatalogConfirmed ? 'success' : 'warning'" effect="plain">
                      {{ isCatalogConfirmed ? '已确认' : '待确认' }}
                    </el-tag>
                  </div>
                  <p>{{ isCatalogConfirmed ? '这份手册的品牌、年款和车型已经确认，可以继续生成目录分段和导入标准库。' : (canBindParseResultToCatalog ? '候选车型已经识别出来，请先确认是当前车型、现有车型还是新建车型。' : '需要先稳定识别品牌和车型，再进入确认流程。') }}</p>
                  <div class="head-actions">
                    <el-button size="small" :loading="importingCatalogModel" :disabled="!canConfirmCurrentCatalog" @click="confirmCurrentCatalogBinding">确认当前</el-button>
                    <el-button type="primary" plain size="small" :disabled="!canBindParseResultToCatalog" @click="openCatalogConfirmationDialog('bind_existing')">绑定现有</el-button>
                    <el-button type="success" plain size="small" :disabled="!canBindParseResultToCatalog" @click="openCatalogConfirmationDialog('create_new')">新建并确认</el-button>
                  </div>
                </div>
                <div class="readiness-item">
                  <div class="section-title-row">
                    <strong>导入标准作业卡</strong>
                    <el-tag :type="canImportParseResultToManual ? 'success' : 'warning'" effect="plain">
                      {{ canImportParseResultToManual ? '现在可做' : '暂不可做' }}
                    </el-tag>
                  </div>
                  <p>{{ canImportParseResultToManual ? '当前已识别到可用步骤，且标准车型已经确认，可导入为标准手册条目。' : '需要先确认标准车型，并识别出有效步骤，再导入到标准手册条目。' }}</p>
                  <el-button
                    type="primary"
                    size="small"
                    :loading="importingParseResult"
                    :disabled="!canImportParseResultToManual"
                    @click="importParseResultToManual"
                  >
                    导入标准作业卡
                  </el-button>
                </div>
                <div class="readiness-item">
                  <div class="section-title-row">
                    <strong>继续识别</strong>
                    <el-tag :type="['queued', 'processing'].includes(parseResultDetail.status) ? 'warning' : 'info'" effect="plain">
                      {{ ['queued', 'processing'].includes(parseResultDetail.status) ? '后台处理中' : '可再次发起' }}
                    </el-tag>
                  </div>
                  <p>{{ ['queued', 'processing'].includes(parseResultDetail.status) ? '当前任务仍在运行，系统会自动继续更新进度。' : '如果结果不完整，可以重新发起识别任务。' }}</p>
                  <el-button
                    size="small"
                    :disabled="['queued', 'processing'].includes(parseResultDetail.status)"
                    @click="retryParseJob({ latest_parse_job: { id: parseResultDetail.id } })"
                  >
                    重新识别
                  </el-button>
                </div>
              </div>
            </div>
            <div class="parse-section-block" v-if="quickOverview.gaps.length">
              <strong>待补全项</strong>
              <div class="parse-chip-list">
                <el-tag v-for="item in quickOverview.gaps" :key="item" type="warning" effect="plain">
                  {{ item }}
                </el-tag>
              </div>
            </div>
            <div class="parse-section-block">
              <strong>解析摘要</strong>
              <p>{{ parseResultDetail.summary_json?.summary || '暂无摘要' }}</p>
            </div>
            <div class="parse-section-block" v-if="(parseResultDetail.raw_result_json?.kb_collections || []).length">
              <strong>已同步检索库</strong>
              <div class="parse-chip-list">
                <el-tag v-for="(item, index) in parseResultDetail.raw_result_json.kb_collections" :key="index" type="success" effect="plain">
                  {{ item }}
                </el-tag>
              </div>
            </div>
            <div class="parse-section-block" v-if="(parseResultDetail.summary_json?.sections || []).length">
              <div class="section-title-row">
                <strong>章节候选</strong>
                <el-button link type="primary" @click="openResultSectionsEditor">编辑</el-button>
              </div>
              <div class="parse-chip-list">
                <el-tag v-for="(item, index) in parseResultDetail.summary_json.sections" :key="index" effect="plain">
                  {{ `${item.title || item}${formatPageText(item) ? ` · ${formatPageText(item)}` : ''}` }}
                </el-tag>
              </div>
            </div>
            <div class="parse-section-block" v-if="tocSegments.length">
              <div class="section-title-row">
                <strong>目录分段</strong>
                <el-tag effect="plain">{{ `${tocSegments.length} 段` }}</el-tag>
              </div>
              <el-table :data="tocSegments" size="small" style="width: 100%; margin-top: 8px">
                <el-table-column prop="chapter_no" label="章节号" width="90" />
                <el-table-column prop="title" label="目录标题" min-width="180" />
                <el-table-column label="目录页" width="90">
                  <template #default="scope">{{ scope.row.toc_page_number || '-' }}</template>
                </el-table-column>
                <el-table-column label="起始 PDF 页" width="110">
                  <template #default="scope">{{ scope.row.start_page || '-' }}</template>
                </el-table-column>
                <el-table-column label="结束 PDF 页" width="110">
                  <template #default="scope">{{ scope.row.end_page || '-' }}</template>
                </el-table-column>
                <el-table-column label="状态" width="100">
                  <template #default="scope">
                    <el-tag :type="scope.row.resolved ? 'success' : 'warning'" effect="plain">
                      {{ scope.row.resolved ? '已定位' : '待定位' }}
                    </el-tag>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </el-tab-pane>

          <el-tab-pane label="模板覆盖" name="template">
            <div class="parse-section-block" v-if="parseResultDetail.raw_result_json?.manual_template">
              <div class="section-title-row">
                <strong>标准模板完成度</strong>
                <el-tag type="warning" effect="plain">
                  {{ `${Math.round(Number(parseResultDetail.raw_result_json.manual_template.completion_ratio || 0) * 100)}%` }}
                </el-tag>
              </div>
              <el-table
                :data="parseResultDetail.raw_result_json.manual_template.completion || []"
                size="small"
                style="width: 100%; margin-top: 8px"
              >
                <el-table-column prop="label" label="模板模块" min-width="180" />
                <el-table-column label="状态" width="120">
                  <template #default="scope">
                    <el-tag :type="scope.row.is_complete ? 'success' : 'info'" effect="plain">
                      {{ scope.row.is_complete ? '已覆盖' : '待补全' }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="已识别字段" min-width="220" show-overflow-tooltip>
                  <template #default="scope">{{ (scope.row.present_children || []).join('、') || '-' }}</template>
                </el-table-column>
                <el-table-column label="缺失字段" min-width="220" show-overflow-tooltip>
                  <template #default="scope">{{ (scope.row.missing_children || []).join('、') || '-' }}</template>
                </el-table-column>
              </el-table>
            </div>
          </el-tab-pane>

          <el-tab-pane label="车型识别" name="vehicle">
            <div class="parse-section-block" v-if="parseResultDetail.raw_result_json?.normalized_manual">
              <div class="section-title-row">
                <strong>识别车型信息</strong>
                <el-button link type="primary" @click="openVehicleRecognitionEditor">编辑</el-button>
              </div>
              <el-descriptions :column="2" border size="small">
                <el-descriptions-item label="文档标题">
                  {{ parseResultDetail.raw_result_json.normalized_manual.document_profile?.document_title || '-' }}
                </el-descriptions-item>
                <el-descriptions-item label="文档类型">
                  {{ parseResultDetail.raw_result_json.normalized_manual.document_profile?.document_type || '-' }}
                </el-descriptions-item>
                <el-descriptions-item label="识别品牌">
                  {{ recognizedCatalogCandidate.brand || '-' }}
                </el-descriptions-item>
                <el-descriptions-item label="识别车型">
                  {{ recognizedCatalogCandidate.model_name || '-' }}
                </el-descriptions-item>
                <el-descriptions-item label="识别年份">
                  {{ recognizedCatalogCandidate.year_range || '-' }}
                </el-descriptions-item>
                <el-descriptions-item label="发动机代码">
                  {{ recognizedCatalogCandidate.engine_code || '-' }}
                </el-descriptions-item>
                <el-descriptions-item label="项目索引">
                  {{ (parseResultDetail.raw_result_json.normalized_manual.operation_index?.operation_names || []).join('、') || '-' }}
                </el-descriptions-item>
                <el-descriptions-item label="来源页码">
                  {{ (parseResultDetail.raw_result_json.normalized_manual.traceability?.source_pages || []).join('、') || '-' }}
                </el-descriptions-item>
              </el-descriptions>
            </div>
          </el-tab-pane>

          <el-tab-pane label="维修工快查" name="technician">
            <div class="parse-section-block">
              <div class="section-title-row">
                <strong>现场快查卡</strong>
                <el-tag effect="plain">{{ `${technicianStepCards.length} 步` }}</el-tag>
              </div>
              <div class="quick-overview-grid">
                <div class="quick-overview-card">
                  <span>关键扭矩</span>
                  <strong>{{ technicianTorqueSpecs.length }}</strong>
                </div>
                <div class="quick-overview-card">
                  <span>油液/容量</span>
                  <strong>{{ technicianFluidSpecs.length }}</strong>
                </div>
                <div class="quick-overview-card">
                  <span>滤芯/滤清器</span>
                  <strong>{{ technicianFilterRows.length }}</strong>
                </div>
                <div class="quick-overview-card">
                  <span>紧固件</span>
                  <strong>{{ technicianFastenerRows.length }}</strong>
                </div>
                <div class="quick-overview-card">
                  <span>工具</span>
                  <strong>{{ technicianToolRows.length }}</strong>
                </div>
              </div>
            </div>

            <div class="parse-section-block" v-if="technicianTorqueSpecs.length">
              <div class="section-title-row">
                <strong>扭矩快查</strong>
                <el-tag effect="plain">{{ `${technicianTorqueSpecs.length} 条` }}</el-tag>
              </div>
              <el-table :data="technicianTorqueSpecs" size="small" style="width: 100%; margin-top: 8px">
                <el-table-column prop="label" label="部位" min-width="180" />
                <el-table-column label="扭矩值" width="160">
                  <template #default="scope">{{ `${scope.row.value || '-'} ${scope.row.unit || ''}` }}</template>
                </el-table-column>
                <el-table-column label="页码" width="110">
                  <template #default="scope">{{ formatPageText(scope.row) }}</template>
                </el-table-column>
                <el-table-column prop="source_text" label="来源文本" min-width="220" show-overflow-tooltip />
              </el-table>
            </div>

            <div class="spec-card-grid">
              <div class="spec-card" v-if="technicianFluidSpecs.length">
                <div class="section-title-row">
                  <strong>油液/容量</strong>
                  <el-tag effect="plain">{{ `${technicianFluidSpecs.length} 条` }}</el-tag>
                </div>
                <el-table :data="technicianFluidSpecs" size="small" style="width: 100%; margin-top: 8px">
                  <el-table-column prop="label" label="项目" min-width="150" />
                  <el-table-column label="数值" width="140">
                    <template #default="scope">{{ `${scope.row.value || '-'} ${scope.row.unit || ''}` }}</template>
                  </el-table-column>
                  <el-table-column label="页码" width="100">
                    <template #default="scope">{{ formatPageText(scope.row) }}</template>
                  </el-table-column>
                </el-table>
              </div>

              <div class="spec-card" v-if="technicianFilterRows.length || technicianMaterialRows.length">
                <div class="section-title-row">
                  <strong>配件/耗材</strong>
                  <el-tag effect="plain">{{ `${technicianFilterRows.length + technicianMaterialRows.length} 项` }}</el-tag>
                </div>
                <el-table :data="[...technicianFilterRows, ...technicianMaterialRows]" size="small" style="width: 100%; margin-top: 8px">
                  <el-table-column prop="name" label="名称" min-width="150" />
                  <el-table-column label="参数" width="140">
                    <template #default="scope">{{ formatValueUnit(scope.row.value, scope.row.unit) }}</template>
                  </el-table-column>
                  <el-table-column prop="source_text" label="来源文本" min-width="180" show-overflow-tooltip />
                </el-table>
              </div>

              <div class="spec-card" v-if="technicianFastenerRows.length">
                <div class="section-title-row">
                  <strong>紧固件快查</strong>
                  <el-tag effect="plain">{{ `${technicianFastenerRows.length} 项` }}</el-tag>
                </div>
                <el-table :data="technicianFastenerRows" size="small" style="width: 100%; margin-top: 8px">
                  <el-table-column label="紧固件" min-width="220">
                    <template #default="scope">{{ formatTranslatedValue(scope.row.name, scope.row.name_zh) }}</template>
                  </el-table-column>
                  <el-table-column prop="size" label="规格" width="120" />
                  <el-table-column prop="drive_type" label="刀型" width="110" />
                  <el-table-column prop="source_text" label="来源文本" min-width="180" show-overflow-tooltip />
                </el-table>
              </div>

              <div class="spec-card" v-if="technicianToolRows.length">
                <div class="section-title-row">
                  <strong>工具快查</strong>
                  <el-tag effect="plain">{{ `${technicianToolRows.length} 项` }}</el-tag>
                </div>
                <div class="parse-chip-list" style="margin-top: 8px">
                  <el-tag v-for="item in technicianToolRows" :key="item.name" effect="plain">{{ formatTranslatedValue(item.name, item.name_zh) }}</el-tag>
                </div>
              </div>
            </div>

            <div class="parse-section-block" v-if="technicianStepCards.length">
              <div class="section-title-row">
                <strong>步骤卡片</strong>
                <div class="section-title-row tail-actions">
                  <el-tag v-if="technicianCriticalSteps.length" type="danger" effect="plain">{{ `${technicianCriticalSteps.length} 个关键步骤` }}</el-tag>
                  <el-tag effect="plain">{{ `${technicianStepCards.length} 步` }}</el-tag>
                </div>
              </div>
              <div class="technician-step-list">
                <div v-for="item in technicianStepCards" :key="`${item.step_order}-${item.source_page}-${item.instruction}`" class="technician-step-card">
                  <div class="section-title-row">
                    <strong>{{ `步骤 ${item.step_order}` }}</strong>
                    <div class="section-title-row tail-actions">
                      <el-tag v-if="item.section_title" effect="plain">{{ item.section_title }}</el-tag>
                      <el-tag :type="stepCriticalityTagType(item.criticality)" effect="plain">{{ formatCriticality(item.criticality) }}</el-tag>
                      <el-tag effect="plain">{{ formatPageText(item) }}</el-tag>
                    </div>
                  </div>
                  <p>{{ item.instruction_zh || item.instruction_original || item.instruction || '-' }}</p>
                  <div class="technician-inline-grid">
                    <div v-if="item.step_purpose">
                      <span>工序目的</span>
                      <strong>{{ item.step_purpose }}</strong>
                    </div>
                    <div>
                      <span>动作类型</span>
                      <strong>{{ formatActionType(item.action_type) }}</strong>
                    </div>
                    <div>
                      <span>执行岗位</span>
                      <strong>{{ item.executor_role || '-' }}</strong>
                    </div>
                    <div v-if="item.support_role">
                      <span>配合岗位</span>
                      <strong>{{ item.support_role }}</strong>
                    </div>
                    <div>
                      <span>复核岗位</span>
                      <strong>{{ item.verification_role || '-' }}</strong>
                    </div>
                    <div>
                      <span>对象部件</span>
                      <strong>{{ item.target_component || '-' }}</strong>
                    </div>
                    <div>
                      <span>工具</span>
                      <strong>{{ formatToolNames(item.required_tools) }}</strong>
                    </div>
                    <div v-if="formatSimpleList(item.input_requirements) !== '-'">
                      <span>输入条件</span>
                      <strong>{{ formatSimpleList(item.input_requirements) }}</strong>
                    </div>
                    <div v-if="formatSimpleList(item.preconditions) !== '-'">
                      <span>开工前</span>
                      <strong>{{ formatSimpleList(item.preconditions) }}</strong>
                    </div>
                    <div v-if="formatSimpleList(item.setup_conditions) !== '-'">
                      <span>工位准备</span>
                      <strong>{{ formatSimpleList(item.setup_conditions) }}</strong>
                    </div>
                    <div>
                      <span>扭矩</span>
                      <strong>{{ formatTorqueRows(item.torque_specs) }}</strong>
                    </div>
                    <div>
                      <span>耗材</span>
                      <strong>{{ formatNamedRows(item.materials) }}</strong>
                    </div>
                    <div>
                      <span>紧固件</span>
                      <strong>{{ formatFastenerRows(item.fasteners) }}</strong>
                    </div>
                    <div>
                      <span>控制点</span>
                      <strong>{{ formatSimpleList(item.control_points) }}</strong>
                    </div>
                    <div>
                      <span>验收点</span>
                      <strong>{{ formatSimpleList(item.acceptance_checks) }}</strong>
                    </div>
                    <div v-if="formatSimpleList(item.completion_definition) !== '-'">
                      <span>完成定义</span>
                      <strong>{{ formatSimpleList(item.completion_definition) }}</strong>
                    </div>
                    <div v-if="formatSimpleList(item.output_results) !== '-'">
                      <span>输出结果</span>
                      <strong>{{ formatSimpleList(item.output_results) }}</strong>
                    </div>
                    <div v-if="formatSimpleList(item.reassembly_requirements) !== '-'">
                      <span>复装要求</span>
                      <strong>{{ formatSimpleList(item.reassembly_requirements) }}</strong>
                    </div>
                    <div v-if="formatSimpleList(item.record_requirements) !== '-'">
                      <span>记录要求</span>
                      <strong>{{ formatSimpleList(item.record_requirements) }}</strong>
                    </div>
                    <div v-if="formatSimpleList(item.caution_notes) !== '-'">
                      <span>风险提示</span>
                      <strong>{{ formatSimpleList(item.caution_notes) }}</strong>
                    </div>
                    <div v-if="formatSimpleList(item.common_failure_modes) !== '-'">
                      <span>常见失误</span>
                      <strong>{{ formatSimpleList(item.common_failure_modes) }}</strong>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </el-tab-pane>

          <el-tab-pane label="规格与步骤" name="specs">
            <div class="parse-section-block" v-if="groupedSpecCards.length">
              <strong>规格候选分类</strong>
              <div class="spec-card-grid">
                <div v-for="group in groupedSpecCards" :key="group.key" class="spec-card">
                  <div class="section-title-row">
                    <strong>{{ group.label }}</strong>
                    <div class="section-title-row tail-actions">
                      <el-tag effect="plain">{{ `${group.items.length} 条` }}</el-tag>
                      <el-button link type="primary" @click="openSpecGroupEditor(group)">编辑</el-button>
                    </div>
                  </div>
                  <el-table :data="group.items" size="small" style="width: 100%; margin-top: 8px">
                    <el-table-column prop="label" label="标签" min-width="120" />
                    <el-table-column label="值" width="140">
                      <template #default="scope">{{ `${scope.row.value || '-'} ${scope.row.unit || ''}` }}</template>
                    </el-table-column>
                    <el-table-column label="页码" width="110">
                      <template #default="scope">{{ formatPageText(scope.row) }}</template>
                    </el-table-column>
                    <el-table-column label="状态" width="100">
                      <template #default="scope">
                        <el-tag :type="itemReviewTagType(scope.row.review_status)" effect="plain">
                          {{ itemReviewText(scope.row.review_status) }}
                        </el-tag>
                      </template>
                    </el-table-column>
                    <el-table-column prop="source_text" label="来源文本" min-width="180" show-overflow-tooltip />
                    <el-table-column label="操作" width="180">
                      <template #default="scope">
                        <el-button link type="success" @click="markSpecItemStatus(group.key, scope.$index, 'confirmed')">确认</el-button>
                        <el-button link type="warning" @click="markSpecItemStatus(group.key, scope.$index, 'ignored')">忽略</el-button>
                        <el-button link @click="markSpecItemStatus(group.key, scope.$index, 'pending_review')">恢复</el-button>
                      </template>
                    </el-table-column>
                  </el-table>
                </div>
              </div>
            </div>
            <div class="parse-section-block">
              <strong>步骤候选分类</strong>
              <div class="spec-card-grid">
                <div v-for="group in groupedProcedureCards" :key="group.key" class="spec-card">
                  <div class="section-title-row">
                    <strong>{{ group.label }}</strong>
                    <div class="section-title-row tail-actions">
                      <el-tag effect="plain">{{ `${group.items.length} 步` }}</el-tag>
                      <el-button link type="primary" @click="openProcedureGroupEditor(group)">编辑</el-button>
                    </div>
                  </div>
                  <el-table :data="group.items" size="small" style="width: 100%; margin-top: 8px">
                    <el-table-column prop="step_order" label="步骤" width="80" />
                    <el-table-column label="内容" min-width="220" show-overflow-tooltip>
                      <template #default="scope">{{ scope.row.instruction_zh || scope.row.instruction_original || scope.row.instruction || '-' }}</template>
                    </el-table-column>
                    <el-table-column prop="required_tools" label="工具" min-width="120" show-overflow-tooltip />
                    <el-table-column prop="torque_spec" label="扭矩/规格" width="120" show-overflow-tooltip />
                    <el-table-column label="页码" width="110">
                      <template #default="scope">{{ formatPageText(scope.row) }}</template>
                    </el-table-column>
                    <el-table-column label="状态" width="100">
                      <template #default="scope">
                        <el-tag :type="itemReviewTagType(scope.row.review_status)" effect="plain">
                          {{ itemReviewText(scope.row.review_status) }}
                        </el-tag>
                      </template>
                    </el-table-column>
                    <el-table-column label="操作" width="180">
                      <template #default="scope">
                        <el-button link type="success" @click="markProcedureItemStatus(group.key, scope.$index, 'confirmed')">确认</el-button>
                        <el-button link type="warning" @click="markProcedureItemStatus(group.key, scope.$index, 'ignored')">忽略</el-button>
                        <el-button link @click="markProcedureItemStatus(group.key, scope.$index, 'pending_review')">恢复</el-button>
                      </template>
                    </el-table-column>
                  </el-table>
                </div>
              </div>
            </div>
          </el-tab-pane>

          <el-tab-pane label="逐页内容" name="pages">
            <el-table :data="parseResultDetail.pages || []" max-height="320" style="width: 100%">
              <el-table-column prop="page_number" label="页码" width="80" />
              <el-table-column label="页面类型" width="140">
                <template #default="scope">
                  <el-tag effect="plain">{{ pageTypeText(scope.row.page_type) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="判断来源" width="120">
                <template #default="scope">
                  <el-tag :type="scope.row.page_type_source === 'llm' ? 'success' : 'info'" effect="plain">
                    {{ scope.row.page_type_source === 'llm' ? '本地模型' : '规则' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="summary" label="页面摘要" min-width="220" show-overflow-tooltip />
              <el-table-column label="规格候选" width="100">
                <template #default="scope">{{ (scope.row.specs_json || []).length }}</template>
              </el-table-column>
              <el-table-column label="步骤候选" width="100">
                <template #default="scope">{{ (scope.row.procedures_json || []).length }}</template>
              </el-table-column>
              <el-table-column label="抽取来源" width="140">
                <template #default="scope">
                  <el-tag effect="plain">
                    {{ [scope.row.spec_extraction_source, scope.row.procedure_extraction_source].filter((item) => item && item !== 'disabled').join(' / ') || '未抽取' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="查看" width="100">
                <template #default="scope">
                  <el-button link type="primary" @click="selectedParsePage = scope.row.page_number">展开</el-button>
                </template>
              </el-table-column>
            </el-table>
            <div v-if="selectedParsePageDetail" class="parse-page-detail">
              <div class="section-title-row">
                <strong>{{ `第 ${selectedParsePageDetail.page_number} 页详情` }}</strong>
                <div class="section-title-row tail-actions">
                  <el-tag effect="plain">{{ selectedParsePageDetail.page_label || '页面内容' }}</el-tag>
                  <el-tag effect="plain">{{ pageTypeText(selectedParsePageDetail.page_type) }}</el-tag>
                  <el-tag :type="selectedParsePageDetail.page_type_source === 'llm' ? 'success' : 'info'" effect="plain">
                    {{ selectedParsePageDetail.page_type_source === 'llm' ? '本地模型判定' : '规则判定' }}
                  </el-tag>
                  <el-tag effect="plain">
                    {{ [selectedParsePageDetail.spec_extraction_source, selectedParsePageDetail.procedure_extraction_source].filter((item) => item && item !== 'disabled').join(' / ') || '未抽取' }}
                  </el-tag>
                  <el-button link type="primary" @click="openParsePageEditor">编辑本页</el-button>
                </div>
              </div>
              <p class="parse-page-summary">{{ selectedParsePageDetail.summary || '暂无页面摘要' }}</p>
              <el-alert
                :title="selectedParsePageDetail.page_type_reason || '暂无页面类型说明'"
                type="info"
                :closable="false"
                show-icon
                style="margin-bottom: 12px"
              />
              <el-collapse>
                <el-collapse-item title="页面文本" name="text">
                  <pre class="parse-page-text">{{ selectedParsePageDetail.text_content || '-' }}</pre>
                </el-collapse-item>
                <el-collapse-item title="页面分块" name="segments">
                  <div class="parse-step-list">
                    <div v-for="(item, index) in selectedParsePageSegments" :key="`${item.role}-${index}`" class="parse-step-item">
                      <div class="section-title-row">
                        <strong>{{ `片段 ${index + 1}` }}</strong>
                        <el-tag effect="plain">{{ formatSegmentRole(item.role) }}</el-tag>
                      </div>
                      <p>{{ item.text || '-' }}</p>
                    </div>
                    <div v-if="!selectedParsePageSegments.length" class="muted">暂无页面分块</div>
                  </div>
                </el-collapse-item>
                <el-collapse-item title="参数表行" name="spec-table">
                <el-table :data="selectedParsePageSpecTableRows" size="small" style="width: 100%">
                  <el-table-column label="项目" min-width="220">
                    <template #default="scope">{{ formatTranslatedValue(scope.row.item, scope.row.item_zh) }}</template>
                  </el-table-column>
                  <el-table-column prop="standard_value" label="标准值" min-width="140" />
                  <el-table-column prop="limit_value" label="极限值" min-width="140" />
                  <el-table-column label="工具" min-width="160">
                    <template #default="scope">{{ formatTranslatedValue(scope.row.tool, scope.row.tool_zh) }}</template>
                  </el-table-column>
                  <el-table-column prop="model" label="适用车型" min-width="140" />
                  <el-table-column label="备注" min-width="180" show-overflow-tooltip>
                    <template #default="scope">{{ formatTranslatedValue(scope.row.note, scope.row.note_zh) }}</template>
                  </el-table-column>
                </el-table>
                  <div v-if="!selectedParsePageSpecTableRows.length" class="muted">暂无参数表行</div>
                </el-collapse-item>
                <el-collapse-item title="规格候选" name="specs">
                  <div class="parse-chip-list">
                    <el-tag v-for="(item, index) in selectedParsePageDetail.specs_json || []" :key="index" :type="itemReviewTagType(item.review_status)" effect="plain">
                      {{ `${item.label || item.type}: ${item.value || '-'} ${item.unit || ''} · ${formatPageText(item)}` }}
                    </el-tag>
                  </div>
                </el-collapse-item>
                <el-collapse-item title="步骤候选" name="procedures">
                  <div class="parse-step-list">
                    <div v-for="(item, index) in selectedParsePageDetail.procedures_json || []" :key="index" class="parse-step-item">
                      <div class="section-title-row">
                        <strong>{{ `步骤 ${item.step_order || index + 1}` }}</strong>
                        <el-tag :type="itemReviewTagType(item.review_status)" effect="plain">{{ itemReviewText(item.review_status) }}</el-tag>
                      </div>
                  <p>{{ item.instruction || '-' }}</p>
                  <p v-if="item.instruction_zh && !item.instruction_original" class="parse-page-summary" style="margin-top: 6px;">
                    {{ item.instruction_zh }}
                  </p>
                    </div>
                  </div>
                </el-collapse-item>
              </el-collapse>
            </div>
          </el-tab-pane>
        </el-tabs>
      </template>
      <template v-else>
        <el-empty description="还没有解析结果" />
      </template>
    </el-dialog>

    <el-dialog v-model="catalogConfirmationDialogVisible" :title="catalogConfirmationMode === 'bind_existing' ? '绑定到现有车型' : '新建并确认车型'" width="720px">
      <el-form :model="catalogConfirmationForm" label-width="110px">
        <template v-if="catalogConfirmationMode === 'bind_existing'">
          <el-form-item label="选择车型">
            <el-select v-model="catalogConfirmationForm.model_id" filterable placeholder="请选择标准车型" style="width: 100%">
              <el-option v-for="item in existingCatalogModelOptions" :key="item.id" :label="item.label" :value="item.id" />
            </el-select>
          </el-form-item>
        </template>
        <template v-else>
          <el-row :gutter="12">
            <el-col :span="12"><el-form-item label="品牌"><el-input v-model="catalogConfirmationForm.brand" /></el-form-item></el-col>
            <el-col :span="12"><el-form-item label="车型"><el-input v-model="catalogConfirmationForm.model_name" /></el-form-item></el-col>
          </el-row>
          <el-row :gutter="12">
            <el-col :span="12"><el-form-item label="起始年份"><el-input-number v-model="catalogConfirmationForm.year_from" :min="1950" :max="2100" style="width: 100%" /></el-form-item></el-col>
            <el-col :span="12"><el-form-item label="截止年份"><el-input-number v-model="catalogConfirmationForm.year_to" :min="1950" :max="2100" style="width: 100%" /></el-form-item></el-col>
          </el-row>
          <el-row :gutter="12">
            <el-col :span="12"><el-form-item label="排量(cc)"><el-input-number v-model="catalogConfirmationForm.displacement_cc" :min="0" :max="2500" style="width: 100%" /></el-form-item></el-col>
            <el-col :span="12"><el-form-item label="发动机代码"><el-input v-model="catalogConfirmationForm.default_engine_code" /></el-form-item></el-col>
          </el-row>
          <el-form-item label="分类"><el-input v-model="catalogConfirmationForm.category" /></el-form-item>
        </template>
        <el-form-item label="确认备注"><el-input v-model="catalogConfirmationForm.notes" type="textarea" :rows="3" placeholder="可以写明识别依据、页码或判断原因" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="catalogConfirmationDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="catalogConfirmationSaving" @click="saveCatalogConfirmation">确认保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="vehicleRecognitionEditorVisible" title="编辑车型识别结果" width="700px">
      <el-form :model="vehicleRecognitionForm" label-width="100px">
        <el-form-item label="品牌"><el-input v-model="vehicleRecognitionForm.brand" /></el-form-item>
        <el-form-item label="车型"><el-input v-model="vehicleRecognitionForm.model_name" /></el-form-item>
        <el-form-item label="年份范围"><el-input v-model="vehicleRecognitionForm.year_range" placeholder="例如 2019-2024" /></el-form-item>
        <el-form-item label="发动机代码"><el-input v-model="vehicleRecognitionForm.engine_code" /></el-form-item>
        <el-form-item label="来源页码"><el-input v-model="vehicleRecognitionForm.source_pages_text" placeholder="例如 1,2,3" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="vehicleRecognitionEditorVisible = false">取消</el-button>
        <el-button type="primary" :loading="parseResultSaving" @click="saveVehicleRecognitionEditor">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="resultListEditorVisible" :title="resultListEditorTitle" width="980px">
      <div class="parts-editor-head">
        <strong>{{ resultListEditorTitle }}</strong>
        <el-button size="small" @click="appendResultListEditorRow">新增一行</el-button>
      </div>
      <template v-if="resultListEditorType === 'sections'">
        <div v-for="(item, index) in resultListEditorRows" :key="index" class="manual-step-row">
          <el-input v-model="item.title" placeholder="章节标题" style="width: 320px" />
          <el-input v-model="item.page_number" placeholder="页码" style="width: 120px" />
          <el-button link type="danger" @click="removeResultListEditorRow(index)">移除</el-button>
        </div>
      </template>
      <template v-else-if="resultListEditorType === 'specs'">
        <div v-for="(item, index) in resultListEditorRows" :key="index" class="manual-step-row">
          <el-input v-model="item.label" placeholder="标签" style="width: 150px" />
          <el-input v-model="item.type" placeholder="类型" style="width: 120px" />
          <el-input v-model="item.value" placeholder="值" style="width: 120px" />
          <el-input v-model="item.unit" placeholder="单位" style="width: 100px" />
          <el-input v-model="item.page_number" placeholder="页码" style="width: 100px" />
          <el-input v-model="item.source_text" placeholder="来源文本" style="width: 220px" />
          <el-button link type="danger" @click="removeResultListEditorRow(index)">移除</el-button>
        </div>
      </template>
      <template v-else>
        <div v-for="(item, index) in resultListEditorRows" :key="index" class="manual-step-row">
          <el-input-number v-model="item.step_order" :min="1" style="width: 90px" />
          <el-input v-model="item.instruction" placeholder="步骤内容" style="width: 260px" />
          <el-input v-model="item.required_tools" placeholder="工具" style="width: 130px" />
          <el-input v-model="item.torque_spec" placeholder="扭矩/规格" style="width: 120px" />
          <el-input v-model="item.page_number" placeholder="页码" style="width: 100px" />
          <el-input v-model="item.hazards" placeholder="注意事项" style="width: 180px" />
          <el-button link type="danger" @click="removeResultListEditorRow(index)">移除</el-button>
        </div>
      </template>
      <template #footer>
        <el-button @click="resultListEditorVisible = false">取消</el-button>
        <el-button type="primary" :loading="parseResultSaving" @click="saveResultListEditor">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="parsePageEditorVisible" title="编辑页面识别结果" width="1000px">
      <el-form :model="parsePageEditorForm" label-width="90px">
        <el-form-item label="页码">
          <el-tag effect="plain">{{ parsePageEditorForm.page_number || '-' }}</el-tag>
        </el-form-item>
        <el-form-item label="页面摘要"><el-input v-model="parsePageEditorForm.summary" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="页面文本"><el-input v-model="parsePageEditorForm.text_content" type="textarea" :rows="8" /></el-form-item>
      </el-form>
      <div class="parts-editor-head">
        <strong>规格候选</strong>
        <el-button size="small" @click="appendParsePageSpec">新增规格</el-button>
      </div>
      <div v-for="(item, index) in parsePageEditorForm.specs_json" :key="`spec-${index}`" class="manual-step-row">
        <el-input v-model="item.label" placeholder="标签" style="width: 150px" />
        <el-input v-model="item.type" placeholder="类型" style="width: 120px" />
        <el-input v-model="item.value" placeholder="值" style="width: 120px" />
        <el-input v-model="item.unit" placeholder="单位" style="width: 100px" />
        <el-input v-model="item.page_number" placeholder="页码" style="width: 100px" />
        <el-input v-model="item.source_text" placeholder="来源文本" style="width: 220px" />
        <el-button link type="danger" @click="parsePageEditorForm.specs_json.splice(index, 1)">移除</el-button>
      </div>
      <div class="parts-editor-head" style="margin-top: 14px;">
        <strong>步骤候选</strong>
        <el-button size="small" @click="appendParsePageProcedure">新增步骤</el-button>
      </div>
      <div v-for="(item, index) in parsePageEditorForm.procedures_json" :key="`procedure-${index}`" class="manual-step-row">
        <el-input-number v-model="item.step_order" :min="1" style="width: 90px" />
        <el-input v-model="item.instruction" placeholder="步骤内容" style="width: 260px" />
        <el-input v-model="item.required_tools" placeholder="工具" style="width: 130px" />
        <el-input v-model="item.torque_spec" placeholder="扭矩/规格" style="width: 120px" />
        <el-input v-model="item.page_number" placeholder="页码" style="width: 100px" />
        <el-input v-model="item.hazards" placeholder="注意事项" style="width: 180px" />
        <el-button link type="danger" @click="parsePageEditorForm.procedures_json.splice(index, 1)">移除</el-button>
      </div>
      <template #footer>
        <el-button @click="parsePageEditorVisible = false">取消</el-button>
        <el-button type="primary" :loading="parseResultSaving" @click="saveParsePageEditor">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import request from '../utils/request'
import { applyAppSettings, createAppSettingsState } from '../composables/appSettings'
import { createPageFeedbackState } from '../composables/pageFeedback'
import { EMPTY_TEXT, TABLE_LOADING_TEXT } from '../constants/uiState'

const route = useRoute()
const router = useRouter()
const activeTab = ref('vehicle')
const syncing = ref(false)
const vehicleLoading = ref(false)
const partLoading = ref(false)
const serviceLoading = ref(false)
const servicePartSyncing = ref(false)
const servicePartSyncingItemId = ref(null)
const servicePackageLoading = ref(false)
const vehicleSaving = ref(false)
const partSaving = ref(false)
const serviceItemSaving = ref(false)
const servicePackageSaving = ref(false)

const vehicleRows = ref([])
const vehicleBrands = ref([])
const vehicleBrandModels = ref([])
const vehicleCategories = ref([])
const vehiclePager = reactive({ page: 1, size: 50, total: 0 })
const vehicleFilters = reactive({ brand: '', model_name: '', category: '', keyword: '' })
const vehicleDialogVisible = ref(false)
const vehicleDetailVisible = ref(false)
const vehicleForm = reactive({ id: null, brand: '', model_name: '', year_from: new Date().getFullYear(), year_to: new Date().getFullYear(), displacement_cc: null, category: '', fuel_type: 'gasoline', default_engine_code: '' })
const vehicleDetail = reactive({ id: null, brand: '', model_name: '', year_from: null, year_to: null })
const appSettings = reactive(createAppSettingsState())
const { pageError, clearPageError, setPageError } = createPageFeedbackState()
const serviceItems = ref([])
const servicePackages = ref([])
const vehicleSpecs = ref([])
const vehicleSpecDialogVisible = ref(false)
const vehicleSpecSaving = ref(false)
const vehicleSpecForm = reactive({ id: null, spec_key: '', spec_label: '', spec_type: '', spec_value: '', spec_unit: '', source_page: '', source_text: '', review_status: 'confirmed', source: 'manual', notes: '' })
const serviceItemDialogVisible = ref(false)
const serviceItemForm = reactive({ id: null, service_name: '', service_code: '', labor_hours: null, labor_price: 80, suggested_price: 0, repair_method: '', notes: '', required_parts: [] })
const servicePackageDialogVisible = ref(false)
const servicePackageForm = reactive({ id: null, package_name: '', package_code: '', description: '', recommended_interval_km: null, recommended_interval_months: null, service_item_ids: [] })
const manualProcedures = ref([])
const knowledgeSegments = ref([])
const segmentFilters = reactive({ chapter: '', keyword: '' })
const serviceManualLocatorVisible = ref(false)
const currentServiceManualItem = ref(null)
const serviceManualMatches = ref([])
const manualProcedureDialogVisible = ref(false)
const manualStepDialogVisible = ref(false)
const manualSaving = ref(false)
const documentSaving = ref(false)
const currentManualProcedure = ref(null)
const manualProcedureForm = reactive({ id: null, name: '', description: '' })
const manualStepForm = reactive({ steps: [] })
const knowledgeDocuments = ref([])
const libraryDocuments = ref([])
const libraryLoading = ref(false)
const libraryQuickFilter = ref('all')
const documentCategories = ['维修手册', '扭矩表', '线路图', '保养标准', '故障诊断']
const libraryFilters = reactive({ category: '', parse_status: '', review_status: '', keyword: '' })
const parsingDocumentId = ref(null)
const parseResultDialogVisible = ref(false)
const parseResultLoading = ref(false)
const parseResultDetail = ref(null)
const parseViewTab = ref('overview')
const selectedParsePage = ref(null)
const importingParseResult = ref(false)
const importingCatalogModel = ref(false)
const importingConfirmedSpecs = ref(false)
const catalogConfirmationDialogVisible = ref(false)
const catalogConfirmationMode = ref('existing')
const catalogConfirmationSaving = ref(false)
const catalogConfirmationForm = reactive({ model_id: null, brand: '', model_name: '', year_from: null, year_to: null, displacement_cc: null, default_engine_code: '', category: '街车/跑车', notes: '' })
const parseResultSaving = ref(false)
const vehicleRecognitionEditorVisible = ref(false)
const resultListEditorVisible = ref(false)
const resultListEditorType = ref('sections')
const resultListEditorTitle = ref('编辑识别结果')
const resultListEditorRows = ref([])
const parsePageEditorVisible = ref(false)
const vehicleRecognitionForm = reactive({ brand: '', model_name: '', year_range: '', engine_code: '', source_pages_text: '' })
const parsePageEditorForm = reactive({ id: null, page_number: null, summary: '', text_content: '', specs_json: [], procedures_json: [] })
let parseResultPollingTimer = null
let libraryPollingTimer = null
const documentDialogVisible = ref(false)
const documentFileInput = ref(null)
const documentForm = reactive({ title: '', category: '维修手册', notes: '' })

const partRows = ref([])
const partOptions = ref([])
const partCategories = ref([])
const partPager = reactive({ page: 1, size: 50, total: 0 })
const partFilters = reactive({ category: '', keyword: '' })
const partDialogVisible = ref(false)
const partForm = reactive({ id: null, part_no: '', name: '', brand: '', category: '', unit: '件', min_stock: 0, sale_price: 0, cost_price: 0, stock_qty: 0, supplier_name: '' })
const normalizedStoreName = computed(() => String(appSettings.store_name || '').trim() || '机车博士')
const inventoryHeadText = computed(() => `这里统一维护 ${normalizedStoreName.value} 的标准车型、标准项目、标准配件和标准资料，是全系统唯一的标准口径来源。`)
const vehicleWorkbenchText = computed(() => '品牌、年款、标准项目和套餐都从这里展开。')
const partWorkbenchText = computed(() => '先补料号、售价和兼容关系，工单金额才会更准。')
const documentWorkbenchText = computed(() => `优先确认 ${normalizedStoreName.value} 的车型归属和审核状态，后面标准作业卡才能稳定入库。`)
const processingWorkbenchText = computed(() => '解析中的手册会自动刷新，点进去就能直接看进度。')
const vehicleDomainText = computed(() => `统一品牌、车型、年份、标准项目、资料和套餐。${normalizedStoreName.value} 的实际到店车辆请到客户库录入。`)
const partDomainText = computed(() => '料号、库存、售价、兼容车型和手册识别出的配件型号都统一沉淀在这里。')
const documentDomainText = computed(() => '维修手册、章节分段、OCR 结果和审核状态都统一从这里进入。')

const vehicleDetailTitle = computed(() => vehicleDetail.id ? `${vehicleDetail.brand} ${vehicleDetail.model_name} 的标准项目` : '标准项目')
const manualStepDialogTitle = computed(() => currentManualProcedure.value ? `编辑步骤：${currentManualProcedure.value.name}` : '编辑步骤')
const serviceManualLocatorTitle = computed(() => currentServiceManualItem.value ? `手册定位：${currentServiceManualItem.value.service_name}` : '手册定位')
const recognizedCatalogCandidate = computed(() => {
  const documentCandidate = parseResultDocument.value?.catalog_candidate || {}
  const parsedCandidate = parseResultDetail.value?.raw_result_json?.normalized_manual?.applicability || {}
  return {
    ...documentCandidate,
    ...parsedCandidate,
    brand: parsedCandidate.brand || documentCandidate.brand || '',
    model_name: parsedCandidate.model_name || documentCandidate.model_name || '',
    year_range: parsedCandidate.year_range || documentCandidate.year_range || '',
    engine_code: parsedCandidate.engine_code || documentCandidate.engine_code || '',
    source_pages: parsedCandidate.source_pages || documentCandidate.source_pages || []
  }
})
const parseResultConfirmedModel = computed(() => parseResultDocument.value?.catalog_confirmed_model_info || null)
const parseResultSuggestedModel = computed(() => parseResultDocument.value?.model_info || null)
const isCatalogConfirmed = computed(() => (parseResultDocument.value?.catalog_confirmation_status || 'pending_confirmation') === 'confirmed')
const canConfirmCurrentCatalog = computed(() => Boolean(parseResultDocument.value?.id && parseResultDocument.value?.model_id))
const canCreateCatalogFromCandidate = computed(() => Boolean(recognizedCatalogCandidate.value?.brand && recognizedCatalogCandidate.value?.model_name))
const canMaterializeSegments = computed(() => Boolean(parseResultDetail.value?.id && isCatalogConfirmed.value))
const canImportConfirmedSpecs = computed(() => Boolean(parseResultDetail.value?.id && isCatalogConfirmed.value))
const existingCatalogModelOptions = computed(() => {
  const rows = vehicleRows.value || []
  return rows.map((item) => ({
    id: item.id,
    label: `${item.brand} ${item.model_name} (${item.year_from}-${item.year_to})`
  }))
})
const tocSegments = computed(() => parseResultDetail.value?.raw_result_json?.normalized_manual?.toc_segments || parseResultDetail.value?.raw_result_json?.normalized_manual?.traceability?.toc_segments || [])
const parsedProcedures = computed(() => {
  const detail = parseResultDetail.value
  if (!detail) return []
  const raw = detail.raw_result_json || {}
  const normalized = raw.normalized_manual || {}
  const fromNormalized = normalized.procedures?.steps || []
  if (fromNormalized.length) return fromNormalized
  const fromSummary = detail.summary_json?.procedures || []
  if (fromSummary.length) return fromSummary
  return (detail.pages || []).flatMap((page) => page.procedures_json || [])
})
const groupedSpecCards = computed(() => {
  const specs = parseResultDetail.value?.summary_json?.specs || []
  const groups = [
    { key: 'torque', label: '扭矩', aliases: ['torque'] },
    { key: 'fluid', label: '油液/容量', aliases: ['capacity', 'fluid'] },
    { key: 'pressure', label: '胎压/压力', aliases: ['pressure'] },
    { key: 'electrical', label: '电气', aliases: ['voltage', 'electrical'] },
    { key: 'clearance', label: '间隙', aliases: ['clearance'] },
    { key: 'other', label: '其他', aliases: [] }
  ]
  const bucketed = groups.map((group) => ({ ...group, items: [] }))
  for (const item of specs) {
    const type = String(item?.type || '').toLowerCase()
    const target = bucketed.find((group) => group.aliases.includes(type)) || bucketed.find((group) => group.key === 'other')
    target.items.push(item)
  }
  return bucketed.filter((group) => group.items.length)
})
const groupedProcedureCards = computed(() => {
  const source = parsedProcedures.value || []
  const groups = [
    { key: 'removal', label: '拆卸步骤', items: [] },
    { key: 'installation', label: '安装步骤', items: [] },
    { key: 'inspection', label: '检查步骤', items: [] },
    { key: 'adjustment', label: '调整步骤', items: [] },
    { key: 'other', label: '其他步骤', items: [] }
  ]
  for (const item of source) {
    const text = `${item?.instruction || ''} ${item?.hazards || ''}`.toLowerCase()
    let targetKey = 'other'
    if (/(拆|remove|disassemble|松开|卸下)/i.test(text)) targetKey = 'removal'
    else if (/(装|install|assemble|复位|装回)/i.test(text)) targetKey = 'installation'
    else if (/(查|inspect|check|检测|确认)/i.test(text)) targetKey = 'inspection'
    else if (/(调|adjust|set|校准|张紧)/i.test(text)) targetKey = 'adjustment'
    const target = groups.find((group) => group.key === targetKey)
    target.items.push(item)
  }
  return groups.filter((group) => group.items.length)
})
const technicianView = computed(() => parseResultDetail.value?.raw_result_json?.normalized_manual?.technician_view || {})
const technicianQuickReference = computed(() => technicianView.value?.quick_reference || {})
const technicianStepCards = computed(() => {
  const cards = technicianView.value?.step_cards || parseResultDetail.value?.raw_result_json?.normalized_manual?.procedures?.step_cards || []
  return Array.isArray(cards) ? cards : []
})
const technicianCriticalSteps = computed(() => technicianStepCards.value.filter((item) => String(item?.criticality || '').toLowerCase() === 'critical'))
const technicianTorqueSpecs = computed(() => {
  const rows = technicianQuickReference.value?.torque
    || parseResultDetail.value?.raw_result_json?.normalized_manual?.specifications?.top_torque_specs
    || parseResultDetail.value?.raw_result_json?.normalized_manual?.specifications?.torque_specs
    || []
  return Array.isArray(rows) ? rows : []
})
const technicianFluidSpecs = computed(() => {
  const rows = technicianQuickReference.value?.fluids
    || parseResultDetail.value?.raw_result_json?.normalized_manual?.specifications?.fluid_specs
    || []
  return Array.isArray(rows) ? rows : []
})
const technicianFilterRows = computed(() => {
  const rows = technicianQuickReference.value?.filters
    || parseResultDetail.value?.raw_result_json?.normalized_manual?.parts_and_materials?.filters
    || []
  return Array.isArray(rows) ? rows : []
})
const technicianFastenerRows = computed(() => {
  const rows = technicianQuickReference.value?.fasteners
    || parseResultDetail.value?.raw_result_json?.normalized_manual?.specifications?.fastener_specs
    || []
  return Array.isArray(rows) ? rows : []
})
const technicianToolRows = computed(() => {
  const rows = technicianQuickReference.value?.tools
    || parseResultDetail.value?.raw_result_json?.normalized_manual?.procedures?.required_tools
    || []
  if (!Array.isArray(rows)) return []
  return rows.map((item) => (typeof item === 'string' ? { name: item } : item)).filter((item) => item?.name)
})
const technicianMaterialRows = computed(() => {
  const rows = parseResultDetail.value?.raw_result_json?.normalized_manual?.parts_and_materials?.consumables || []
  return Array.isArray(rows) ? rows : []
})
const selectedParsePageDetail = computed(() => {
  const pageNo = Number(selectedParsePage.value || 0)
  if (!pageNo) return null
  return (parseResultDetail.value?.pages || []).find((item) => Number(item.page_number) === pageNo) || null
})
const selectedParsePageSegments = computed(() => {
  const rows = selectedParsePageDetail.value?.content_segments || []
  return Array.isArray(rows) ? rows : []
})
const selectedParsePageSpecTableRows = computed(() => {
  const rows = selectedParsePageDetail.value?.spec_table_rows || []
  return Array.isArray(rows) ? rows : []
})
const pageTypeText = (value) => ({
  cover: '封面页',
  preface: '前言页',
  index: '目录/索引页',
  legend: '符号说明页',
  spec_table: '参数表页',
  procedure: '施工步骤页',
  general: '普通内容页'
}[String(value || '').toLowerCase()] || '未分类')
const parseResultDocument = computed(() => {
  const documentId = Number(parseResultDetail.value?.document_id || 0)
  if (!documentId) return null
  return libraryDocuments.value.find((item) => Number(item.id) === documentId) || knowledgeDocuments.value.find((item) => Number(item.id) === documentId) || null
})
const quickOverview = computed(() => {
  const detail = parseResultDetail.value || {}
  const recognized = recognizedCatalogCandidate.value || {}
  const completionRatio = Number(detail?.raw_result_json?.manual_template?.completion_ratio || 0)
  const pages = detail?.pages || []
  const highlights = []
  const gaps = []
  const specCount = Number(detail?.summary_json?.specs?.length || detail?.extracted_specs || 0)
  const procedureCount = Number(parsedProcedures.value?.length || 0)
  const groupedSpecs = groupedSpecCards.value || []
  const groupedSteps = groupedProcedureCards.value || []
  const pageTypeMap = new Map()
  pages.forEach((item) => {
    const key = String(item?.page_type || 'general').toLowerCase()
    pageTypeMap.set(key, Number(pageTypeMap.get(key) || 0) + 1)
  })
  const pageTypeSummary = Array.from(pageTypeMap.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 4)
    .map(([key, count]) => `${pageTypeText(key)}${count}`)
    .join(' / ') || '暂无'

  const suggestedModel = parseResultSuggestedModel.value
  const modelLabel = [recognized.brand, recognized.model_name].filter(Boolean).join(' ')
    || (suggestedModel ? `${suggestedModel.brand} ${suggestedModel.model_name}（当前挂载）` : '待识别')
  if (recognized.brand && recognized.model_name) highlights.push(`已识别车型：${modelLabel}`)
  else gaps.push('品牌或车型未稳定识别')

  if (completionRatio >= 0.8) highlights.push('模板覆盖较完整')
  else if (completionRatio > 0) gaps.push('模板覆盖仍需补全')
  else gaps.push('模板覆盖尚未形成')

  if (specCount) highlights.push(`已提取 ${specCount} 条规格候选`)
  else gaps.push('关键规格尚未识别')

  if (procedureCount) highlights.push(`已提取 ${procedureCount} 条步骤候选`)
  else gaps.push('施工步骤尚未识别')

  if (!recognized.year_range) gaps.push('年款范围待确认')
  if (!recognized.engine_code) gaps.push('发动机代码待确认')

  const canBindCatalog = Boolean(recognized.brand && recognized.model_name)
  const canImportManual = Boolean(procedureCount)
  const readinessItems = [
    {
      key: 'catalog',
      label: '确认车型',
      ready: isCatalogConfirmed.value,
      reason: isCatalogConfirmed.value ? '车型已确认，可继续生成分段和入库' : (canBindCatalog ? '已识别出候选车型，等待你确认' : '品牌或车型仍未稳定识别')
    },
    {
      key: 'manual',
      label: '导入维修条目',
      ready: isCatalogConfirmed.value && canImportManual,
      reason: !isCatalogConfirmed.value ? '需要先确认车型' : (canImportManual ? `已识别 ${procedureCount} 条步骤` : '还没有可用的施工步骤')
    },
    {
      key: 'template',
      label: '进入标准库',
      ready: completionRatio >= 0.6 && isCatalogConfirmed.value,
      reason: completionRatio >= 0.6 && isCatalogConfirmed.value ? '模板覆盖已达到基础入库要求' : '车型未确认或模板覆盖仍需补全'
    }
  ]

  return {
    modelLabel,
    templateCompletion: `${Math.round(completionRatio * 100)}%`,
    specSummary: groupedSpecs.length ? groupedSpecs.map((item) => `${item.label}${item.items.length}`).join(' / ') : '暂无',
    procedureSummary: groupedSteps.length ? groupedSteps.map((item) => `${item.label}${item.items.length}`).join(' / ') : '暂无',
    pageTypeSummary,
    highlights,
    gaps: gaps.slice(0, 6),
    pageCount: pages.length,
    readinessItems
  }
})
const canBindParseResultToCatalog = computed(() => {
  const recognized = recognizedCatalogCandidate.value || {}
  return Boolean(parseResultDetail.value?.id && recognized.brand && recognized.model_name)
})
const canImportParseResultToManual = computed(() => Boolean(vehicleDetail.id && parsedProcedures.value.length && isCatalogConfirmed.value))
const parseStatusText = (status) => ({ pending: '待解析', queued: '排队中', processing: '解析中', completed: '已完成', failed: '失败' }[status] || '未解析')
const parseStatusTagType = (status) => ({ pending: 'info', queued: 'info', processing: 'warning', completed: 'success', failed: 'danger' }[status] || 'info')
const reviewStatusText = (status) => ({ pending_review: '待审核', confirmed: '已确认', needs_fix: '需补录' }[status] || '待审核')
const reviewStatusTagType = (status) => ({ pending_review: 'info', confirmed: 'success', needs_fix: 'warning' }[status] || 'info')
const catalogConfirmationStatusText = (status) => ({ pending_confirmation: '待确认车型', confirmed: '已确认车型' }[status] || '待确认车型')
const catalogConfirmationStatusTagType = (status) => ({ pending_confirmation: 'warning', confirmed: 'success' }[status] || 'warning')
const itemReviewText = (status) => ({ pending_review: '待审核', confirmed: '已确认', ignored: '已忽略' }[status] || '待审核')
const itemReviewTagType = (status) => ({ pending_review: 'info', confirmed: 'success', ignored: 'warning' }[status] || 'info')
const extractLibraryRecognized = (row) => row?.latest_parse_job?.raw_result_json?.normalized_manual?.applicability || {}
const extractLibraryTemplateRatio = (row) => Number(row?.latest_parse_job?.raw_result_json?.manual_template?.completion_ratio || 0)
const extractLibraryProcedures = (row) => {
  const raw = row?.latest_parse_job?.raw_result_json || {}
  const normalized = raw.normalized_manual || {}
  const normalizedSteps = normalized.procedures?.steps || []
  if (normalizedSteps.length) return normalizedSteps
  return row?.latest_parse_job?.summary_json?.procedures || []
}
const libraryOverview = (row) => {
  const recognized = extractLibraryRecognized(row)
  const ratio = extractLibraryTemplateRatio(row)
  const specs = Number(row?.latest_parse_job?.summary_json?.specs?.length || row?.latest_parse_job?.extracted_specs || 0)
  const procedures = extractLibraryProcedures(row).length
  return {
    modelLabel: [recognized.brand, recognized.model_name].filter(Boolean).join(' ') || '待识别',
    templateCompletion: `${Math.round(ratio * 100)}%`,
    specSummary: `规格 ${specs} / 步骤 ${procedures}`
  }
}
const pendingReviewDocumentCount = computed(() => (libraryDocuments.value || []).filter((row) => (row?.review_status || 'pending_review') === 'pending_review').length)
const processingDocumentCount = computed(() => (libraryDocuments.value || []).filter((row) => ['queued', 'processing'].includes(row?.latest_parse_job?.status || 'pending')).length)
const readyDocumentCount = computed(() => (libraryDocuments.value || []).filter((row) => {
  const readiness = libraryReadiness(row)
  return readiness.every((item) => item.ready)
}).length)
const libraryReadiness = (row) => {
  const recognized = extractLibraryRecognized(row)
  const ratio = extractLibraryTemplateRatio(row)
  const procedures = extractLibraryProcedures(row).length
  const confirmed = (row?.catalog_confirmation_status || 'pending_confirmation') === 'confirmed'
  return [
      { key: 'catalog', label: '标准车型确认', ready: confirmed },
    { key: 'manual', label: '维修条目', ready: confirmed && procedures > 0 },
    { key: 'standard', label: '标准库', ready: confirmed && ratio >= 0.6 }
  ]
}
const focusWorkbench = (action) => {
  if (action === 'vehicle-create') {
    activeTab.value = 'vehicle'
    openVehicleDialog()
    return
  }
  if (action === 'part-create') {
    activeTab.value = 'parts'
    openPartDialog()
    return
  }
  if (action === 'documents-pending') {
    activeTab.value = 'documents'
    applyLibraryQuickFilter('pending_review')
    return
  }
  if (action === 'documents-processing') {
    activeTab.value = 'documents'
    applyLibraryQuickFilter('processing')
  }
}
const openLibraryRow = (row) => {
  if (row?.latest_parse_job) {
    openParseResultDialog(row)
    return
  }
  openKnowledgeDocument(row)
}
const libraryPriorityScore = (row) => {
  const parseStatus = row?.latest_parse_job?.status || 'pending'
  const reviewStatus = row?.review_status || 'pending_review'
  const readiness = libraryReadiness(row)
  const readyCount = readiness.filter((item) => item.ready).length
  if (parseStatus === 'processing' || parseStatus === 'queued') return 0
  if (reviewStatus === 'pending_review' && readyCount > 0) return 1
  if (reviewStatus === 'needs_fix') return 2
  if (parseStatus === 'failed') return 3
  if (reviewStatus === 'pending_review') return 4
  return 5
}
const formatBatchProgress = (job) => {
  const processed = Number(job?.processed_batches || 0)
  const total = Number(job?.total_batches || 0)
  if (!total) return '等待统计'
  return `${processed}/${total} 批`
}
const formatParseProgress = (job) => {
  const percent = Number(job?.progress_percent || 0)
  const message = job?.progress_message || ''
  const batch = formatBatchProgress(job)
  return `${percent}% · ${batch}${message ? ` · ${message}` : ''}`
}
const normalizePageNumber = (value) => {
  if (Array.isArray(value)) return value.map((item) => normalizePageNumber(item)).filter(Boolean).join('、')
  const text = String(value ?? '').trim()
  return text || ''
}
const parseSourcePagesText = (value) => {
  const raw = String(value || '')
  return raw.split(/[,，、/\s]+/).map((item) => item.trim()).filter(Boolean)
}
const formatPageText = (item) => {
  if (!item) return '-'
  const candidates = [
    item.page_number,
    item.page_no,
    item.page,
    item.page_label,
    item.source_page,
    item.source_pages
  ]
  for (const candidate of candidates) {
    const text = normalizePageNumber(candidate)
    if (text) return text.startsWith('第') || text.includes('页') ? text : `第 ${text} 页`
  }
  return '-'
}
const formatValueUnit = (value, unit) => {
  const joined = [value, unit].filter(Boolean).join(' ')
  return joined || '-'
}
const formatSimpleList = (rows) => {
  if (!Array.isArray(rows)) return '-'
  return rows.filter(Boolean).join('；') || '-'
}
const formatSegmentRole = (value) => ({
  title: '标题',
  procedure: '步骤',
  spec: '参数',
  note: '说明'
}[String(value || '').toLowerCase()] || '未分类')
const formatCriticality = (value) => ({
  critical: '关键步骤',
  major: '重点步骤',
  normal: '常规步骤'
}[String(value || '').toLowerCase()] || '常规步骤')
const stepCriticalityTagType = (value) => ({
  critical: 'danger',
  major: 'warning',
  normal: ''
}[String(value || '').toLowerCase()] || '')
const formatActionType = (value) => ({
  removal: '拆卸/拆下',
  installation: '安装/回装',
  tightening: '紧固',
  inspection: '检查/确认',
  adjustment: '调整/校准',
  filling: '加注/补充',
  cleaning: '清洁',
  operation: '一般作业'
}[String(value || '').toLowerCase()] || '-')
const normalizeNamedRows = (value) => {
  if (!Array.isArray(value)) return []
  return value.map((item) => (typeof item === 'string' ? { name: item } : item)).filter(Boolean)
}
const formatNamedRows = (rows) => {
  const list = normalizeNamedRows(rows).map((item) => item.name ? formatTranslatedValue(item.name, item.name_zh) : formatValueUnit(item.value, item.unit)).filter(Boolean)
  return list.join('、') || '-'
}
const formatToolNames = (rows) => {
  const list = normalizeNamedRows(rows).map((item) => item.name ? formatTranslatedValue(item.name, item.name_zh) : '').filter(Boolean)
  return list.join('、') || '-'
}
const formatTranslatedValue = (original, zh) => {
  const translated = String(zh || '').trim()
  const source = String(original || '').trim()
  return translated || source || '-'
}
const formatTorqueRows = (rows) => {
  if (!Array.isArray(rows)) return '-'
  return rows.map((item) => `${item.label || '扭矩'} ${formatValueUnit(item.value, item.unit)}`).join('；') || '-'
}
const formatFastenerRows = (rows) => {
  if (!Array.isArray(rows)) return '-'
  return rows.map((item) => [formatTranslatedValue(item.name, item.name_zh), item.size, item.drive_type].filter(Boolean).join(' / ')).join('；') || '-'
}
const cloneRow = (item) => JSON.parse(JSON.stringify(item || {}))
const saveParseResultPatch = async (payload, successText = '识别结果已保存') => {
  if (!parseResultDetail.value?.id) return
  parseResultSaving.value = true
  try {
    parseResultDetail.value = await request.patch(`/mp/knowledge/parse-jobs/${parseResultDetail.value.id}/result`, payload)
    ElMessage.success(successText)
    await Promise.all([loadKnowledgeDocuments(), loadLibraryDocuments()])
  } finally {
    parseResultSaving.value = false
  }
}
const markSpecItemStatus = async (groupKey, index, status) => {
  const groups = groupedSpecCards.value || []
  const group = groups.find((item) => item.key === groupKey)
  if (!group) return
  const target = group.items[index]
  if (!target) return
  const specs = (parseResultDetail.value?.summary_json?.specs || []).map((item) => {
    const same = item === target || (
      item?.label === target?.label &&
      String(item?.value || '') === String(target?.value || '') &&
      String(item?.page_number || '') === String(target?.page_number || '')
    )
    return same ? { ...item, review_status: status } : item
  })
  await saveParseResultPatch({ specs }, `规格已标记为${itemReviewText(status)}`)
}
const markProcedureItemStatus = async (groupKey, index, status) => {
  const groups = groupedProcedureCards.value || []
  const group = groups.find((item) => item.key === groupKey)
  if (!group) return
  const target = group.items[index]
  if (!target) return
  const procedures = parsedProcedures.value.map((item) => {
    const same = item === target || (
      Number(item?.step_order || 0) === Number(target?.step_order || 0) &&
      String(item?.instruction || '') === String(target?.instruction || '') &&
      String(item?.page_number || '') === String(target?.page_number || '')
    )
    return same ? { ...item, review_status: status } : item
  })
  await saveParseResultPatch({ procedures }, `步骤已标记为${itemReviewText(status)}`)
}

const loadVehicleBrands = async () => { vehicleBrands.value = await request.get('/mp/catalog/vehicle-models/brands') }
const loadVehicleCategories = async () => { vehicleCategories.value = await request.get('/mp/catalog/vehicle-models/categories') }
const loadParts = async () => {
  partLoading.value = true
  try {
    const res = await request.get('/mp/catalog/parts', { params: { page: partPager.page, size: partPager.size, category: partFilters.category || '', keyword: partFilters.keyword || '' } })
    clearPageError()
    partRows.value = res?.items || []
    partOptions.value = partRows.value
    partPager.total = Number(res?.total || 0)
  } catch (error) {
    setPageError('加载标准配件库失败，请稍后重试', error)
    ElMessage.error(error?.message || '加载标准配件库失败')
  } finally { partLoading.value = false }
}
const loadPartCategories = async () => { partCategories.value = await request.get('/mp/catalog/parts/categories') }
const loadVehicleModelsByBrand = async (brand) => {
  if (!brand) { vehicleBrandModels.value = []; return }
  vehicleBrandModels.value = await request.get('/mp/catalog/vehicle-models/by-brand', { params: { brand } })
}
const loadVehicleModels = async () => {
  vehicleLoading.value = true
  try {
    const res = await request.get('/mp/catalog/vehicle-models', { params: { page: vehiclePager.page, size: vehiclePager.size, brand: vehicleFilters.brand || '', model_name: vehicleFilters.model_name || '', category: vehicleFilters.category || '', keyword: vehicleFilters.keyword || '' } })
    clearPageError()
    vehicleRows.value = res?.items || []
    vehiclePager.total = Number(res?.total || 0)
  } catch (error) {
    setPageError('加载标准车型库失败，请稍后重试', error)
    ElMessage.error(error?.message || '加载标准车型库失败')
  } finally { vehicleLoading.value = false }
}
const loadServiceItems = async () => {
  if (!vehicleDetail.id) return
  serviceLoading.value = true
  try { serviceItems.value = await request.get(`/mp/catalog/vehicle-models/${vehicleDetail.id}/service-items`) } finally { serviceLoading.value = false }
}
const loadServicePackages = async () => {
  if (!vehicleDetail.id) return
  servicePackageLoading.value = true
  try { servicePackages.value = await request.get(`/mp/catalog/vehicle-models/${vehicleDetail.id}/service-packages`) } finally { servicePackageLoading.value = false }
}
const loadVehicleSpecs = async () => {
  if (!vehicleDetail.id) return
  vehicleSpecs.value = await request.get(`/mp/catalog/vehicle-models/${vehicleDetail.id}/specs`)
}
const loadManualProcedures = async () => {
  if (!vehicleDetail.id) return
  manualProcedures.value = await request.get(`/mp/knowledge/catalog-models/${vehicleDetail.id}/procedures`)
}
const loadKnowledgeSegments = async () => {
  if (!vehicleDetail.id) return
  knowledgeSegments.value = await request.get(`/mp/knowledge/catalog-models/${vehicleDetail.id}/segments`)
}
const segmentChapterOptions = computed(() => {
  const values = new Set()
  for (const item of knowledgeSegments.value || []) {
    const chapter = String(item?.chapter_no || '').trim()
    if (chapter) values.add(chapter)
  }
  return [...values].sort((a, b) => a.localeCompare(b, 'zh-CN', { numeric: true }))
})
const filteredKnowledgeSegments = computed(() => {
  const keyword = String(segmentFilters.keyword || '').trim().toLowerCase()
  const chapter = String(segmentFilters.chapter || '').trim()
  const rows = (knowledgeSegments.value || []).filter((item) => {
    if (chapter && String(item?.chapter_no || '') !== chapter) return false
    return true
  })
  if (!keyword) {
    return rows
  }
  return rows
    .map((item) => {
      const title = String(item?.title || '').toLowerCase()
      const chapterNo = String(item?.chapter_no || '').toLowerCase()
      const segmentTitle = String(item?.segment_document?.title || '').toLowerCase()
      const procedureName = String(item?.procedure?.name || '').toLowerCase()
      const stepsText = (item?.procedure?.steps || []).map((step) => String(step?.instruction || '').toLowerCase()).join(' ')
      const haystack = [title, chapterNo, segmentTitle, procedureName, stepsText].filter(Boolean).join(' ')
      if (!haystack.includes(keyword)) return null
      let score = 0
      if (title === keyword) score += 120
      else if (title.startsWith(keyword)) score += 80
      else if (title.includes(keyword)) score += 55
      if (chapterNo === keyword) score += 110
      else if (chapterNo.startsWith(keyword)) score += 65
      if (procedureName === keyword) score += 95
      else if (procedureName.startsWith(keyword)) score += 60
      else if (procedureName.includes(keyword)) score += 40
      if (segmentTitle.includes(keyword)) score += 28
      if (stepsText.includes(keyword)) score += 12
      const tokens = tokenizeManualText(keyword)
      for (const token of tokens) {
        if (title.includes(token)) score += 16
        else if (procedureName.includes(token)) score += 12
        else if (stepsText.includes(token)) score += 5
      }
      return { item, score }
    })
    .filter(Boolean)
    .sort((a, b) => {
      if (b.score !== a.score) return b.score - a.score
      return Number(a.item?.start_page || 0) - Number(b.item?.start_page || 0)
    })
    .map((entry) => entry.item)
})
const servicePackagePreview = computed(() => {
  const ids = new Set((servicePackageForm.service_item_ids || []).map((item) => Number(item)))
  const items = (serviceItems.value || []).filter((item) => ids.has(Number(item.id)))
  const labor_hours_total = items.reduce((sum, item) => sum + Number(item.labor_hours || 0), 0)
  const labor_price_total = items.reduce((sum, item) => sum + Number(item.labor_price || 0), 0)
  const parts_price_total = items.reduce(
    (sum, item) => sum + (item.required_parts || []).reduce((acc, part) => acc + (Number(part.unit_price || 0) * Number(part.qty || 0)), 0),
    0
  )
  const suggested_price_total = items.reduce((sum, item) => sum + Number(item.suggested_price || 0), 0)
  return { items, labor_hours_total, labor_price_total, parts_price_total, suggested_price_total }
})
const tokenizeManualText = (value) => {
  const text = String(value || '')
  return text
    .split(/[\s,，。；、:：()（）\-_/]+/)
    .map((item) => item.trim().toLowerCase())
    .filter((item) => item && item.length >= 2)
}
const locateServiceManualSegments = (serviceItem) => {
  const serviceName = String(serviceItem?.service_name || '').trim().toLowerCase()
  const repairMethod = String(serviceItem?.repair_method || '').trim().toLowerCase()
  const keywords = Array.from(new Set([
    ...tokenizeManualText(serviceItem?.service_name),
    ...tokenizeManualText(serviceItem?.repair_method),
    ...tokenizeManualText(serviceItem?.notes)
  ]))
  const rows = []
  for (const segment of knowledgeSegments.value || []) {
    const title = String(segment?.title || '').toLowerCase()
    const docTitle = String(segment?.segment_document?.title || '').toLowerCase()
    const procedureName = String(segment?.procedure?.name || '').toLowerCase()
    const stepsText = (segment?.procedure?.steps || []).map((step) => String(step?.instruction || '').toLowerCase()).join(' ')
    const haystack = [title, docTitle, procedureName, stepsText].filter(Boolean).join(' ')
    const matched = keywords.filter((keyword) => haystack.includes(keyword))
    let score = matched.length
    if (serviceName && title === serviceName) score += 120
    else if (serviceName && title.startsWith(serviceName)) score += 75
    else if (serviceName && title.includes(serviceName)) score += 42
    if (serviceName && procedureName === serviceName) score += 105
    else if (serviceName && procedureName.startsWith(serviceName)) score += 68
    else if (serviceName && procedureName.includes(serviceName)) score += 38
    if (repairMethod && stepsText.includes(repairMethod)) score += 28
    if (repairMethod && docTitle.includes(repairMethod)) score += 18
    if (matched.length && title.includes(matched[0])) score += 8
    if (matched.length && procedureName.includes(matched[0])) score += 6
    if (segment?.chapter_no && serviceName && String(segment.chapter_no).toLowerCase() === serviceName) score += 40
    if (score > 0) {
      rows.push({
        ...segment,
        _match_score: score,
        _match_reasons: matched.slice(0, 6)
      })
    }
  }
  return rows.sort((a, b) => {
    if (b._match_score !== a._match_score) return b._match_score - a._match_score
    return Number(a.start_page || 0) - Number(b.start_page || 0)
  }).slice(0, 12)
}
const loadKnowledgeDocuments = async () => {
  if (!vehicleDetail.id) return
  knowledgeDocuments.value = await request.get(`/mp/knowledge/catalog-models/${vehicleDetail.id}/documents`)
}
const loadLibraryDocuments = async () => {
  libraryLoading.value = true
  try {
    let rows = await request.get('/mp/knowledge/documents', {
      params: {
        category: libraryFilters.category || '',
        parse_status: libraryFilters.parse_status || '',
        review_status: libraryFilters.review_status || '',
        keyword: libraryFilters.keyword || ''
      }
    })
    rows = [...(rows || [])]
    if (libraryQuickFilter.value === 'ready') {
      rows = rows.filter((row) => libraryReadiness(row).every((item) => item.ready || item.key !== 'manual') && libraryReadiness(row).some((item) => item.key === 'catalog' && item.ready))
    } else if (libraryQuickFilter.value === 'processing') {
      rows = rows.filter((row) => ['queued', 'processing'].includes(row?.latest_parse_job?.status))
    } else if (libraryQuickFilter.value === 'pending_review') {
      rows = rows.filter((row) => (row?.review_status || 'pending_review') === 'pending_review')
    } else if (libraryQuickFilter.value === 'needs_fix') {
      rows = rows.filter((row) => row?.review_status === 'needs_fix')
    }
    libraryDocuments.value = [...(rows || [])].sort((a, b) => libraryPriorityScore(a) - libraryPriorityScore(b))
    clearPageError()
  } catch (error) {
    setPageError('加载标准资料库失败，请稍后重试', error)
    ElMessage.error(error?.message || '加载标准资料库失败')
  } finally {
    libraryLoading.value = false
    ensureLibraryPolling()
  }
}
const retryActiveTabLoad = async () => {
  if (activeTab.value === 'vehicle') return loadVehicleModels()
  if (activeTab.value === 'parts') return loadParts()
  if (activeTab.value === 'documents') return loadLibraryDocuments()
}
const applyLibraryQuickFilter = async (mode) => {
  libraryQuickFilter.value = mode
  libraryFilters.review_status = ''
  libraryFilters.parse_status = ''
  if (mode === 'pending_review') libraryFilters.review_status = 'pending_review'
  else if (mode === 'needs_fix') libraryFilters.review_status = 'needs_fix'
  else if (mode === 'processing') libraryFilters.parse_status = 'processing'
  await loadLibraryDocuments()
}
const onVehicleBrandChange = async () => { vehicleFilters.model_name = ''; await loadVehicleModelsByBrand(vehicleFilters.brand); await loadVehicleModels() }
const resetVehicleFilters = async () => { vehicleFilters.brand = ''; vehicleFilters.model_name = ''; vehicleFilters.category = ''; vehicleFilters.keyword = ''; vehicleBrandModels.value = []; await loadVehicleModels() }
const resetPartFilters = async () => { partFilters.category = ''; partFilters.keyword = ''; await loadParts() }
const resetLibraryFilters = async () => { libraryQuickFilter.value = 'all'; libraryFilters.category = ''; libraryFilters.parse_status = ''; libraryFilters.review_status = ''; libraryFilters.keyword = ''; await loadLibraryDocuments() }
const syncCatalog = async () => { syncing.value = true; try { await request.post('/mp/catalog/sync-defaults'); ElMessage.success('车型基础库已同步'); await Promise.all([loadVehicleBrands(), loadVehicleCategories(), loadVehicleModels(), loadPartCategories(), loadParts()]) } finally { syncing.value = false } }
const loadAppSettings = async () => {
  try {
    const data = await request.get('/mp/settings')
    applyAppSettings(appSettings, data)
  } catch {
    applyAppSettings(appSettings)
  }
}
const handleStoreChanged = async () => {
  await loadAppSettings()
  await Promise.all([loadVehicleBrands(), loadVehicleCategories(), loadVehicleModels(), loadPartCategories(), loadParts(), loadLibraryDocuments()])
}
const openVehicleDialog = (row = null) => {
  Object.assign(vehicleForm, row ? row : { id: null, brand: '', model_name: '', year_from: new Date().getFullYear(), year_to: new Date().getFullYear(), displacement_cc: null, category: '', fuel_type: 'gasoline', default_engine_code: '' })
  vehicleDialogVisible.value = true
}
const saveVehicle = async () => {
  if (!vehicleForm.brand || !vehicleForm.model_name) return ElMessage.warning('请填写品牌和车型')
  vehicleSaving.value = true
  try {
    const payload = { ...vehicleForm, displacement_cc: vehicleForm.displacement_cc == null ? null : Number(vehicleForm.displacement_cc), is_active: true }
    if (vehicleForm.id) await request.put(`/mp/catalog/vehicle-models/${vehicleForm.id}`, payload)
    else await request.post('/mp/catalog/vehicle-models', payload)
    vehicleDialogVisible.value = false
    ElMessage.success('车型已保存')
    await Promise.all([loadVehicleBrands(), loadVehicleCategories(), loadVehicleModels()])
  } finally { vehicleSaving.value = false }
}
const removeVehicle = async (row) => { try { await ElMessageBox.confirm(`确定删除车型【${row.brand} ${row.model_name}】吗？`, '确认删除', { type: 'warning' }) } catch { return } await request.delete(`/mp/catalog/vehicle-models/${row.id}`); ElMessage.success('车型已删除'); await loadVehicleModels() }
const openVehicleDetail = async (row) => {
  Object.assign(vehicleDetail, row)
  segmentFilters.chapter = ''
  segmentFilters.keyword = ''
  vehicleDetailVisible.value = true
  await Promise.all([loadServiceItems(), loadServicePackages(), loadVehicleSpecs(), loadManualProcedures(), loadKnowledgeSegments(), loadKnowledgeDocuments()])
}
const packageIntervalText = (row) => {
  const parts = []
  if (row?.recommended_interval_km) parts.push(`${row.recommended_interval_km} km`)
  if (row?.recommended_interval_months) parts.push(`${row.recommended_interval_months} 个月`)
  return parts.join(' / ') || '未设置'
}
const normalizeSpecKeyText = (value) => {
  const text = String(value || '').trim().toLowerCase()
  return text.replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '') || 'spec'
}
const openVehicleSpecDialog = (row = null) => {
  Object.assign(vehicleSpecForm, row ? {
    id: row.id,
    spec_key: row.spec_key || '',
    spec_label: row.spec_label || '',
    spec_type: row.spec_type || '',
    spec_value: row.spec_value || '',
    spec_unit: row.spec_unit || '',
    source_page: row.source_page || '',
    source_text: row.source_text || '',
    review_status: row.review_status || 'confirmed',
    source: row.source || 'manual',
    notes: row.notes || ''
  } : {
    id: null,
    spec_key: '',
    spec_label: '',
    spec_type: '',
    spec_value: '',
    spec_unit: '',
    source_page: '',
    source_text: '',
    review_status: 'confirmed',
    source: 'manual',
    notes: ''
  })
  vehicleSpecDialogVisible.value = true
}
const saveVehicleSpec = async () => {
  if (!vehicleDetail.id) return
  if (!vehicleSpecForm.spec_label) return ElMessage.warning('请填写参数名称')
  vehicleSpecSaving.value = true
  try {
    const payload = {
      spec_key: normalizeSpecKeyText(vehicleSpecForm.spec_key || vehicleSpecForm.spec_label),
      spec_label: vehicleSpecForm.spec_label,
      spec_type: vehicleSpecForm.spec_type || null,
      spec_value: vehicleSpecForm.spec_value || null,
      spec_unit: vehicleSpecForm.spec_unit || null,
      source_page: vehicleSpecForm.source_page || null,
      source_text: vehicleSpecForm.source_text || null,
      review_status: vehicleSpecForm.review_status || 'confirmed',
      source: vehicleSpecForm.source || 'manual',
      notes: vehicleSpecForm.notes || null
    }
    if (vehicleSpecForm.id) await request.put(`/mp/catalog/vehicle-models/${vehicleDetail.id}/specs/${vehicleSpecForm.id}`, payload)
    else await request.post(`/mp/catalog/vehicle-models/${vehicleDetail.id}/specs`, payload)
    vehicleSpecDialogVisible.value = false
    ElMessage.success('车型参数已保存')
    await loadVehicleSpecs()
  } finally {
    vehicleSpecSaving.value = false
  }
}
const removeVehicleSpec = async (row) => {
  try { await ElMessageBox.confirm(`确定删除参数【${row.spec_label}】吗？`, '确认删除', { type: 'warning' }) } catch { return }
  await request.delete(`/mp/catalog/vehicle-models/${vehicleDetail.id}/specs/${row.id}`)
  ElMessage.success('车型参数已删除')
  await loadVehicleSpecs()
}
const addRequiredPart = () => { serviceItemForm.required_parts.push({ part_id: null, part_name: '', part_no: '', qty: 1, unit_price: 0, notes: '', sort_order: (serviceItemForm.required_parts.length + 1) * 10, is_optional: false }) }
const removeRequiredPart = (index) => { serviceItemForm.required_parts.splice(index, 1) }
const onRequiredPartChange = (row, partId) => { const part = partOptions.value.find((item) => item.id === partId); if (!part) return; row.part_id = part.id; row.part_name = part.name; row.part_no = part.part_no; row.unit_price = Number(part.sale_price || 0) }
const openServiceItemDialog = (row = null) => {
  if (!row) Object.assign(serviceItemForm, { id: null, service_name: '', service_code: '', labor_hours: null, labor_price: Number(appSettings.default_labor_price || 0), suggested_price: 0, repair_method: '', notes: '', required_parts: [] })
  else Object.assign(serviceItemForm, { id: row.id, service_name: row.service_name || '', service_code: row.service_code || '', labor_hours: row.labor_hours ?? null, labor_price: Number(row.labor_price || 0), suggested_price: Number(row.suggested_price || 0), repair_method: row.repair_method || '', notes: row.notes || '', required_parts: (row.required_parts || []).map((item, index) => ({ part_id: item.part_id || null, part_name: item.part_name || '', part_no: item.part_no || '', qty: Number(item.qty || 1), unit_price: Number(item.unit_price || 0), notes: item.notes || '', sort_order: Number(item.sort_order || ((index + 1) * 10)), is_optional: Boolean(item.is_optional) })) })
  serviceItemDialogVisible.value = true
}
const saveServiceItem = async () => {
  if (!vehicleDetail.id) return
  if (!serviceItemForm.service_name) return ElMessage.warning('请填写标准项目名称')
  serviceItemSaving.value = true
  try {
    const payload = { service_name: serviceItemForm.service_name, service_code: serviceItemForm.service_code || null, labor_hours: serviceItemForm.labor_hours == null ? null : Number(serviceItemForm.labor_hours), labor_price: Number(serviceItemForm.labor_price || 0), suggested_price: Number(serviceItemForm.suggested_price || 0), repair_method: serviceItemForm.repair_method || null, notes: serviceItemForm.notes || null, sort_order: 100, is_active: true, required_parts: serviceItemForm.required_parts.map((item, index) => ({ part_id: item.part_id || null, part_no: item.part_no || null, part_name: item.part_name, qty: Number(item.qty || 1), unit_price: Number(item.unit_price || 0), notes: item.notes || null, sort_order: Number(item.sort_order || ((index + 1) * 10)), is_optional: Boolean(item.is_optional) })) }
    if (serviceItemForm.id) await request.put(`/mp/catalog/vehicle-models/${vehicleDetail.id}/service-items/${serviceItemForm.id}`, payload)
    else await request.post(`/mp/catalog/vehicle-models/${vehicleDetail.id}/service-items`, payload)
    serviceItemDialogVisible.value = false
    ElMessage.success('标准项目已保存')
    await loadServiceItems()
  } finally { serviceItemSaving.value = false }
}
const syncServiceItemPartsFromManual = async (row = null) => {
  if (!vehicleDetail.id) return
  if (row?.id) servicePartSyncingItemId.value = row.id
  else servicePartSyncing.value = true
  try {
    const res = await request.post(`/mp/catalog/vehicle-models/${vehicleDetail.id}/service-items/sync-manual-parts`, null, {
      params: row?.id ? { item_id: row.id } : {}
    })
    await Promise.all([loadServiceItems(), loadParts()])
    const synced = Number(res?.synced || 0)
    if (row?.id) {
      ElMessage.success(synced ? `已按手册同步【${row.service_name}】所需配件` : `【${row.service_name}】暂无更具体的手册配件可同步`)
    } else {
      ElMessage.success(synced ? `已同步 ${synced} 个标准项目的所需配件` : '当前没有可更新的手册配件')
    }
  } finally {
    servicePartSyncing.value = false
    servicePartSyncingItemId.value = null
  }
}
const seedServicePackages = async () => {
  if (!vehicleDetail.id) return
  await request.post(`/mp/catalog/vehicle-models/${vehicleDetail.id}/service-packages/seed-defaults`)
  ElMessage.success('推荐服务套餐已生成')
  await loadServicePackages()
}
const openServicePackageDialog = (row = null) => {
  Object.assign(servicePackageForm, row ? {
    id: row.id,
    package_name: row.package_name || '',
    package_code: row.package_code || '',
    description: row.description || '',
    recommended_interval_km: row.recommended_interval_km ?? null,
    recommended_interval_months: row.recommended_interval_months ?? null,
    service_item_ids: (row.items || []).map((item) => Number(item.template_item_id))
  } : {
    id: null,
    package_name: '',
    package_code: '',
    description: '',
    recommended_interval_km: null,
    recommended_interval_months: null,
    service_item_ids: []
  })
  servicePackageDialogVisible.value = true
}
const saveServicePackage = async () => {
  if (!vehicleDetail.id) return
  if (!servicePackageForm.package_name) return ElMessage.warning('请填写套餐名称')
  if (!(servicePackageForm.service_item_ids || []).length) return ElMessage.warning('请至少选择一个标准项目')
  servicePackageSaving.value = true
  try {
    const payload = {
      package_name: servicePackageForm.package_name,
      package_code: servicePackageForm.package_code || null,
      description: servicePackageForm.description || null,
      recommended_interval_km: servicePackageForm.recommended_interval_km == null ? null : Number(servicePackageForm.recommended_interval_km),
      recommended_interval_months: servicePackageForm.recommended_interval_months == null ? null : Number(servicePackageForm.recommended_interval_months),
      is_active: true,
      sort_order: 100,
      items: (servicePackageForm.service_item_ids || []).map((id, index) => ({
        template_item_id: Number(id),
        sort_order: (index + 1) * 10,
        is_optional: false,
        notes: null
      }))
    }
    if (servicePackageForm.id) await request.put(`/mp/catalog/vehicle-models/${vehicleDetail.id}/service-packages/${servicePackageForm.id}`, payload)
    else await request.post(`/mp/catalog/vehicle-models/${vehicleDetail.id}/service-packages`, payload)
    servicePackageDialogVisible.value = false
    ElMessage.success('服务套餐已保存')
    await loadServicePackages()
  } finally {
    servicePackageSaving.value = false
  }
}
const removeServicePackage = async (row) => {
  try { await ElMessageBox.confirm(`确定删除服务套餐【${row.package_name}】吗？`, '确认删除', { type: 'warning' }) } catch { return }
  await request.delete(`/mp/catalog/vehicle-models/${vehicleDetail.id}/service-packages/${row.id}`)
  ElMessage.success('服务套餐已删除')
  await loadServicePackages()
}
const removeServiceItem = async (row) => { try { await ElMessageBox.confirm(`确定删除标准项目【${row.service_name}】吗？`, '确认删除', { type: 'warning' }) } catch { return } await request.delete(`/mp/catalog/vehicle-models/${vehicleDetail.id}/service-items/${row.id}`); ElMessage.success('标准项目已删除'); await loadServiceItems() }
const openServiceManualLocator = (row) => {
  currentServiceManualItem.value = row
  serviceManualMatches.value = locateServiceManualSegments(row)
  serviceManualLocatorVisible.value = true
}
const focusSegment = (row) => {
  segmentFilters.chapter = String(row?.chapter_no || '')
  segmentFilters.keyword = String(row?.title || '')
  serviceManualLocatorVisible.value = false
}
const openManualProcedureDialog = (row = null) => {
  Object.assign(manualProcedureForm, row ? { id: row.id, name: row.name || '', description: row.description || '' } : { id: null, name: '', description: '' })
  manualProcedureDialogVisible.value = true
}
const saveManualProcedure = async () => {
  if (!vehicleDetail.id) return
  if (!manualProcedureForm.name) return ElMessage.warning('请填写标准手册条目名称')
  manualSaving.value = true
  try {
    const payload = { name: manualProcedureForm.name, description: manualProcedureForm.description || null }
    if (manualProcedureForm.id) await request.put(`/mp/knowledge/procedures/${manualProcedureForm.id}`, payload)
    else await request.post(`/mp/knowledge/catalog-models/${vehicleDetail.id}/procedures`, payload)
    manualProcedureDialogVisible.value = false
    ElMessage.success('标准手册条目已保存')
    await loadManualProcedures()
  } finally { manualSaving.value = false }
}
const removeManualProcedure = async (row) => {
  try { await ElMessageBox.confirm(`确定删除标准手册条目【${row.name}】吗？`, '确认删除', { type: 'warning' }) } catch { return }
  await request.delete(`/mp/knowledge/procedures/${row.id}`)
  ElMessage.success('标准手册条目已删除')
  await loadManualProcedures()
}
const openManualStepDialog = (row) => {
  currentManualProcedure.value = row
  manualStepForm.steps = (row.steps || []).map((item) => ({ ...item }))
  manualStepDialogVisible.value = true
}
const appendManualStep = () => {
  manualStepForm.steps.push({ id: null, step_order: manualStepForm.steps.length + 1, instruction: '', required_tools: '', torque_spec: '', hazards: '' })
}
const removeManualStep = async (index, row) => {
  if (row?.id && currentManualProcedure.value?.id) {
    await request.delete(`/mp/knowledge/procedures/${currentManualProcedure.value.id}/steps/${row.id}`)
  }
  manualStepForm.steps.splice(index, 1)
}
const saveManualSteps = async () => {
  if (!currentManualProcedure.value?.id) return
  manualSaving.value = true
  try {
    for (const item of manualStepForm.steps) {
      const payload = {
        step_order: Number(item.step_order || 1),
        instruction: item.instruction,
        required_tools: item.required_tools || null,
        torque_spec: item.torque_spec || null,
        hazards: item.hazards || null
      }
      if (item.id) await request.put(`/mp/knowledge/procedures/${currentManualProcedure.value.id}/steps/${item.id}`, payload)
      else await request.post(`/mp/knowledge/procedures/${currentManualProcedure.value.id}/steps`, payload)
    }
    ElMessage.success('标准步骤已保存')
    manualStepDialogVisible.value = false
    await loadManualProcedures()
  } finally { manualSaving.value = false }
}
const openDocumentDialog = () => {
  documentForm.title = ''
  documentForm.category = '维修手册'
  documentForm.notes = ''
  documentDialogVisible.value = true
}
const uploadKnowledgeDocument = async () => {
  if (!vehicleDetail.id) return
  const file = documentFileInput.value?.files?.[0]
  if (!file) return ElMessage.warning('请选择 PDF 文件')
  documentSaving.value = true
  try {
    const formData = new FormData()
    formData.append('title', documentForm.title || file.name)
    formData.append('category', documentForm.category || '维修手册')
    formData.append('notes', documentForm.notes || '')
    formData.append('file', file)
    const created = await request.post(`/mp/knowledge/catalog-models/${vehicleDetail.id}/documents`, formData)
    documentDialogVisible.value = false
    if (documentFileInput.value) documentFileInput.value.value = ''
    ElMessage.success('资料已上传')
    await Promise.all([loadKnowledgeDocuments(), loadLibraryDocuments()])
    if ((documentForm.category || '维修手册') === '维修手册' && created?.id) {
      await parseKnowledgeDocument(created)
    }
  } finally { documentSaving.value = false }
}
const openKnowledgeDocument = (row) => {
  const target = row?.download_url || row?.file_url
  if (!target) return
  window.open(target, '_blank')
}
const openLinkedModel = async (row) => {
  if (!row?.model_info?.id) return
  activeTab.value = 'vehicle'
  await router.replace({ name: 'inventory', query: { tab: 'vehicles', model_id: row.model_info.id } })
  await handleRouteFocus()
}
const parseKnowledgeDocument = async (row) => {
  if (!row?.id) return
  parsingDocumentId.value = row.id
  try {
    const job = await request.post(`/mp/knowledge/documents/${row.id}/parse`)
    ElMessage.success('已提交解析任务，系统会在后台继续处理')
    await Promise.all([loadKnowledgeDocuments(), loadLibraryDocuments()])
    if (job?.id) {
      void monitorParseJob(job.id)
    }
  } finally {
    parsingDocumentId.value = null
  }
}
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))
const stopParseResultPolling = () => {
  if (parseResultPollingTimer) {
    clearInterval(parseResultPollingTimer)
    parseResultPollingTimer = null
  }
}
const stopLibraryPolling = () => {
  if (libraryPollingTimer) {
    clearInterval(libraryPollingTimer)
    libraryPollingTimer = null
  }
}
const shouldPollLibraryDocuments = () => {
  if (activeTab.value !== 'documents') return false
  return libraryDocuments.value.some((row) => ['queued', 'processing'].includes(row?.latest_parse_job?.status))
}
const ensureLibraryPolling = () => {
  if (!shouldPollLibraryDocuments()) {
    stopLibraryPolling()
    return
  }
  if (libraryPollingTimer) return
  libraryPollingTimer = setInterval(async () => {
    if (!shouldPollLibraryDocuments()) {
      stopLibraryPolling()
      return
    }
    try {
      await loadLibraryDocuments()
    } catch (error) {
      console.error('library polling failed', error)
    }
  }, 5000)
}
const monitorParseJob = async (jobId) => {
  const maxAttempts = 360
  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    await sleep(5000)
    const detail = await request.get(`/mp/knowledge/parse-jobs/${jobId}`)
    if (detail?.status === 'completed') {
      await Promise.all([loadKnowledgeDocuments(), loadLibraryDocuments()])
      ElMessage.success('资料解析完成')
      return
    }
    if (detail?.status === 'failed') {
      await Promise.all([loadKnowledgeDocuments(), loadLibraryDocuments()])
      ElMessage.error(detail.error_message || '资料解析失败')
      return
    }
  }
  await Promise.all([loadKnowledgeDocuments(), loadLibraryDocuments()])
  ElMessage.warning('解析任务仍在后台执行，请稍后查看结果')
}
const retryParseJob = async (row) => {
  const jobId = row?.latest_parse_job?.id
  if (!jobId) return ElMessage.warning('当前没有可重试的解析任务')
  await request.post(`/mp/knowledge/parse-jobs/${jobId}/retry`)
  ElMessage.success('已重新发起解析任务')
  await Promise.all([loadKnowledgeDocuments(), loadLibraryDocuments()])
}
const applyReviewStatus = async (row, reviewStatus) => {
  await request.patch(`/mp/knowledge/documents/${row.id}/review`, { review_status: reviewStatus })
  ElMessage.success(`已更新为${reviewStatusText(reviewStatus)}`)
  await Promise.all([loadKnowledgeDocuments(), loadLibraryDocuments()])
}
const openVehicleRecognitionEditor = () => {
  const traceability = parseResultDetail.value?.raw_result_json?.normalized_manual?.traceability || {}
  vehicleRecognitionForm.brand = recognizedCatalogCandidate.value?.brand || ''
  vehicleRecognitionForm.model_name = recognizedCatalogCandidate.value?.model_name || ''
  vehicleRecognitionForm.year_range = recognizedCatalogCandidate.value?.year_range || ''
  vehicleRecognitionForm.engine_code = recognizedCatalogCandidate.value?.engine_code || ''
  vehicleRecognitionForm.source_pages_text = (traceability.source_pages || []).join(',')
  vehicleRecognitionEditorVisible.value = true
}
const saveVehicleRecognitionEditor = async () => {
  if (!parseResultDetail.value?.id) return
  await saveParseResultPatch({
      applicability: {
        brand: vehicleRecognitionForm.brand || null,
        model_name: vehicleRecognitionForm.model_name || null,
        year_range: vehicleRecognitionForm.year_range || null,
        engine_code: vehicleRecognitionForm.engine_code || null,
        source_pages: parseSourcePagesText(vehicleRecognitionForm.source_pages_text)
      }
    }, '车型识别结果已保存')
  vehicleRecognitionEditorVisible.value = false
}
const openResultSectionsEditor = () => {
  resultListEditorType.value = 'sections'
  resultListEditorTitle.value = '编辑章节候选'
  resultListEditorRows.value = (parseResultDetail.value?.summary_json?.sections || []).map((item) => ({
    title: item?.title || item?.label || String(item || ''),
    page_number: item?.page_number || item?.page || '',
    review_status: item?.review_status || 'pending_review'
  }))
  resultListEditorVisible.value = true
}
const openSpecGroupEditor = (group) => {
  resultListEditorType.value = 'specs'
  resultListEditorTitle.value = `编辑${group.label}`
  resultListEditorRows.value = (group?.items || []).map((item) => ({
      label: item?.label || '',
      type: item?.type || '',
      value: item?.value || '',
      unit: item?.unit || '',
      page_number: item?.page_number || item?.page || '',
      source_text: item?.source_text || '',
      review_status: item?.review_status || 'pending_review'
    }))
  resultListEditorVisible.value = true
}
const openProcedureGroupEditor = (group) => {
  resultListEditorType.value = 'procedures'
  resultListEditorTitle.value = `编辑${group.label}`
  resultListEditorRows.value = (group?.items || []).map((item, index) => ({
    step_order: Number(item?.step_order || (index + 1)),
    instruction: item?.instruction || '',
      required_tools: item?.required_tools || '',
      torque_spec: item?.torque_spec || '',
      page_number: item?.page_number || item?.page || '',
      hazards: item?.hazards || '',
      review_status: item?.review_status || 'pending_review'
    }))
  resultListEditorVisible.value = true
}
const appendResultListEditorRow = () => {
  if (resultListEditorType.value === 'sections') resultListEditorRows.value.push({ title: '', page_number: '', review_status: 'pending_review' })
  else if (resultListEditorType.value === 'specs') resultListEditorRows.value.push({ label: '', type: '', value: '', unit: '', page_number: '', source_text: '', review_status: 'pending_review' })
  else resultListEditorRows.value.push({ step_order: resultListEditorRows.value.length + 1, instruction: '', required_tools: '', torque_spec: '', page_number: '', hazards: '', review_status: 'pending_review' })
}
const removeResultListEditorRow = (index) => {
  resultListEditorRows.value.splice(index, 1)
}
const saveResultListEditor = async () => {
  if (!parseResultDetail.value?.id) return
  const payload = {}
  if (resultListEditorType.value === 'sections') {
    payload.sections = resultListEditorRows.value
        .filter((item) => item.title)
        .map((item) => ({ title: item.title, page_number: item.page_number || null, review_status: item.review_status || 'pending_review' }))
  } else if (resultListEditorType.value === 'specs') {
    payload.specs = resultListEditorRows.value
        .filter((item) => item.label || item.value || item.source_text)
        .map((item) => ({
          label: item.label || null,
          type: item.type || 'other',
          value: item.value || null,
          unit: item.unit || null,
          page_number: item.page_number || null,
          source_text: item.source_text || null,
          review_status: item.review_status || 'pending_review'
        }))
  } else {
    payload.procedures = resultListEditorRows.value
        .filter((item) => item.instruction)
        .map((item, index) => ({
          step_order: Number(item.step_order || (index + 1)),
          instruction: item.instruction,
          required_tools: item.required_tools || null,
          torque_spec: item.torque_spec || null,
          page_number: item.page_number || null,
          hazards: item.hazards || null,
          review_status: item.review_status || 'pending_review'
        }))
  }
  await saveParseResultPatch(payload, '识别结果已保存')
  resultListEditorVisible.value = false
}
const openParsePageEditor = () => {
  const page = selectedParsePageDetail.value
  if (!page) return
  parsePageEditorForm.id = page.id
  parsePageEditorForm.page_number = page.page_number
  parsePageEditorForm.summary = page.summary || ''
  parsePageEditorForm.text_content = page.text_content || ''
  parsePageEditorForm.specs_json = (page.specs_json || []).map((item) => cloneRow(item))
  parsePageEditorForm.procedures_json = (page.procedures_json || []).map((item) => cloneRow(item))
  parsePageEditorVisible.value = true
}
const appendParsePageSpec = () => {
  parsePageEditorForm.specs_json.push({ label: '', type: 'other', value: '', unit: '', page_number: parsePageEditorForm.page_number, source_text: '' })
}
const appendParsePageProcedure = () => {
  parsePageEditorForm.procedures_json.push({ step_order: parsePageEditorForm.procedures_json.length + 1, instruction: '', required_tools: '', torque_spec: '', page_number: parsePageEditorForm.page_number, hazards: '' })
}
const saveParsePageEditor = async () => {
  if (!parsePageEditorForm.id) return
  parseResultSaving.value = true
  try {
    parseResultDetail.value = await request.patch(`/mp/knowledge/parse-pages/${parsePageEditorForm.id}`, {
      summary: parsePageEditorForm.summary || null,
      text_content: parsePageEditorForm.text_content || null,
      specs_json: parsePageEditorForm.specs_json.map((item) => ({
        label: item.label || null,
        type: item.type || 'other',
        value: item.value || null,
        unit: item.unit || null,
        page_number: item.page_number || parsePageEditorForm.page_number,
        source_text: item.source_text || null,
        review_status: item.review_status || 'pending_review'
      })),
      procedures_json: parsePageEditorForm.procedures_json.map((item, index) => ({
        step_order: Number(item.step_order || (index + 1)),
        instruction: item.instruction || null,
        required_tools: item.required_tools || null,
        torque_spec: item.torque_spec || null,
        page_number: item.page_number || parsePageEditorForm.page_number,
        hazards: item.hazards || null,
        review_status: item.review_status || 'pending_review'
      }))
    })
    parsePageEditorVisible.value = false
    selectedParsePage.value = parsePageEditorForm.page_number
    ElMessage.success(`第 ${parsePageEditorForm.page_number} 页已保存`)
    await Promise.all([loadKnowledgeDocuments(), loadLibraryDocuments()])
  } finally {
    parseResultSaving.value = false
  }
}
const openParseResultDialog = async (row) => {
  const jobId = row?.latest_parse_job?.id
  if (!jobId) return ElMessage.warning('这份资料还没有解析结果')
  stopParseResultPolling()
  parseResultDialogVisible.value = true
  parseResultLoading.value = true
  parseResultDetail.value = null
  parseViewTab.value = 'overview'
  selectedParsePage.value = null
  try {
    parseResultDetail.value = await request.get(`/mp/knowledge/parse-jobs/${jobId}`)
    selectedParsePage.value = parseResultDetail.value?.pages?.[0]?.page_number || null
    if (['queued', 'processing'].includes(parseResultDetail.value?.status)) {
      parseResultPollingTimer = setInterval(async () => {
        if (!parseResultDialogVisible.value) {
          stopParseResultPolling()
          return
        }
        const detail = await request.get(`/mp/knowledge/parse-jobs/${jobId}`)
        parseResultDetail.value = detail
        if (!selectedParsePage.value && detail?.pages?.length) selectedParsePage.value = detail.pages[0].page_number
        if (!['queued', 'processing'].includes(detail?.status)) {
          stopParseResultPolling()
          await loadKnowledgeDocuments()
          await loadLibraryDocuments()
        }
      }, 5000)
    }
  } finally {
    parseResultLoading.value = false
  }
}
const importParseResultToManual = async () => {
  if (!vehicleDetail.id || !parseResultDetail.value) return
  if (!isCatalogConfirmed.value) return ElMessage.warning('请先确认这份手册对应的品牌、年款和车型')
  importingParseResult.value = true
  try {
    const raw = parseResultDetail.value.raw_result_json || {}
    const summary = parseResultDetail.value.summary_json || {}
    const normalized = raw.normalized_manual || {}
    const sourceTitle = raw.title || normalized.document_profile?.document_title || 'OCR 导入条目'
    const allSpecs = summary.specs || []
    const specs = (allSpecs.filter((item) => item?.review_status === 'confirmed').length
      ? allSpecs.filter((item) => item?.review_status === 'confirmed')
      : allSpecs).slice(0, 12)
    const procedureSource = (normalized.procedures?.steps || []).length
      ? normalized.procedures.steps
      : (summary.procedures || []).length
        ? summary.procedures
        : (parseResultDetail.value.pages || []).flatMap((page) => page.procedures_json || [])
    const confirmedProcedures = procedureSource.filter((item) => item?.review_status === 'confirmed')
    const procedures = confirmedProcedures.length ? confirmedProcedures : procedureSource

    const descriptionParts = []
    if (summary.summary) descriptionParts.push(summary.summary)
    const operationNames = normalized.operation_index?.operation_names || []
    if (operationNames.length) descriptionParts.push(`识别项目：${operationNames.join('；')}`)
    if (specs.length) {
      descriptionParts.push(`识别规格：${specs.map((item) => `${item.label || item.type} ${item.value || '-'}${item.unit || ''}`).join('；')}`)
    }
    const cautionText = (normalized.procedures?.safety_cautions || []).slice(0, 6).join('；')
    if (cautionText) descriptionParts.push(`安全提示：${cautionText}`)
    if (raw.file_name) descriptionParts.push(`来源文件：${raw.file_name}`)
    if (raw.provider || parseResultDetail.value.provider) descriptionParts.push(`解析引擎：${raw.provider || parseResultDetail.value.provider}`)

    const created = await request.post(`/mp/knowledge/catalog-models/${vehicleDetail.id}/procedures`, {
      name: sourceTitle,
      description: descriptionParts.join('\n')
    })

    for (const [index, item] of procedures.slice(0, 30).entries()) {
      await request.post(`/mp/knowledge/procedures/${created.id}/steps`, {
        step_order: Number(item.step_order || (index + 1)),
        instruction: item.instruction || `OCR 导入步骤 ${index + 1}`,
        required_tools: item.required_tools || null,
        torque_spec: item.torque_spec || null,
        hazards: item.hazards || null
      })
    }

    await Promise.all([loadManualProcedures(), loadKnowledgeSegments()])
    ElMessage.success(procedures.length ? '已导入标准手册条目和步骤' : '已导入标准手册条目')
  } finally {
    importingParseResult.value = false
  }
}
const materializeParseSegments = async () => {
  if (!parseResultDetail.value?.id) return
  importingParseResult.value = true
  try {
    const result = await request.post(`/mp/knowledge/parse-jobs/${parseResultDetail.value.id}/materialize-segments`)
    await Promise.all([loadKnowledgeSegments(), loadKnowledgeDocuments(), loadManualProcedures(), loadLibraryDocuments()])
    const sourceText = result?.source === 'pdf_outline' ? 'PDF 原生目录' : 'OCR 目录'
    ElMessage.success(`已根据${sourceText}生成 ${Number(result?.materialized || 0)} 个目录分段`)
  } finally {
    importingParseResult.value = false
  }
}
const openCatalogConfirmationDialog = (mode = 'existing') => {
  catalogConfirmationMode.value = mode
  const candidate = recognizedCatalogCandidate.value || {}
  catalogConfirmationForm.model_id = parseResultDocument.value?.model_id || null
  catalogConfirmationForm.brand = candidate.brand || ''
  catalogConfirmationForm.model_name = candidate.model_name || ''
  catalogConfirmationForm.year_from = Number(candidate.year_from || new Date().getFullYear())
  catalogConfirmationForm.year_to = Number(candidate.year_to || candidate.year_from || new Date().getFullYear())
  catalogConfirmationForm.displacement_cc = candidate.displacement_cc || null
  catalogConfirmationForm.default_engine_code = candidate.engine_code || candidate.default_engine_code || ''
  catalogConfirmationForm.category = '街车/跑车'
  catalogConfirmationForm.notes = ''
  catalogConfirmationDialogVisible.value = true
}
const confirmCurrentCatalogBinding = async () => {
  if (!parseResultDocument.value?.id) return
  importingCatalogModel.value = true
  try {
    const result = await request.patch(`/mp/knowledge/documents/${parseResultDocument.value.id}/catalog-confirmation`, {
      action: 'confirm_current'
    })
    await Promise.all([loadVehicleBrands(), loadVehicleModels(), loadKnowledgeDocuments(), loadLibraryDocuments()])
    if (result?.model_id) {
      await router.replace({ name: 'inventory', query: { tab: 'vehicles', model_id: result.model_id } })
      await handleRouteFocus()
    }
    ElMessage.success('已确认当前绑定车型')
  } finally {
    importingCatalogModel.value = false
  }
}
const resetCatalogConfirmation = async () => {
  if (!parseResultDocument.value?.id) return
  importingCatalogModel.value = true
  try {
    await request.patch(`/mp/knowledge/documents/${parseResultDocument.value.id}/catalog-confirmation`, {
      action: 'reset_pending'
    })
    await Promise.all([loadKnowledgeDocuments(), loadLibraryDocuments()])
    ElMessage.success('已恢复为待确认车型')
  } finally {
    importingCatalogModel.value = false
  }
}
const saveCatalogConfirmation = async () => {
  if (!parseResultDocument.value?.id) return
  catalogConfirmationSaving.value = true
  try {
    const payload = { action: catalogConfirmationMode.value, notes: catalogConfirmationForm.notes || null }
    if (catalogConfirmationMode.value === 'bind_existing') {
      payload.model_id = Number(catalogConfirmationForm.model_id || 0)
    } else if (catalogConfirmationMode.value === 'create_new') {
      Object.assign(payload, {
        brand: catalogConfirmationForm.brand || null,
        model_name: catalogConfirmationForm.model_name || null,
        year_from: Number(catalogConfirmationForm.year_from || new Date().getFullYear()),
        year_to: Number(catalogConfirmationForm.year_to || catalogConfirmationForm.year_from || new Date().getFullYear()),
        displacement_cc: catalogConfirmationForm.displacement_cc ? Number(catalogConfirmationForm.displacement_cc) : null,
        default_engine_code: catalogConfirmationForm.default_engine_code || null,
        category: catalogConfirmationForm.category || null
      })
    }
    const result = await request.patch(`/mp/knowledge/documents/${parseResultDocument.value.id}/catalog-confirmation`, payload)
    await Promise.all([loadVehicleBrands(), loadVehicleModels(), loadKnowledgeDocuments(), loadLibraryDocuments()])
    catalogConfirmationDialogVisible.value = false
    if (result?.model_id) {
      await router.replace({ name: 'inventory', query: { tab: 'vehicles', model_id: result.model_id } })
      await handleRouteFocus()
    }
    const confirmed = result?.catalog_confirmed_model_info || result?.model_info || {}
    ElMessage.success(`已确认车型：${confirmed.brand || ''} ${confirmed.model_name || ''}`.trim())
  } finally {
    catalogConfirmationSaving.value = false
  }
}
const importConfirmedSpecsToCatalog = async () => {
  if (!parseResultDetail.value?.id) return
  importingConfirmedSpecs.value = true
  try {
    const result = await request.post(`/mp/knowledge/parse-jobs/${parseResultDetail.value.id}/import-confirmed-specs`)
  ElMessage.success(`已导入 ${Number(result?.imported || 0)} 条规格到标准车型参数`)
    if (vehicleDetail.id && Number(parseResultDocument.value?.model_id || 0) === Number(vehicleDetail.id)) {
      await loadVehicleSpecs()
    }
  } finally {
    importingConfirmedSpecs.value = false
  }
}
const removeKnowledgeDocument = async (row) => {
  try { await ElMessageBox.confirm(`确定删除资料【${row.title}】吗？`, '确认删除', { type: 'warning' }) } catch { return }
  await request.delete(`/mp/knowledge/documents/${row.id}`)
  ElMessage.success('资料已删除')
  await Promise.all([loadKnowledgeDocuments(), loadLibraryDocuments()])
}
const openPartDialog = (row = null) => { Object.assign(partForm, row ? { ...row } : { id: null, part_no: '', name: '', brand: '', category: '', unit: '件', min_stock: 0, sale_price: 0, cost_price: 0, stock_qty: 0, supplier_name: '' }); partDialogVisible.value = true }
const savePart = async () => {
  if (!partForm.part_no || !partForm.name) return ElMessage.warning('请填写料号和名称')
  partSaving.value = true
  try {
    const payload = { ...partForm, min_stock: Number(partForm.min_stock || 0), sale_price: Number(partForm.sale_price || 0), cost_price: Number(partForm.cost_price || 0), stock_qty: Number(partForm.stock_qty || 0), compatible_model_ids: [], is_active: true }
    if (partForm.id) await request.put(`/mp/catalog/parts/${partForm.id}`, payload)
    else await request.post('/mp/catalog/parts', payload)
    partDialogVisible.value = false
    ElMessage.success('配件已保存')
    await Promise.all([loadPartCategories(), loadParts()])
  } finally { partSaving.value = false }
}
const removePart = async (row) => { try { await ElMessageBox.confirm(`确定删除配件【${row.name}】吗？`, '确认删除', { type: 'warning' }) } catch { return } await request.delete(`/mp/catalog/parts/${row.id}`); ElMessage.success('配件已删除'); await loadParts() }

const handleRouteFocus = async () => {
  const query = route.query || {}
  const targetTab = typeof query.tab === 'string' && query.tab ? query.tab : ''
  const modelId = Number(query.model_id || 0)
  if (targetTab === 'vehicles') activeTab.value = 'vehicle'
  if (targetTab === 'documents') activeTab.value = 'documents'
  if (!modelId) return
  const row = vehicleRows.value.find((item) => Number(item.id) === modelId)
  if (!row) return
  await openVehicleDetail(row)
  await router.replace({ name: 'inventory', query: { tab: targetTab || undefined } })
}

onMounted(async () => {
  await Promise.all([loadAppSettings(), loadVehicleBrands(), loadVehicleCategories(), loadVehicleModels(), loadPartCategories(), loadParts(), loadLibraryDocuments()])
  window.addEventListener('drmoto-store-changed', handleStoreChanged)
  await handleRouteFocus()
})
onBeforeUnmount(() => {
  window.removeEventListener('drmoto-store-changed', handleStoreChanged)
})
watch(() => route.query, async () => {
  await handleRouteFocus()
})
watch(activeTab, () => {
  ensureLibraryPolling()
})
watch(
  () => libraryDocuments.value.map((row) => `${row?.id}:${row?.latest_parse_job?.status || 'pending'}`).join('|'),
  () => {
    ensureLibraryPolling()
  }
)
watch(parseResultDialogVisible, (visible) => {
  if (!visible) stopParseResultPolling()
})
onBeforeUnmount(() => {
  stopParseResultPolling()
  stopLibraryPolling()
})
</script>

<style scoped>
.inventory-page { display: flex; flex-direction: column; gap: 16px; }
.page-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
.page-head h2 { margin: 0 0 6px; }
.page-head p { margin: 0; color: #64748b; line-height: 1.7; }
.summary-grid { display: grid; grid-template-columns: repeat(4, minmax(120px, 1fr)); gap: 12px; }
.quick-workbench { display: grid; grid-template-columns: repeat(4, minmax(180px, 1fr)); gap: 12px; }
.quick-workbench-card { display: flex; flex-direction: column; gap: 8px; }
.quick-workbench-card span { color: #64748b; font-size: 12px; }
.quick-workbench-card strong { color: #0f172a; font-size: 28px; }
.quick-workbench-card p { margin: 0; color: #64748b; line-height: 1.6; min-height: 44px; }
.domain-hint-card { margin-bottom: 12px; padding: 12px 14px; border-radius: 12px; border: 1px solid #d8e7f3; background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%); display: flex; flex-direction: column; gap: 6px; }
.domain-hint-card strong { color: #17324a; font-size: 14px; }
.domain-hint-card span { color: #627d96; font-size: 12px; line-height: 1.7; }
.summary-card { display: flex; flex-direction: column; gap: 6px; }
.summary-card span { color: #64748b; font-size: 12px; }
.summary-card strong { font-size: 28px; color: #0f172a; }
.toolbar { margin-bottom: 14px; display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.library-quick-filters { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 12px; }
.library-focus-strip { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-bottom: 12px; }
.library-focus-item { padding: 12px 14px; border-radius: 12px; border: 1px solid #dbeafe; background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%); display: flex; flex-direction: column; gap: 4px; }
.library-focus-item span { color: #64748b; font-size: 12px; }
.library-focus-item strong { color: #0f172a; font-size: 22px; }
.library-focus-item small { color: #64748b; line-height: 1.6; }
.library-focus-actions { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; justify-content: flex-end; }
.detail-head { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 14px; }
.detail-head p { margin: 6px 0 0; color: #64748b; }
.head-actions { display: flex; gap: 8px; }
.part-tags { display: flex; flex-wrap: wrap; gap: 6px; }
.package-preview { margin-top: 12px; padding: 12px 14px; border-radius: 12px; background: linear-gradient(180deg, #f5fbff 0%, #eef6ff 100%); border: 1px solid #d8ebff; }
.package-preview-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 8px; margin-top: 8px; color: #496179; }
.muted { color: #94a3b8; }
.parts-editor-head { display: flex; justify-content: space-between; align-items: center; margin: 8px 0 12px; }
.required-part-row { display: flex; gap: 8px; align-items: center; margin-bottom: 10px; flex-wrap: wrap; }
.manual-section { margin-top: 18px; padding-top: 18px; border-top: 1px solid #e2e8f0; }
.manual-head { margin-bottom: 12px; }
.manual-head p { margin: 6px 0 0; color: #64748b; line-height: 1.7; }
.doc-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
.segment-toolbar { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin: 6px 0 12px; flex-wrap: wrap; }
.segment-toolbar__filters { display: flex; gap: 8px; flex-wrap: wrap; }
.segment-toolbar__summary { color: #64748b; font-size: 13px; }
.locator-summary { margin-bottom: 12px; padding: 14px 16px; border: 1px solid #dbeafe; background: #f8fbff; border-radius: 12px; }
.locator-summary__title { font-weight: 700; color: #0f172a; margin-bottom: 6px; }
.locator-summary__text { color: #475569; line-height: 1.7; }
.locator-reasons { display: flex; gap: 6px; flex-wrap: wrap; }
.manual-step-row { display: flex; gap: 8px; align-items: center; margin-bottom: 10px; flex-wrap: wrap; }
.parse-loading { padding: 36px 0; text-align: center; color: #64748b; }
.parse-result-actions { display: flex; justify-content: flex-end; margin-bottom: 12px; }
.parse-summary-grid { display: grid; grid-template-columns: repeat(4, minmax(120px, 1fr)); gap: 12px; margin-bottom: 16px; }
.parse-summary-card { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 12px 14px; display: flex; flex-direction: column; gap: 6px; }
.parse-summary-card span { color: #64748b; font-size: 12px; }
.parse-summary-card strong { color: #0f172a; font-size: 18px; }
.parse-review-banner { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; padding: 12px 14px; border: 1px solid #dbeafe; border-radius: 14px; background: linear-gradient(180deg, #f8fbff 0%, #eef6ff 100%); margin-bottom: 14px; }
.parse-review-banner p { margin: 6px 0 0; color: #64748b; line-height: 1.6; }
.parse-confirmation-banner { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; padding: 12px 14px; border: 1px solid #bfdbfe; border-radius: 14px; background: linear-gradient(180deg, #fefefe 0%, #eff6ff 100%); margin-bottom: 14px; }
.parse-confirmation-banner p { margin: 6px 0 0; color: #64748b; line-height: 1.6; }
.parse-section-block { margin-bottom: 14px; }
.section-title-row { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.tail-actions { justify-content: flex-end; }
.parse-section-block p { margin: 8px 0 0; color: #334155; line-height: 1.7; }
.parse-view-tabs { margin-top: 8px; }
.parse-chip-list { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }
.parse-progress-inline { display: flex; flex-direction: column; gap: 6px; min-width: 220px; }
.list-overview-cell { display: flex; flex-direction: column; gap: 4px; }
.list-overview-cell strong { color: #0f172a; font-size: 13px; }
.list-overview-cell span { color: #64748b; font-size: 12px; }
.quick-overview-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-bottom: 14px; }
.quick-overview-card { padding: 14px 16px; border: 1px solid #dbeafe; border-radius: 14px; background: linear-gradient(180deg, #f8fbff 0%, #eef6ff 100%); }
.quick-overview-card span { display: block; color: #64748b; font-size: 12px; margin-bottom: 6px; }
.quick-overview-card strong { color: #0f172a; font-size: 16px; line-height: 1.4; }
.readiness-list { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin-top: 8px; }
.readiness-item { padding: 12px 14px; border: 1px solid #e2e8f0; border-radius: 14px; background: #fff; }
.spec-card-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; margin-top: 8px; }
.technician-step-list { display: flex; flex-direction: column; gap: 12px; margin-top: 8px; }
.technician-step-card { border: 1px solid #e2e8f3; border-radius: 12px; padding: 12px 14px; background: #fbfcff; }
.technician-step-card p { margin: 8px 0 0; color: #24324a; line-height: 1.75; }
.technician-inline-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px 14px; margin-top: 12px; }
.technician-inline-grid span { display: block; color: #7a8599; font-size: 12px; margin-bottom: 4px; }
.technician-inline-grid strong { color: #162033; line-height: 1.6; }
.spec-card { border: 1px solid #e2e8f0; border-radius: 14px; background: #fff; padding: 12px 14px; }
.parse-page-detail { margin-top: 14px; padding: 14px 16px; border: 1px solid #dbeafe; border-radius: 14px; background: #f8fbff; }
.parse-page-summary { margin: 8px 0 12px; color: #334155; }
.parse-page-text { margin: 0; white-space: pre-wrap; word-break: break-word; line-height: 1.7; color: #1e293b; }
.parse-step-list { display: flex; flex-direction: column; gap: 10px; }
.parse-step-item { padding: 10px 12px; border: 1px solid #e2e8f0; border-radius: 10px; background: #fff; }
.parse-step-item p { margin: 6px 0 0; }
@media (max-width: 900px) { .summary-grid, .quick-workbench, .spec-card-grid, .quick-overview-grid, .readiness-list, .library-focus-strip { grid-template-columns: repeat(2, minmax(120px, 1fr)); } .page-head, .parse-review-banner, .library-focus-actions { flex-direction: column; align-items: flex-start; } }
@media (max-width: 900px) { .technician-inline-grid { grid-template-columns: 1fr; } }
@media (max-width: 640px) { .summary-grid, .quick-workbench, .parse-summary-grid, .quick-overview-grid, .readiness-list, .library-focus-strip { grid-template-columns: 1fr; } }
</style>
