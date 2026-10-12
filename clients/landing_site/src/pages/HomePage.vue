<template>
  <main id="top" class="apple-home">
    <section class="apple-hero">
      <img
        src="/sample-photos/photo-01-inspection.jpg"
        alt="DrMoto 机车博士品牌灯牌实拍图"
        width="1800"
        height="1012"
        fetchpriority="high"
        decoding="async"
      />
      <div class="apple-hero__content">
        <p class="hero-badge">DrMoto</p>
        <h1>机车博士。</h1>
        <p>
          让机车维修透明可追踪。检测、报价、施工、交车，都留下清楚记录。
        </p>
        <div class="hero-actions">
          <RouterLink class="primary-action" to="/contact?type=rider">预约检测</RouterLink>
          <a class="text-action" href="#business">门店方案</a>
        </div>
      </div>
    </section>

    <section id="values" class="apple-statement">
      <div class="apple-statement__content">
        <p class="statement-label">DrMoto Values</p>
        <h2>好的维修，应该有记录、有依据、有交代。</h2>
        <p>
          把判断、费用和结果说清楚，让每一次交付都经得起回看。
        </p>
      </div>
    </section>

    <section class="apple-proof" aria-label="机车博士服务证据">
      <article>
        <span>Before</span>
        <strong>维修前，有检测依据。</strong>
      </article>
      <article>
        <span>During</span>
        <strong>维修中，有过程记录。</strong>
      </article>
      <article>
        <span>After</span>
        <strong>交车后，有车辆档案。</strong>
      </article>
    </section>

    <section id="riders" class="apple-section service-section">
      <div class="section-copy compact-copy">
        <p class="eyebrow">Rider Service</p>
        <h2>四步，把维修说清楚。</h2>
      </div>
      <div class="apple-step-grid" aria-label="车主服务流程">
        <article>
          <span>01</span>
          <h3>检测</h3>
          <p>问题、照片和初步判断先进入记录。</p>
        </article>
        <article>
          <span>02</span>
          <h3>报价</h3>
          <p>项目、配件、工时分开展示。</p>
        </article>
        <article>
          <span>03</span>
          <h3>施工</h3>
          <p>关键节点同步，过程不靠反复追问。</p>
        </article>
        <article>
          <span>04</span>
          <h3>交车</h3>
          <p>完工体检和保养建议归入车辆档案。</p>
        </article>
      </div>
    </section>

    <section id="photo-story" class="apple-section photo-led-section">
      <div class="photo-led-grid">
        <div class="photo-panel large">
          <img src="/sample-photos/photo-02-detail.jpg" alt="维修细节特写示例图" width="1800" height="1013" loading="lazy" decoding="async" />
          <div>
            <span>Detail</span>
            <h2>专业感，来自每一个细节。</h2>
          </div>
        </div>
        <div class="photo-panel">
          <img src="/sample-photos/photo-03-handoff.jpg" alt="交车沟通场景示例图" width="1800" height="1180" loading="lazy" decoding="async" />
          <div>
            <span>Handoff</span>
            <h3>交车时，车主看得懂发生了什么。</h3>
          </div>
        </div>
        <div class="record-panel">
          <span>Vehicle Memory</span>
          <h3>车辆档案会记住每一次维修。</h3>
          <p>历史工单、保养建议和健康记录，跟随车辆长期沉淀。</p>
        </div>
      </div>
    </section>

    <section id="business" class="apple-section business-release">
      <div class="business-release__copy">
        <p class="eyebrow">For Workshops</p>
        <h2>给认真经营服务质量的机车门店。</h2>
        <p>
          从接车建档、报价确认到施工记录、线下收款和交车，统一管理门店服务流程。
        </p>
        <RouterLink class="primary-action" to="/contact?type=workshop">预约门店演示</RouterLink>
      </div>
      <div class="business-product">
        <div class="business-product__photo">
          <img src="/sample-photos/photo-04-system.jpg" alt="机车博士门店品牌氛围实拍图" width="1800" height="1013" loading="lazy" decoding="async" />
        </div>
        <div class="business-product__screen">
          <img src="/product-shots/saas-workshop-screen.png" alt="机车博士门店管理系统工单中心截图" width="2880" height="1960" loading="lazy" decoding="async" />
        </div>
        <div class="business-product__features" aria-label="门店系统核心能力">
          <span>工单中心</span>
          <span>车辆档案</span>
          <span>交付记录</span>
        </div>
      </div>
    </section>

    <section id="contact" class="conversion-section">
      <div class="conversion-section__head">
        <p class="eyebrow">Next</p>
        <h2>选择你的下一步。</h2>
      </div>
      <div class="conversion-grid">
        <article class="conversion-card conversion-card--primary">
          <span>Rider</span>
          <h3>预约透明检测。</h3>
          <p>留下车型、车辆问题和期望到店时间，与门店确认检测安排。</p>
          <RouterLink class="primary-action" to="/contact?type=rider">预约检测</RouterLink>
        </article>
        <article class="conversion-card">
          <span>Workshop</span>
          <h3>预约门店演示。</h3>
          <p>适合想把工单、车辆档案和交付记录统一管理的机车门店。</p>
          <RouterLink class="text-action" to="/contact?type=workshop">预约演示</RouterLink>
        </article>
      </div>
      <div class="contact-strip" aria-label="联系方式">
        <RouterLink to="/contact">联系机车博士</RouterLink>
        <span>具体到店时间以门店确认为准</span>
      </div>
    </section>
  </main>
</template>
