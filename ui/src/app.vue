<template>
  <div id="app" :class="{ 'chat-open': chatPanelOpen }">
    <!-- 背景光效装饰 -->
    <div class="bg-decor" aria-hidden="true">
      <i class="blob blob-1"></i>
      <i class="blob blob-2"></i>
      <i class="blob blob-3"></i>
    </div>

    <!-- ============ 顶部品牌栏（暗色玻璃拟态） ============ -->
    <header class="top-bar">
      <div class="top-bar-inner">
        <div class="brand">
          <div class="brand-logo">🍽️</div>
          <div class="brand-text">
            <div class="brand-name">智能点餐助手</div>
            <div class="brand-sub">AI SMART ORDERING · 美味即刻拥有</div>
          </div>
        </div>

        <div class="search-box">
          <span class="search-icon">🔍</span>
          <input
            v-model="searchKeyword"
            class="search-input"
            placeholder="搜索菜品名称、分类或描述…"
          />
          <span v-if="searchKeyword" class="search-clear" @click="searchKeyword = ''">✕</span>
        </div>

        <div class="top-actions">
          <button class="top-btn" @click="ordersDrawerVisible = true">
            🧾 我的订单
            <span v-if="orders.length" class="top-btn-badge">{{ orders.length }}</span>
          </button>
          <button class="top-btn" @click="openReservationDrawer">
            📅 我的预订
            <span v-if="reservations.length" class="top-btn-badge">{{ reservations.length }}</span>
          </button>
          <button class="top-btn top-btn-primary" @click="toggleChatPanel">
            🤖 AI 助手
            <span class="top-btn-dot" :class="'state-' + chatStatus.type"></span>
          </button>
        </div>
      </div>
    </header>

    <!-- ============ 店铺信息条 ============ -->
    <div class="shop-strip">
      <div class="shop-strip-inner">
        <div class="shop-name">
          <strong>本店招牌</strong>
          <span class="shop-state">
            <i class="state-dot" :class="chatStatus.type"></i>AI 服务{{ chatStatus.label }}
          </span>
        </div>
        <div class="shop-tags">
          <span class="shop-tag tag-yellow">🤖 AI 智能推荐</span>
          <span class="shop-tag tag-cyan">⚡ 流式实时应答</span>
          <span class="shop-tag tag-red">🌶️ 辣度标注</span>
          <span class="shop-tag tag-green">🥬 素食可选</span>
          <span class="shop-tag tag-purple">📅 支持预订</span>
        </div>
      </div>
    </div>

    <!-- ============ 主体：左侧 AI 助手 + 右侧点餐区 ============ -->
    <main class="page">
      <!-- 左侧 AI 对话面板（默认常驻） -->
      <aside class="chat-panel">
        <div class="chat-panel-head">
          <div class="chat-panel-title">
            <span class="chat-panel-emoji">🤖</span>
            AI 点餐助手
            <el-tag size="small" :type="chatStatus.type" effect="dark">{{ chatStatus.label }}</el-tag>
          </div>
          <button class="chat-close" @click="chatPanelOpen = false">✕</button>
        </div>

        <!-- 聊天历史记录 -->
        <div class="chat-history" ref="chatHistoryRef">
          <div v-if="chatMessages.length === 0" class="welcome-message">
            <div class="welcome-emoji">👋</div>
            <p>您好！我是您的智能点餐助手</p>
            <p class="welcome-sub">告诉我您的口味，我来为您挑菜</p>
            <div class="suggestion-chips">
              <span class="chip" @click="quickAsk('你们几点营业？')">你们几点营业？</span>
              <span class="chip" @click="quickAsk('推荐几个不辣的菜')">推荐不辣的菜</span>
              <span class="chip" @click="quickAsk('能送到清华大学吗？')">能送到清华大学吗？</span>
            </div>
          </div>

          <div
            v-for="(msg, index) in chatMessages"
            :key="index"
            class="message-wrapper"
            :class="msg.role"
          >
            <div class="avatar">{{ msg.role === 'user' ? '👤' : '🤖' }}</div>
            <div class="message-bubble">
              <div
                v-if="msg.role === 'assistant'"
                v-html="formatMessage(msg.content)"
                class="markdown-content"
              ></div>
              <div v-else>{{ msg.content }}</div>
            </div>
          </div>

          <div v-if="chatLoading" class="message-wrapper assistant">
            <div class="avatar">🤖</div>
            <div class="message-bubble loading-bubble">
              <div class="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        </div>

        <!-- FAQ 联想推荐 -->
        <div v-if="faqSuggestionsVisible" class="faq-suggestions">
          <div class="faq-suggestions-title">您可能想问：</div>
          <div class="faq-suggestions-list">
            <button
              v-for="item in faqSuggestions"
              :key="item.question"
              class="faq-suggestion-btn"
              @click="selectFaqSuggestion(item)"
            >{{ item.question }}</button>
          </div>
        </div>

        <!-- 输入区域 -->
        <div class="chat-input-wrapper">
          <el-input
            ref="chatInputRef"
            v-model="chatQuery"
            type="textarea"
            :rows="2"
            placeholder="请输入您的需求，Enter 发送 / Shift+Enter 换行"
            class="chat-input"
            resize="none"
            @keydown.enter.exact.prevent="sendChatQuery"
          />
          <button
            class="send-btn"
            :class="{ loading: chatLoading }"
            @click="sendChatQuery"
            :disabled="chatLoading"
          >➤</button>
        </div>
      </aside>

      <!-- 右侧：分类 + 菜品列表 -->
      <div class="shop-card">
        <!-- 分类导航 -->
        <aside class="cate-rail">
          <div class="cate-rail-title">菜单分类</div>
          <div
            v-for="cate in categories"
            :key="cate.name"
            class="cate-item"
            :class="{ active: activeCategory === cate.name }"
            @click="activeCategory = cate.name"
          >
            <span class="cate-name">{{ cate.name }}</span>
            <span class="cate-count">{{ cate.count }}</span>
          </div>
        </aside>

        <!-- 菜品列表 -->
        <section class="dish-panel">
          <div class="dish-panel-head">
            <div class="dish-panel-title">
              {{ activeCategory }}
              <span class="dish-panel-count">（{{ filteredMenuItems.length }} 道）</span>
            </div>
            <button class="refresh-btn" @click="loadMenuItems" :disabled="menuLoading">
              {{ menuLoading ? '加载中…' : '↻ 刷新菜单' }}
            </button>
          </div>

          <div v-if="menuError" class="menu-error">
            <el-alert :title="menuError" type="error" :closable="true" show-icon effect="dark" />
          </div>

          <div v-if="menuLoading" class="dish-skeleton">
            <el-skeleton v-for="n in 4" :key="n" :rows="3" animated class="skeleton-block" />
          </div>

          <div v-else-if="filteredMenuItems.length > 0" class="dish-list">
            <div
              v-for="item in filteredMenuItems"
              :key="item.id"
              class="dish-card"
              :class="{
                highlighted: highlightedItems.includes(getItemIdStr(item)),
                flashing: flashingItems.includes(getItemIdStr(item))
              }"
            >
              <!-- 真实菜品图（加载失败回退到 emoji 渐变） -->
              <div class="dish-thumb">
                <img
                  v-if="showDishImage(item)"
                  :src="dishImage(item)"
                  :alt="item.dish_name"
                  class="thumb-img"
                  loading="lazy"
                  @error="onImgError(item)"
                />
                <div v-else class="thumb-fallback" :style="thumbStyle(item)">
                  <span class="thumb-emoji">{{ dishEmoji(item) }}</span>
                </div>
                <span v-if="highlightedItems.includes(getItemIdStr(item))" class="ai-badge">AI 推荐</span>
              </div>

              <!-- 菜品信息 -->
              <div class="dish-info">
                <div class="dish-name">{{ item.dish_name }}</div>
                <div class="dish-tags">
                  <span class="pill pill-cate">{{ item.category }}</span>
                  <span
                    v-if="item.spice_text"
                    class="pill"
                    :class="'pill-spice-' + (item.spice_level || 0)"
                  >{{ item.spice_text }}</span>
                  <span v-if="item.is_vegetarian" class="pill pill-veg">🥬 素食</span>
                </div>
                <div class="dish-desc" :title="item.description">{{ item.description }}</div>
                <div class="dish-bottom">
                  <div class="dish-price">{{ item.formatted_price || ('¥' + item.price) }}</div>
                  <div class="dish-actions">
                    <template v-if="getCartQty(item) > 0">
                      <button class="step-btn step-minus" @click.stop="changeQty(item, -1)">−</button>
                      <span class="step-qty">{{ getCartQty(item) }}</span>
                    </template>
                    <button class="step-btn step-plus" @click.stop="changeQty(item, 1)">＋</button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <el-empty
            v-else
            :description="searchKeyword ? '没有找到相关菜品，换个关键词试试' : '暂无菜品'"
          />
        </section>
      </div>
    </main>

    <!-- ============ 底部购物车结算栏 ============ -->
    <div class="cart-bar">
      <div class="cart-bar-inner">
        <div class="cart-icon-wrap" @click="cartDrawerVisible = true">
          <div class="cart-icon" :class="{ empty: cartCount === 0 }">
            🛒
            <span v-if="cartCount > 0" class="cart-badge">{{ cartCount }}</span>
          </div>
        </div>
        <div class="cart-total" @click="cartCount > 0 && (cartDrawerVisible = true)">
          <template v-if="cartCount > 0">
            <div class="total-price">¥{{ cartTotal.toFixed(2) }}</div>
            <div class="total-hint">已选 {{ cartCount }} 件商品</div>
          </template>
          <div v-else class="total-empty">购物车是空的，快去挑选美食吧～</div>
        </div>
        <button
          class="checkout-btn"
          :class="{ disabled: cartCount === 0 }"
          @click="placeOrder"
        >去结算</button>
      </div>
    </div>

    <!-- ============ 购物车抽屉 ============ -->
    <el-drawer
      v-model="cartDrawerVisible"
      title="🛒 已选商品"
      direction="rtl"
      size="380px"
      class="mt-drawer cart-drawer"
      :z-index="2000"
    >
      <div class="cart-drawer-body">
        <template v-if="cartItems.length > 0">
          <div class="cart-drawer-head">
            <span>共 {{ cartCount }} 件商品</span>
            <button class="clear-cart-btn" @click="clearCart">🗑 清空购物车</button>
          </div>
          <div class="cart-lines">
            <div v-for="line in cartItems" :key="line.id" class="cart-line">
              <div class="cart-line-thumb">
                <img
                  v-if="showDishImage(line)"
                  :src="dishImage(line)"
                  :alt="line.dish_name"
                  @error="onImgError(line)"
                />
                <span v-else>{{ dishEmoji(line) }}</span>
              </div>
              <div class="cart-line-info">
                <div class="cart-line-name">{{ line.dish_name }}</div>
                <div class="cart-line-price">{{ line.formatted_price || ('¥' + line.price) }}</div>
              </div>
              <div class="cart-line-actions">
                <button class="step-btn step-minus" @click="updateQuantity(line, -1)">−</button>
                <span class="step-qty">{{ line.quantity }}</span>
                <button class="step-btn step-plus" @click="updateQuantity(line, 1)">＋</button>
              </div>
            </div>
          </div>
        </template>
        <el-empty v-else description="购物车是空的" :image-size="80" />
      </div>
      <template #footer>
        <div class="cart-drawer-footer">
          <div class="cart-drawer-total">
            合计：<strong>¥{{ cartTotal.toFixed(2) }}</strong>
          </div>
          <button
            class="checkout-btn small"
            :class="{ disabled: cartCount === 0 }"
            @click="goCheckout"
          >去结算</button>
        </div>
      </template>
    </el-drawer>

    <!-- ============ 预订信息抽屉 ============ -->
    <el-drawer
      v-model="reservationDrawerVisible"
      title="📅 我的预订"
      direction="rtl"
      size="400px"
      class="mt-drawer reservation-drawer"
      :z-index="2000"
    >
      <div class="reservation-drawer-body">
        <div class="reservation-head">
          <span>共 {{ reservations.length }} 条预订</span>
          <button class="refresh-btn" @click="loadReservations" :disabled="reservationLoading">
            {{ reservationLoading ? '加载中…' : '↻ 刷新' }}
          </button>
        </div>
        <div v-if="reservationLoading" class="reservation-loading">
          <el-skeleton :rows="4" animated />
        </div>
        <div v-else-if="reservations.length > 0" class="reservation-list">
          <div v-for="item in reservations" :key="item.id" class="reservation-item">
            <div class="reservation-title">
              <span>预订 #{{ item.id }}</span>
              <span class="reservation-time">{{ item.arrival_time }}</span>
            </div>
            <div class="reservation-meta">
              <span>👥 {{ item.num_people }} 人</span>
              <span>🧒 {{ item.num_children }} 儿童</span>
              <span v-if="item.seat_preference">🪑 {{ item.seat_preference }}</span>
              <span v-if="item.main_dish_preference">🍲 {{ item.main_dish_preference }}</span>
            </div>
            <div v-if="item.other_comments" class="reservation-comments">
              {{ item.other_comments }}
            </div>
          </div>
        </div>
        <el-empty v-else description="暂无预订信息" :image-size="80" />
      </div>
    </el-drawer>

    <!-- ============ 结算确认对话框 ============ -->
    <el-dialog
      v-model="showOrderDialog"
      title="确认订单"
      width="440px"
      class="checkout-dialog"
      :z-index="3000"
    >
      <div class="order-summary">
        <div v-for="line in cartItems" :key="line.id" class="order-line">
          <span class="order-line-name">{{ dishEmoji(line) }} {{ line.dish_name }}</span>
          <span class="order-line-qty">× {{ line.quantity }}</span>
          <span class="order-line-subtotal">¥{{ (line.price * line.quantity).toFixed(2) }}</span>
        </div>
        <div class="order-total-line">
          <span>合计</span>
          <strong>¥{{ cartTotal.toFixed(2) }}</strong>
        </div>
      </div>
      <template #footer>
        <el-button @click="showOrderDialog = false">再想想</el-button>
        <el-button type="warning" class="confirm-order-btn" @click="confirmOrder">确认下单</el-button>
      </template>
    </el-dialog>

    <!-- ============ 下单成功弹窗 ============ -->
    <el-dialog
      v-model="orderSuccessVisible"
      width="430px"
      class="checkout-dialog success-dialog"
      :z-index="3100"
    >
      <div v-if="lastOrder" class="order-success">
        <div class="success-icon">✅</div>
        <div class="success-title">下单成功</div>
        <div class="success-sub">厨房正在准备您的美食</div>
        <div class="success-card">
          <div class="success-line"><span>订单编号</span><strong>{{ lastOrder.id }}</strong></div>
          <div class="success-line"><span>下单时间</span><strong>{{ lastOrder.time }}</strong></div>
          <div class="success-line"><span>菜品数量</span><strong>{{ lastOrder.count }} 件</strong></div>
          <div class="success-line"><span>订单金额</span><strong class="money">¥{{ lastOrder.total.toFixed(2) }}</strong></div>
          <div class="success-line"><span>订单状态</span><strong class="status">🔥 {{ lastOrder.status }}</strong></div>
        </div>
        <div class="success-note">
          演示环境：后端暂未提供下单接口，订单已保存在本浏览器，可随时在顶栏「我的订单」中查看历史。
        </div>
      </div>
      <template #footer>
        <el-button @click="orderSuccessVisible = false">继续点餐</el-button>
        <el-button type="warning" @click="orderSuccessVisible = false; ordersDrawerVisible = true">查看我的订单</el-button>
      </template>
    </el-dialog>

    <!-- ============ 我的订单抽屉 ============ -->
    <el-drawer
      v-model="ordersDrawerVisible"
      title="🧾 我的订单"
      direction="rtl"
      size="400px"
      class="mt-drawer orders-drawer"
      :z-index="2000"
    >
      <div class="reservation-drawer-body">
        <div v-if="orders.length > 0" class="reservation-list">
          <div v-for="o in orders" :key="o.id" class="reservation-item order-item">
            <div class="reservation-title">
              <span>{{ o.id }}</span>
              <span class="reservation-time">{{ o.time }}</span>
            </div>
            <div class="order-item-lines">
              <div v-for="(it, idx) in o.items" :key="idx" class="order-item-line">
                <span>{{ it.name }} × {{ it.quantity }}</span>
                <span>¥{{ (it.price * it.quantity).toFixed(2) }}</span>
              </div>
            </div>
            <div class="order-item-foot">
              <span class="order-status">🔥 {{ o.status }}</span>
              <span class="order-total">合计 ¥{{ o.total.toFixed(2) }}</span>
            </div>
          </div>
        </div>
        <el-empty v-else description="还没有订单，快去点餐吧" :image-size="80" />
      </div>
    </el-drawer>
  </div>
</template>

<script>
import { ElMessage } from 'element-plus';
import { computed, nextTick, onMounted, ref, watch } from 'vue';
import { chatAPI, deliveryAPI, faqAPI, menuAPI, reservationAPI } from './api/index.js';

export default {
  name: 'App',
  setup() {
    // ============ 聊天相关 ============
    const chatQuery = ref('')
    const chatMessages = ref([])
    const chatLoading = ref(false)
    const chatState = ref('unknown')
    const chatStatus = computed(() => ({
      unknown: { label: '待验证', type: 'info' },
      pending: { label: '响应中', type: 'warning' },
      ready: { label: '可用', type: 'success' },
      error: { label: '异常', type: 'danger' }
    }[chatState.value]))
    const chatHistoryRef = ref(null)
    const chatInputRef = ref(null)
    // 移动端以浮层形式打开聊天面板；桌面端面板常驻
    const chatPanelOpen = ref(false)
    const faqSuggestions = ref([])
    const faqSuggestLoading = ref(false)
    let faqSuggestTimer = null

    // ============ 配送相关 ============
    const deliveryAddress = ref('')
    const travelMode = ref("2")
    const deliveryResponse = ref(null)
    const deliveryLoading = ref(false)

    // ============ 菜单相关 ============
    const menuItems = ref([])
    const menuLoading = ref(false)
    const menuError = ref('')
    const highlightedItems = ref([])
    const flashingItems = ref([])
    const searchKeyword = ref('')
    const activeCategory = ref('全部')
    let autoHighlightTimer = null
    let lastHighlightKey = ''

    // ============ 购物车相关 ============
    const cartItems = ref([])
    const showOrderDialog = ref(false)
    const cartDrawerVisible = ref(false)

    // ============ 预订信息 ============
    const reservations = ref([])
    const reservationLoading = ref(false)
    const reservationDrawerVisible = ref(false)

    const cartTotal = computed(() => {
      return cartItems.value.reduce((sum, item) => sum + item.price * item.quantity, 0)
    })

    const cartCount = computed(() => {
      return cartItems.value.reduce((sum, item) => sum + item.quantity, 0)
    })

    // id -> 数量 映射，便于菜品行内步进器显示
    const cartQtyMap = computed(() => {
      const map = {}
      for (const line of cartItems.value) {
        map[String(line.id)] = line.quantity
      }
      return map
    })

    const getCartQty = (item) => cartQtyMap.value[getItemIdStr(item)] || 0

    const addToCart = (item, quantity = 1) => {
      // 使用 loose equality (==) 来兼容 string/number 类型的 ID
      const existing = cartItems.value.find(i => i.id == item.id)
      if (existing) {
        existing.quantity += quantity
      } else {
        cartItems.value.push({ ...item, quantity })
      }
      ElMessage.success(`已将 ${item.dish_name} 加入购物车`)
    }

    const addToCartById = (id, quantity = 1) => {
      const item = menuItems.value.find(i => i.id == id)
      if (item) {
        addToCart(item, quantity)
      } else {
        console.warn('Item not found for cart:', id)
      }
    }

    const updateQuantity = (item, delta) => {
      const newQty = item.quantity + delta
      if (newQty <= 0) {
        // 同样使用 loose equality (==)
        cartItems.value = cartItems.value.filter(i => i.id != item.id)
      } else {
        item.quantity = newQty
      }
    }

    // 菜品行内步进器：静默增减，不弹提示
    const changeQty = (item, delta) => {
      const existing = cartItems.value.find(i => i.id == item.id)
      if (existing) {
        updateQuantity(existing, delta)
      } else if (delta > 0) {
        cartItems.value.push({ ...item, quantity: delta })
      }
    }

    const clearCart = () => {
      cartItems.value = []
      ElMessage.success('购物车已清空')
    }

    const placeOrder = () => {
      if (cartItems.value.length === 0) return
      showOrderDialog.value = true
    }

    const goCheckout = () => {
      if (cartItems.value.length === 0) return
      cartDrawerVisible.value = false
      showOrderDialog.value = true
    }

    // ============ 订单记录 ============
    // 说明：后端暂未提供下单接口，订单保存在浏览器本地（localStorage），
    // 保证下单有真实反馈且历史可在「我的订单」中查看。
    const ORDERS_STORAGE_KEY = 'aimenu_orders'
    const orders = ref([])
    const ordersDrawerVisible = ref(false)
    const orderSuccessVisible = ref(false)
    const lastOrder = ref(null)

    const loadOrders = () => {
      try {
        const raw = window.localStorage.getItem(ORDERS_STORAGE_KEY)
        const list = raw ? JSON.parse(raw) : []
        orders.value = Array.isArray(list) ? list : []
      } catch (e) {
        orders.value = []
      }
    }

    const saveOrders = () => {
      try {
        window.localStorage.setItem(ORDERS_STORAGE_KEY, JSON.stringify(orders.value))
      } catch (e) {
        // ignore
      }
    }

    const confirmOrder = () => {
      if (cartItems.value.length === 0) return
      const now = new Date()
      const pad = (n) => String(n).padStart(2, '0')
      const order = {
        id: `NO${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}${Math.floor(Math.random() * 90 + 10)}`,
        items: cartItems.value.map(i => ({
          name: i.dish_name,
          quantity: i.quantity,
          price: i.price
        })),
        count: cartCount.value,
        total: cartTotal.value,
        time: now.toLocaleString('zh-CN', { hour12: false }),
        status: '厨房备餐中'
      }
      orders.value.unshift(order)
      saveOrders()
      lastOrder.value = order
      cartItems.value = []
      showOrderDialog.value = false
      cartDrawerVisible.value = false
      orderSuccessVisible.value = true
      ElMessage.success('下单成功！厨房正在准备您的美食')
    }

    // 滚动到底部
    const scrollToBottom = async () => {
      await nextTick()
      if (chatHistoryRef.value) {
        chatHistoryRef.value.scrollTop = chatHistoryRef.value.scrollHeight
      }
    }

    // 格式化消息
    const formatMessage = (content) => {
      if (!content) return ''
      return content
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\n/g, '<br/>')
    }

    // 快速提问
    const quickAsk = (text) => {
      chatQuery.value = text
      sendChatQuery()
    }

    // 桌面端聚焦输入框；移动端切换浮层面板
    const toggleChatPanel = () => {
      if (window.matchMedia('(max-width: 980px)').matches) {
        chatPanelOpen.value = !chatPanelOpen.value
        if (chatPanelOpen.value) scrollToBottom()
      } else {
        chatInputRef.value?.focus()
      }
    }

    const openReservationDrawer = () => {
      reservationDrawerVisible.value = true
      loadReservations()
    }

    const fetchFaqSuggestions = async (query) => {
      const q = (query || '').trim()
      if (!q) {
        faqSuggestions.value = []
        return
      }
      faqSuggestLoading.value = true
      try {
        const res = await faqAPI.suggest(q, 6)
        const items = Array.isArray(res?.suggestions) ? res.suggestions : []
        faqSuggestions.value = items
      } catch (e) {
        faqSuggestions.value = []
      } finally {
        faqSuggestLoading.value = false
      }
    }

    const selectFaqSuggestion = async (item) => {
      if (!item?.question || !item?.answer) return
      if (chatLoading.value) return
      const question = item.question
      const answer = item.answer
      chatMessages.value.push({ role: 'user', content: question })
      chatMessages.value.push({ role: 'assistant', content: answer })
      chatQuery.value = ''
      faqSuggestions.value = []
      scrollToBottom()
    }

    // 发送消息
    const sendChatQuery = async () => {
      if (!chatQuery.value.trim() || chatLoading.value) return

      const query = chatQuery.value
      faqSuggestions.value = []
      chatMessages.value.push({ role: 'user', content: query })
      chatQuery.value = ''
      chatLoading.value = true
      chatState.value = 'pending'
      scrollToBottom()

      let hasCreatedMessage = false
      let receivedToken = false
      let streamFailed = false

      await chatAPI.sendStreamMessage(
        query,
        (data) => {
          if (data?.type === 'recommendation' || data?.menu_ids) {
            highlightRecommendedItems(data.menu_ids)
          }

          if (data?.type === 'action' && data?.action === 'add_to_cart') {
            const items = Array.isArray(data.items) ? data.items : []
            if (items.length > 0) {
              for (const item of items) {
                if (item?.id != null) {
                  addToCartById(item.id, item.quantity || 1)
                }
              }
            } else if (data?.data?.menu_id != null) {
              addToCartById(data.data.menu_id, data.data.quantity || 1)
            }
          }

          const token =
            data?.type === 'token'
              ? (typeof data?.content === 'string'
                  ? data.content
                  : typeof data?.data === 'string'
                    ? data.data
                    : '')
              : ''
          const err = data?.type === 'error' ? data?.error : data?.error

          if (token) {
            receivedToken = true
            if (!hasCreatedMessage) {
              chatMessages.value.push({ role: 'assistant', content: '' })
              hasCreatedMessage = true
            }
            const currentMsg = chatMessages.value[chatMessages.value.length - 1]
            currentMsg.content += token
            scheduleAutoHighlightFromText(currentMsg.content)
            scrollToBottom()
          }

          if (err) {
            streamFailed = true
            chatState.value = 'error'
            if (!hasCreatedMessage) {
              chatLoading.value = false
              chatMessages.value.push({ role: 'assistant', content: '' })
              hasCreatedMessage = true
            }
            const currentMsg = chatMessages.value[chatMessages.value.length - 1]
            currentMsg.content += `\n[错误: ${err}]`
          }
        },
        (error) => {
          console.error('Chat error:', error)
          streamFailed = true
          chatState.value = 'error'
          chatLoading.value = false

          if (!hasCreatedMessage) {
            chatMessages.value.push({ role: 'assistant', content: '' })
            hasCreatedMessage = true
          }
          const currentMsg = chatMessages.value[chatMessages.value.length - 1]
          currentMsg.content += `\n[${error?.message || '网络错误，请检查连接'}]`
        },
        () => {
          chatLoading.value = false
          chatState.value = !streamFailed && receivedToken ? 'ready' : 'error'
          if (!hasCreatedMessage) {
            chatMessages.value.push({ role: 'assistant', content: '[未收到有效回答，请重试或查看后端日志。]' })
          }
          scrollToBottom()
        }
      )
    }

    // 配送查询
    const checkDelivery = async () => {
      if (!deliveryAddress.value.trim()) return
      deliveryLoading.value = true
      try {
        const response = await deliveryAPI.checkRange(deliveryAddress.value, travelMode.value)
        deliveryResponse.value = response
      } catch (e) {
        // 错误处理
      } finally {
        deliveryLoading.value = false
      }
    }

    // ============ 加载菜单 ============
    const getMenuItemsFromResponse = (response) => {
      if (!response) return []
      if (Array.isArray(response)) return response
      if (Array.isArray(response.menu_items)) return response.menu_items
      if (Array.isArray(response.menuItems)) return response.menuItems
      const data = response.data
      if (Array.isArray(data)) return data
      if (Array.isArray(data?.menu_items)) return data.menu_items
      if (Array.isArray(data?.menuItems)) return data.menuItems
      if (Array.isArray(data?.items)) return data.items
      return []
    }

    const loadMenuItems = async () => {
      menuLoading.value = true
      menuError.value = ''
      try {
        const response = await menuAPI.getMenuList()
        const items = getMenuItemsFromResponse(response)
        menuItems.value = items
        if (!items.length && response?.message && response.success === false) {
          menuError.value = response.message
          ElMessage.warning(response.message)
        }
      } catch (e) {
        menuItems.value = []
        menuError.value = e?.message || '菜品获取失败'
        ElMessage.error(menuError.value)
      } finally {
        menuLoading.value = false
      }
    }

    const loadReservations = async () => {
      reservationLoading.value = true
      try {
        const res = await reservationAPI.list(10)
        reservations.value = Array.isArray(res?.reservations) ? res.reservations : []
        if (res?.success === false && res?.message) {
          ElMessage.warning(res.message)
        }
      } catch (e) {
        reservations.value = []
        ElMessage.error(e?.message || '预订信息获取失败')
      } finally {
        reservationLoading.value = false
      }
    }

    // ============ 分类与筛选 ============
    const categories = computed(() => {
      const map = new Map()
      for (const it of menuItems.value) {
        const name = it?.category || '其他'
        map.set(name, (map.get(name) || 0) + 1)
      }
      return [
        { name: '全部', count: menuItems.value.length },
        ...Array.from(map, ([name, count]) => ({ name, count }))
      ]
    })

    const filteredMenuItems = computed(() => {
      let list = menuItems.value
      if (activeCategory.value && activeCategory.value !== '全部') {
        list = list.filter(it => (it?.category || '其他') === activeCategory.value)
      }
      const kw = searchKeyword.value.trim().toLowerCase()
      if (kw) {
        list = list.filter(it =>
          String(it?.dish_name || '').toLowerCase().includes(kw) ||
          String(it?.category || '').toLowerCase().includes(kw) ||
          String(it?.description || '').toLowerCase().includes(kw)
        )
      }
      return list
    })

    // ============ 真实菜品图片映射（图片位于 ui/public/dishes/） ============
    const DISH_IMAGES = [
      { keys: ['炒饭'], src: '/dishes/fried_rice.jpg' },
      { keys: ['粥', '泡饭'], src: '/dishes/congee.jpg' },
      { keys: ['米饭', '盖饭', '饭'], src: '/dishes/rice.jpg' },
      { keys: ['葱油饼', '饼'], src: '/dishes/pancake.jpg' },
      { keys: ['黄瓜'], src: '/dishes/cucumber.jpg' },
      { keys: ['酸辣'], src: '/dishes/hot_sour_soup.jpg' },
      { keys: ['蛋花', '紫菜', '汤', '羹', '煲'], src: '/dishes/egg_soup.jpg' },
      { keys: ['番茄', '西红柿'], src: '/dishes/tomato_egg.jpg' },
      { keys: ['四季豆', '豆角', '干煸'], src: '/dishes/veg.jpg' },
      { keys: ['宫保', '鸡丁', '鸡'], src: '/dishes/kung_pao.jpg' },
      { keys: ['鱼', '鲈'], src: '/dishes/fish.jpg' },
      { keys: ['虾'], src: '/dishes/shrimp.jpg' },
      { keys: ['豆腐', '麻婆'], src: '/dishes/tofu.jpg' },
      { keys: ['馄饨', '饺', '包子', '点心'], src: '/dishes/wonton.jpg' },
      { keys: ['面', '粉', '米线'], src: '/dishes/noodles.jpg' },
      { keys: ['蔬', '素', '时蔬', '青菜', '菜心'], src: '/dishes/greens.jpg' }
    ]
    const DISH_IMAGE_DEFAULT = '/dishes/default.jpg'

    const dishImage = (item) => {
      const text = `${item?.dish_name || ''}${item?.category || ''}`
      for (const rule of DISH_IMAGES) {
        if (rule.keys.some(k => text.includes(k))) return rule.src
      }
      return DISH_IMAGE_DEFAULT
    }

    // 图片加载失败时回退到 emoji 渐变占位
    const brokenImages = ref(new Set())

    const showDishImage = (item) => {
      return !brokenImages.value.has(getItemIdStr(item))
    }

    const onImgError = (item) => {
      brokenImages.value.add(getItemIdStr(item))
    }

    // ============ 菜品缩略图回退样式（emoji + 渐变底色） ============
    const EMOJI_RULES = [
      { keys: ['汤', '羹', '煲'], emoji: '🍲' },
      { keys: ['饮', '茶', '咖啡', '汁', '奶', '水'], emoji: '🥤' },
      { keys: ['甜', '蛋糕', '点心', '布丁', '冰淇淋'], emoji: '🍰' },
      { keys: ['饭', '面', '粉', '主食', '饺', '馄饨', '包'], emoji: '🍜' },
      { keys: ['鱼', '虾', '蟹', '海鲜', '鱿', '贝'], emoji: '🦐' },
      { keys: ['鸡', '鸭', '猪', '牛', '羊', '肉', '排'], emoji: '🍖' },
      { keys: ['蔬', '素', '菜', '沙拉', '菌', '菇'], emoji: '🥬' },
      { keys: ['辣', '川', '湘', '麻'], emoji: '🌶️' }
    ]

    const dishEmoji = (item) => {
      if (!item) return '🍽️'
      if (item.is_vegetarian) return '🥬'
      const text = `${item.category || ''}${item.dish_name || ''}`
      for (const rule of EMOJI_RULES) {
        if (rule.keys.some(k => text.includes(k))) return rule.emoji
      }
      return '🍽️'
    }

    const THUMB_GRADIENTS = [
      ['#3A2A18', '#54371C'],
      ['#3A1C18', '#54281F'],
      ['#1C3A20', '#285430'],
      ['#182A3A', '#1C3D54'],
      ['#3A3018', '#54451C'],
      ['#2A1C3A', '#3D2854']
    ]

    const hashStr = (s) => {
      let h = 0
      for (const ch of String(s || '')) {
        h = (h * 31 + ch.charCodeAt(0)) | 0
      }
      return Math.abs(h)
    }

    const thumbStyle = (item) => {
      const seed = Number(getItemIdStr(item)) || hashStr(item?.dish_name)
      const g = THUMB_GRADIENTS[seed % THUMB_GRADIENTS.length]
      return { background: `linear-gradient(135deg, ${g[0]}, ${g[1]})` }
    }

    // ============ 高亮推荐 ============
    const highlightRecommendedItems = (ids) => {
      if (!ids) return
      const normalized = (Array.isArray(ids) ? ids : [])
        .map(id => (id == null ? '' : String(id)))
        .filter(Boolean)
      const unique = Array.from(new Set(normalized)).sort()
      const key = unique.join(',')
      if (!key || key === lastHighlightKey) return
      lastHighlightKey = key
      highlightedItems.value = unique
      flashingItems.value = unique
      window.setTimeout(() => {
        flashingItems.value = []
      }, 900)
      scrollToHighlighted()
    }

    // 滚动到第一个被推荐的菜品
    const scrollToHighlighted = async () => {
      await nextTick()
      const el = document.querySelector('.dish-card.highlighted')
      if (el) {
        try {
          el.scrollIntoView({ behavior: 'smooth', block: 'center' })
        } catch (e) {
          el.scrollIntoView()
        }
      }
    }

    const extractMenuIdsFromText = (text) => {
      if (!text) return []
      const ids = []
      for (const item of menuItems.value) {
        if (!item?.dish_name || item?.id == null) continue
        if (text.includes(item.dish_name)) ids.push(String(item.id))
      }
      return ids
    }

    const getItemIdStr = (item) => {
      if (!item || item.id == null) return ''
      return String(item.id)
    }

    const scheduleAutoHighlightFromText = (text) => {
      if (autoHighlightTimer) window.clearTimeout(autoHighlightTimer)
      autoHighlightTimer = window.setTimeout(() => {
        const ids = extractMenuIdsFromText(text)
        if (ids.length) highlightRecommendedItems(ids)
      }, 240)
    }

    const getSpiceType = (level) => {
      return ['', 'success', 'warning', 'danger'][level] || ''
    }

    const cleanupBrowserCaches = async () => {
      try {
        if ('serviceWorker' in navigator) {
          const regs = await navigator.serviceWorker.getRegistrations()
          for (const reg of regs) {
            try {
              await reg.unregister()
            } catch (e) {
              // ignore
            }
          }
        }
        if ('caches' in window) {
          const keys = await window.caches.keys()
          for (const k of keys) {
            try {
              await window.caches.delete(k)
            } catch (e) {
              // ignore
            }
          }
        }
      } catch (e) {
        // ignore
      }
    }

    onMounted(() => {
      cleanupBrowserCaches()
      loadOrders()
      loadMenuItems()
      loadReservations()
    })

    watch(
      chatQuery,
      (val) => {
        if (faqSuggestTimer) window.clearTimeout(faqSuggestTimer)
        const q = (val || '').trim()
        if (!q || q.length < 2 || chatLoading.value) {
          faqSuggestions.value = []
          return
        }
        faqSuggestTimer = window.setTimeout(() => {
          fetchFaqSuggestions(q)
        }, 220)
      },
      { flush: 'post' }
    )

    return {
      // 聊天
      chatQuery,
      chatMessages,
      chatLoading,
      chatStatus,
      chatHistoryRef,
      chatInputRef,
      chatPanelOpen,
      toggleChatPanel,
      sendChatQuery,
      quickAsk,
      formatMessage,
      faqSuggestions,
      faqSuggestLoading,
      selectFaqSuggestion,
      faqSuggestionsVisible: computed(() => !faqSuggestLoading.value && faqSuggestions.value.length > 0),

      // 配送
      deliveryAddress,
      travelMode,
      deliveryResponse,
      deliveryLoading,
      checkDelivery,

      // 菜单
      menuItems,
      menuLoading,
      menuError,
      highlightedItems,
      flashingItems,
      loadMenuItems,
      getSpiceType,
      getItemIdStr,
      searchKeyword,
      activeCategory,
      categories,
      filteredMenuItems,
      dishEmoji,
      dishImage,
      showDishImage,
      onImgError,
      thumbStyle,

      // 购物车
      cartItems,
      cartTotal,
      cartCount,
      cartDrawerVisible,
      getCartQty,
      addToCart,
      changeQty,
      clearCart,
      updateQuantity,
      placeOrder,
      goCheckout,
      showOrderDialog,
      confirmOrder,

      // 预订
      reservations,
      reservationLoading,
      reservationDrawerVisible,
      openReservationDrawer,
      loadReservations,

      // 订单
      orders,
      ordersDrawerVisible,
      orderSuccessVisible,
      lastOrder
    }
  }
}
</script>

<style>
/* ============ 全局主题变量（暗夜霓虹） ============ */
:root {
  --bg-0: #070A14;
  --bg-1: #0C1122;
  --glass: rgba(255, 255, 255, 0.055);
  --glass-strong: rgba(255, 255, 255, 0.09);
  --line: rgba(255, 255, 255, 0.10);
  --yellow: #FFD100;
  --yellow-2: #FFB800;
  --neon-cyan: #22D3EE;
  --neon-purple: #A78BFA;
  --neon-pink: #FF3D81;
  --price: #FF6A3D;
  --text-0: #F5F7FF;
  --text-1: rgba(235, 240, 255, 0.72);
  --text-2: rgba(235, 240, 255, 0.45);
  --radius: 18px;
}

* {
  box-sizing: border-box;
}

html, body {
  margin: 0;
  min-height: 100%;
}

body {
  background:
    radial-gradient(1100px 560px at 88% -12%, rgba(124, 58, 237, 0.28), transparent 62%),
    radial-gradient(950px 520px at -12% 32%, rgba(34, 211, 238, 0.16), transparent 62%),
    radial-gradient(900px 480px at 52% 112%, rgba(255, 209, 0, 0.10), transparent 62%),
    var(--bg-0);
  background-attachment: fixed;
  color: var(--text-0);
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', '微软雅黑', Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
}

#app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  padding-bottom: 100px;
  position: relative;
}

button {
  font-family: inherit;
  cursor: pointer;
  border: none;
  background: none;
  padding: 0;
  color: inherit;
}

/* 暗色滚动条 */
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.14);
  border-radius: 999px;
}
::-webkit-scrollbar-thumb:hover { background: rgba(255, 255, 255, 0.25); }

/* ============ 背景漂浮光斑 ============ */
.bg-decor {
  position: fixed;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
  z-index: 0;
}

.blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(90px);
}

.blob-1 {
  width: 460px; height: 460px;
  background: rgba(124, 58, 237, 0.4);
  top: -140px; right: -90px;
  animation: drift-1 18s ease-in-out infinite alternate;
}

.blob-2 {
  width: 420px; height: 420px;
  background: rgba(34, 211, 238, 0.26);
  bottom: -160px; left: -110px;
  animation: drift-2 24s ease-in-out infinite alternate;
}

.blob-3 {
  width: 360px; height: 360px;
  background: rgba(255, 209, 0, 0.16);
  top: 42%; left: 56%;
  animation: drift-3 30s ease-in-out infinite alternate;
}

@keyframes drift-1 {
  from { transform: translate(0, 0) scale(1); }
  to   { transform: translate(-70px, 60px) scale(1.15); }
}
@keyframes drift-2 {
  from { transform: translate(0, 0) scale(1); }
  to   { transform: translate(80px, -50px) scale(1.1); }
}
@keyframes drift-3 {
  from { transform: translate(0, 0) scale(1); }
  to   { transform: translate(-90px, -70px) scale(0.9); }
}

/* ============ 顶部品牌栏 ============ */
.top-bar {
  position: sticky;
  top: 0;
  z-index: 100;
  background: rgba(7, 10, 20, 0.72);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-bottom: 1px solid var(--line);
}

.top-bar-inner {
  width: 100%;
  margin: 0 auto;
  padding: 12px 28px;
  display: flex;
  align-items: center;
  gap: 24px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.brand-logo {
  width: 46px;
  height: 46px;
  border-radius: 14px;
  background: linear-gradient(135deg, #FFE04A, var(--yellow-2));
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 25px;
  box-shadow: 0 0 18px rgba(255, 209, 0, 0.45), 0 4px 10px rgba(0, 0, 0, 0.4);
}

.brand-name {
  font-size: 20px;
  font-weight: 800;
  background: linear-gradient(92deg, #FFE04A 10%, #FF9A3D 90%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  line-height: 1.2;
  letter-spacing: 0.5px;
}

.brand-sub {
  font-size: 10px;
  color: var(--text-2);
  margin-top: 3px;
  letter-spacing: 1.5px;
}

/* 搜索框 */
.search-box {
  flex: 1;
  max-width: 480px;
  height: 42px;
  background: var(--glass);
  border: 1px solid var(--line);
  border-radius: 999px;
  display: flex;
  align-items: center;
  padding: 0 16px;
  gap: 8px;
  transition: all 0.2s;
}

.search-box:focus-within {
  border-color: rgba(255, 209, 0, 0.55);
  box-shadow: 0 0 0 3px rgba(255, 209, 0, 0.12), 0 0 18px rgba(255, 209, 0, 0.12);
}

.search-icon {
  font-size: 14px;
  opacity: 0.6;
}

.search-input {
  flex: 1;
  border: none;
  outline: none;
  font-size: 14px;
  color: var(--text-0);
  background: transparent;
}

.search-input::placeholder {
  color: var(--text-2);
}

.search-clear {
  font-size: 12px;
  color: var(--text-2);
  cursor: pointer;
  padding: 2px;
}

.search-clear:hover {
  color: var(--text-0);
}

/* 顶部操作按钮 */
.top-actions {
  display: flex;
  gap: 10px;
  flex-shrink: 0;
  margin-left: auto;
}

.top-btn {
  position: relative;
  height: 42px;
  padding: 0 18px;
  border-radius: 999px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-0);
  background: var(--glass);
  border: 1px solid var(--line);
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 7px;
}

.top-btn:hover {
  background: var(--glass-strong);
  transform: translateY(-1px);
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.35);
}

.top-btn-primary {
  background: linear-gradient(135deg, #FFE04A, var(--yellow-2));
  border-color: transparent;
  color: #1A1A1A;
  font-weight: 800;
  box-shadow: 0 0 16px rgba(255, 209, 0, 0.35);
}

.top-btn-primary:hover {
  box-shadow: 0 0 26px rgba(255, 209, 0, 0.55);
}

.top-btn-badge {
  background: var(--neon-pink);
  color: #FFFFFF;
  font-size: 11px;
  min-width: 18px;
  height: 18px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 5px;
  box-shadow: 0 0 8px rgba(255, 61, 129, 0.6);
}

.top-btn-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #909399;
}

.top-btn-dot.state-success { background: #4CD263; box-shadow: 0 0 8px #4CD263; }
.top-btn-dot.state-warning { background: #FFB800; box-shadow: 0 0 8px #FFB800; }
.top-btn-dot.state-danger  { background: #FF4A26; box-shadow: 0 0 8px #FF4A26; }
.top-btn-dot.state-info    { background: #AAAAAA; }

/* ============ 店铺信息条 ============ */
.shop-strip {
  position: relative;
  z-index: 1;
  width: 100%;
  margin: 16px auto 0;
  padding: 0 28px;
}

.shop-strip-inner {
  background: var(--glass);
  border: 1px solid var(--line);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border-radius: var(--radius);
  padding: 12px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.shop-name {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 16px;
}

.shop-state {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-1);
}

.state-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #909399;
  display: inline-block;
}

.state-dot.success { background: #4CD263; box-shadow: 0 0 8px #4CD263; }
.state-dot.warning { background: #FFB800; box-shadow: 0 0 8px #FFB800; }
.state-dot.danger  { background: #FF4A26; box-shadow: 0 0 8px #FF4A26; }
.state-dot.info    { background: #AAAAAA; }

.shop-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.shop-tag {
  font-size: 12px;
  border-radius: 999px;
  padding: 4px 12px;
  border: 1px solid;
  background: transparent;
}

.tag-yellow { color: #FFE04A; border-color: rgba(255, 224, 74, 0.35); background: rgba(255, 224, 74, 0.08); }
.tag-cyan   { color: #67E3F9; border-color: rgba(34, 211, 238, 0.35); background: rgba(34, 211, 238, 0.08); }
.tag-red    { color: #FF8A70; border-color: rgba(255, 106, 61, 0.4);  background: rgba(255, 106, 61, 0.1); }
.tag-green  { color: #7BE495; border-color: rgba(76, 210, 99, 0.35);  background: rgba(76, 210, 99, 0.08); }
.tag-purple { color: #C4B0FF; border-color: rgba(167, 139, 250, 0.4); background: rgba(167, 139, 250, 0.1); }

/* ============ 主体布局：左 AI 面板 + 右点餐区 ============ */
.page {
  position: relative;
  z-index: 1;
  flex: 1;
  width: 100%;
  margin: 16px auto 0;
  padding: 0 28px;
  display: grid;
  grid-template-columns: 396px minmax(0, 1fr);
  gap: 16px;
  align-items: start;
}

/* 超宽屏加宽 AI 面板 */
@media (min-width: 1600px) {
  .page {
    grid-template-columns: 460px minmax(0, 1fr);
  }
}

/* ============ 左侧 AI 对话面板 ============ */
.chat-panel {
  position: sticky;
  top: 86px;
  height: calc(100vh - 116px);
  min-height: 480px;
  display: flex;
  flex-direction: column;
  background: var(--glass);
  border: 1px solid var(--line);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-radius: var(--radius);
  overflow: hidden;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.35);
}

.chat-panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid var(--line);
  background: linear-gradient(135deg, rgba(255, 224, 74, 0.12), rgba(34, 211, 238, 0.06));
}

.chat-panel-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 800;
}

.chat-panel-emoji {
  font-size: 20px;
  filter: drop-shadow(0 0 8px rgba(255, 209, 0, 0.6));
}

.chat-close {
  display: none;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: var(--glass);
  color: var(--text-1);
  font-size: 14px;
}

.chat-body, .chat-history {
  flex: 1;
  overflow-y: auto;
  padding: 18px 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.welcome-message {
  text-align: center;
  color: var(--text-1);
  margin-top: 30px;
  font-size: 15px;
}

.welcome-emoji {
  font-size: 44px;
  margin-bottom: 10px;
  filter: drop-shadow(0 0 14px rgba(255, 209, 0, 0.5));
}

.welcome-sub {
  font-size: 12.5px;
  color: var(--text-2);
}

.suggestion-chips {
  margin-top: 16px;
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 10px;
}

.chip {
  cursor: pointer;
  font-size: 12.5px;
  color: #FFE04A;
  background: rgba(255, 224, 74, 0.08);
  border: 1px solid rgba(255, 224, 74, 0.35);
  border-radius: 999px;
  padding: 6px 14px;
  transition: all 0.2s;
}

.chip:hover {
  transform: translateY(-2px);
  background: rgba(255, 224, 74, 0.16);
  box-shadow: 0 0 14px rgba(255, 209, 0, 0.25);
}

.message-wrapper {
  display: flex;
  gap: 10px;
  max-width: 90%;
}

.message-wrapper.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: var(--glass-strong);
  border: 1px solid var(--line);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
}

.message-bubble {
  background: var(--glass-strong);
  border: 1px solid var(--line);
  padding: 11px 14px;
  border-radius: 14px;
  line-height: 1.6;
  font-size: 13.5px;
  color: var(--text-0);
  word-break: break-word;
}

.message-wrapper.user .message-bubble {
  background: linear-gradient(135deg, #FFE04A, var(--yellow-2));
  border-color: transparent;
  color: #1A1A1A;
  font-weight: 600;
  border-bottom-right-radius: 4px;
  box-shadow: 0 0 16px rgba(255, 209, 0, 0.25);
}

.message-wrapper.assistant .message-bubble {
  border-top-left-radius: 4px;
}

.faq-suggestions {
  border-top: 1px solid var(--line);
  padding: 10px 14px;
  background: rgba(255, 255, 255, 0.03);
}

.faq-suggestions-title {
  font-size: 12px;
  color: var(--text-2);
  margin-bottom: 8px;
}

.faq-suggestions-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.faq-suggestion-btn {
  font-size: 12.5px;
  color: #67E3F9;
  background: rgba(34, 211, 238, 0.08);
  border: 1px solid rgba(34, 211, 238, 0.3);
  border-radius: 999px;
  padding: 5px 12px;
  transition: all 0.2s;
}

.faq-suggestion-btn:hover {
  background: rgba(34, 211, 238, 0.16);
  box-shadow: 0 0 12px rgba(34, 211, 238, 0.25);
}

.chat-input-wrapper {
  padding: 12px 14px;
  display: flex;
  gap: 10px;
  align-items: flex-end;
  border-top: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.03);
}

.chat-input .el-textarea__inner {
  background: rgba(255, 255, 255, 0.06);
  box-shadow: none;
  border: 1px solid transparent;
  color: var(--text-0);
  border-radius: 12px;
  transition: all 0.2s;
}

.chat-input .el-textarea__inner::placeholder {
  color: var(--text-2);
}

.chat-input .el-textarea__inner:focus {
  background: rgba(255, 255, 255, 0.09);
  border-color: rgba(255, 209, 0, 0.5);
  box-shadow: 0 0 0 3px rgba(255, 209, 0, 0.1);
}

.send-btn {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  background: linear-gradient(135deg, #FFE04A, var(--yellow-2));
  color: #1A1A1A;
  font-size: 17px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.2s;
  box-shadow: 0 0 14px rgba(255, 209, 0, 0.4);
}

.send-btn:hover:not(:disabled) {
  transform: scale(1.06);
  box-shadow: 0 0 22px rgba(255, 209, 0, 0.6);
}

.send-btn.loading,
.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.typing-indicator span {
  display: inline-block;
  width: 6px;
  height: 6px;
  background-color: var(--yellow);
  border-radius: 50%;
  margin: 0 2px;
  animation: bounce 1.4s infinite ease-in-out both;
}

.typing-indicator span:nth-child(1) { animation-delay: -0.32s; }
.typing-indicator span:nth-child(2) { animation-delay: -0.16s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

/* ============ 右侧点餐卡片 ============ */
.shop-card {
  display: flex;
  background: var(--glass);
  border: 1px solid var(--line);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-radius: var(--radius);
  overflow: hidden;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.35);
  align-items: stretch;
  min-height: calc(100vh - 250px);
}

/* 分类导航 */
.cate-rail {
  width: 148px;
  flex-shrink: 0;
  background: rgba(255, 255, 255, 0.03);
  border-right: 1px solid var(--line);
  padding: 12px 0;
  position: sticky;
  top: 86px;
  align-self: flex-start;
  max-height: calc(100vh - 200px);
  overflow-y: auto;
}

.cate-rail-title {
  font-size: 11px;
  letter-spacing: 2px;
  color: var(--text-2);
  padding: 4px 16px 10px;
}

.cate-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  font-size: 13.5px;
  color: var(--text-1);
  cursor: pointer;
  border-left: 3px solid transparent;
  transition: all 0.15s;
}

.cate-item:hover {
  color: var(--text-0);
  background: rgba(255, 255, 255, 0.05);
}

.cate-item.active {
  background: linear-gradient(90deg, rgba(255, 224, 74, 0.18), transparent);
  color: #FFE04A;
  font-weight: 800;
  border-left-color: var(--yellow);
  text-shadow: 0 0 12px rgba(255, 209, 0, 0.5);
}

.cate-count {
  font-size: 11px;
  color: var(--text-2);
  background: rgba(255, 255, 255, 0.08);
  border-radius: 999px;
  padding: 1px 7px;
}

.cate-item.active .cate-count {
  background: rgba(255, 224, 74, 0.2);
  color: #FFE04A;
}

/* 菜品面板 */
.dish-panel {
  flex: 1;
  min-width: 0;
  padding: 16px 20px 24px;
}

.dish-panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}

.dish-panel-title {
  font-size: 17px;
  font-weight: 800;
}

.dish-panel-count {
  font-size: 12px;
  color: var(--text-2);
  font-weight: 400;
}

.refresh-btn {
  font-size: 13px;
  color: #FFE04A;
  background: rgba(255, 224, 74, 0.08);
  border: 1px solid rgba(255, 224, 74, 0.35);
  border-radius: 999px;
  padding: 5px 14px;
  transition: all 0.2s;
}

.refresh-btn:hover:not(:disabled) {
  background: rgba(255, 224, 74, 0.16);
  box-shadow: 0 0 12px rgba(255, 209, 0, 0.25);
}

.refresh-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.menu-error {
  margin-bottom: 12px;
}

.dish-skeleton {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.skeleton-block {
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 14px;
}

/* ============ 菜品列表行 ============ */
.dish-list {
  display: flex;
  flex-direction: column;
}

.dish-card {
  display: flex;
  gap: 16px;
  padding: 16px 12px;
  border-radius: 14px;
  border: 1px solid transparent;
  border-bottom-color: rgba(255, 255, 255, 0.07);
  transition: background 0.2s, box-shadow 0.2s, border-color 0.2s, transform 0.2s;
  position: relative;
}

.dish-card:hover {
  background: rgba(255, 255, 255, 0.045);
  transform: translateX(2px);
}

.dish-card.highlighted {
  border-color: rgba(255, 209, 0, 0.65);
  background: rgba(255, 209, 0, 0.07);
  box-shadow: 0 0 24px rgba(255, 209, 0, 0.18), inset 0 0 24px rgba(255, 209, 0, 0.05);
}

.dish-card.flashing {
  animation: flashPulse 0.9s ease-in-out 1;
}

@keyframes flashPulse {
  0%   { transform: scale(1);    box-shadow: 0 0 0 0 rgba(255, 209, 0, 0); }
  35%  { transform: scale(1.01); box-shadow: 0 0 0 12px rgba(255, 209, 0, 0.16); }
  100% { transform: scale(1);    box-shadow: 0 0 0 0 rgba(255, 209, 0, 0); }
}

/* 菜品图 */
.dish-thumb {
  position: relative;
  width: 116px;
  height: 116px;
  border-radius: 14px;
  flex-shrink: 0;
  overflow: hidden;
  border: 1px solid var(--line);
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.45);
}

.thumb-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transition: transform 0.35s;
}

.dish-card:hover .thumb-img {
  transform: scale(1.08);
}

.thumb-fallback {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.thumb-emoji {
  font-size: 46px;
  filter: drop-shadow(0 3px 6px rgba(0, 0, 0, 0.4));
}

.ai-badge {
  position: absolute;
  top: 0;
  left: 0;
  background: linear-gradient(135deg, var(--neon-pink), #FF8A00);
  color: #FFFFFF;
  font-size: 10px;
  font-weight: 800;
  padding: 4px 9px;
  border-radius: 13px 0 13px 0;
  letter-spacing: 0.5px;
  box-shadow: 0 0 12px rgba(255, 61, 129, 0.6);
}

/* 菜品信息 */
.dish-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.dish-name {
  font-size: 16px;
  font-weight: 800;
  color: var(--text-0);
  margin-bottom: 7px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.dish-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 7px;
}

.pill {
  font-size: 11px;
  border-radius: 5px;
  padding: 2px 8px;
  line-height: 1.6;
  border: 1px solid transparent;
}

.pill-cate {
  color: var(--text-1);
  background: rgba(255, 255, 255, 0.07);
  border-color: var(--line);
}

.pill-spice-0 { color: #7BE495; background: rgba(76, 210, 99, 0.12);  border-color: rgba(76, 210, 99, 0.3); }
.pill-spice-1 { color: #FFC46B; background: rgba(255, 184, 0, 0.12);  border-color: rgba(255, 184, 0, 0.35); }
.pill-spice-2 { color: #FF8A70; background: rgba(255, 106, 61, 0.14); border-color: rgba(255, 106, 61, 0.4); }
.pill-spice-3 { color: #FFFFFF; background: linear-gradient(135deg, #FF4A26, #C81E0E); box-shadow: 0 0 10px rgba(255, 74, 38, 0.5); }

.pill-veg {
  color: #7BE495;
  background: rgba(76, 210, 99, 0.12);
  border-color: rgba(76, 210, 99, 0.3);
}

.dish-desc {
  font-size: 12.5px;
  color: var(--text-2);
  line-height: 1.55;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin-bottom: 8px;
}

.dish-bottom {
  margin-top: auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.dish-price {
  color: var(--price);
  font-size: 20px;
  font-weight: 800;
  text-shadow: 0 0 16px rgba(255, 106, 61, 0.45);
}

/* 步进器 */
.dish-actions,
.cart-line-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.step-btn {
  width: 27px;
  height: 27px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
  font-weight: 700;
  transition: all 0.15s;
  line-height: 1;
}

.step-plus {
  background: linear-gradient(135deg, #FFE04A, var(--yellow-2));
  color: #1A1A1A;
  box-shadow: 0 0 12px rgba(255, 209, 0, 0.45);
}

.step-plus:hover {
  transform: scale(1.12);
  box-shadow: 0 0 20px rgba(255, 209, 0, 0.65);
}

.step-minus {
  background: rgba(255, 255, 255, 0.06);
  color: var(--text-1);
  border: 1.5px solid var(--line);
}

.step-minus:hover {
  border-color: rgba(255, 255, 255, 0.35);
  color: var(--text-0);
}

.step-qty {
  min-width: 18px;
  text-align: center;
  font-size: 14px;
  font-weight: 800;
  color: var(--text-0);
}

/* ============ 底部购物车结算栏 ============ */
.cart-bar {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 150;
  display: flex;
  justify-content: center;
  padding: 12px 20px 16px;
  pointer-events: none;
}

.cart-bar-inner {
  pointer-events: auto;
  width: 100%;
  max-width: 880px;
  height: 62px;
  background: rgba(12, 16, 32, 0.86);
  backdrop-filter: blur(22px);
  -webkit-backdrop-filter: blur(22px);
  border: 1px solid rgba(255, 209, 0, 0.3);
  border-radius: 999px;
  display: flex;
  align-items: center;
  padding: 0 8px 0 12px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.6), 0 0 28px rgba(255, 209, 0, 0.12);
}

.cart-icon-wrap {
  cursor: pointer;
  flex-shrink: 0;
}

.cart-icon {
  position: relative;
  width: 52px;
  height: 52px;
  margin-top: -14px;
  border-radius: 50%;
  background: linear-gradient(180deg, #FFE04A, var(--yellow-2));
  border: 3px solid rgba(7, 10, 20, 0.9);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  box-shadow: 0 0 20px rgba(255, 209, 0, 0.5);
  transition: transform 0.15s;
}

.cart-icon-wrap:hover .cart-icon {
  transform: scale(1.06);
}

.cart-icon.empty {
  filter: grayscale(0.85);
  opacity: 0.6;
  box-shadow: none;
}

.cart-badge {
  position: absolute;
  top: -6px;
  right: -6px;
  background: var(--neon-pink);
  color: #FFFFFF;
  font-size: 11px;
  font-weight: 700;
  min-width: 20px;
  height: 20px;
  border-radius: 999px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 5px;
  border: 2px solid rgba(7, 10, 20, 0.9);
  box-shadow: 0 0 10px rgba(255, 61, 129, 0.7);
}

.cart-total {
  flex: 1;
  padding: 0 16px;
  color: var(--text-0);
  cursor: pointer;
  min-width: 0;
}

.total-price {
  font-size: 21px;
  font-weight: 800;
  line-height: 1.2;
  color: #FFE04A;
  text-shadow: 0 0 16px rgba(255, 209, 0, 0.5);
}

.total-hint {
  font-size: 11px;
  color: var(--text-2);
}

.total-empty {
  font-size: 13px;
  color: var(--text-2);
}

.checkout-btn {
  flex-shrink: 0;
  height: 44px;
  padding: 0 30px;
  border-radius: 999px;
  background: linear-gradient(135deg, #FFE04A, var(--yellow-2));
  color: #1A1A1A;
  font-size: 16px;
  font-weight: 800;
  transition: all 0.2s;
  box-shadow: 0 0 18px rgba(255, 209, 0, 0.4);
}

.checkout-btn:hover:not(.disabled) {
  transform: translateY(-1px);
  box-shadow: 0 0 30px rgba(255, 209, 0, 0.6);
}

.checkout-btn.disabled {
  background: rgba(255, 255, 255, 0.08);
  color: var(--text-2);
  cursor: not-allowed;
  box-shadow: none;
}

.checkout-btn.small {
  height: 40px;
  padding: 0 24px;
  font-size: 15px;
}

/* ============ 抽屉 / 对话框暗色适配 ============ */
.el-drawer.mt-drawer,
.mt-drawer .el-drawer {
  background: #0D1226;
  border-left: 1px solid var(--line);
}

.mt-drawer .el-drawer__header {
  margin-bottom: 0;
  padding: 16px 20px;
  border-bottom: 1px solid var(--line);
  color: var(--text-0);
  font-weight: 800;
}

.mt-drawer .el-drawer__title {
  color: var(--text-0);
}

.mt-drawer .el-drawer__headerbtn .el-drawer__close {
  color: var(--text-2);
}

.mt-drawer .el-drawer__body {
  padding: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  color: var(--text-0);
}

.mt-drawer .el-drawer__footer {
  border-top: 1px solid var(--line);
  padding: 12px 20px;
}

/* 购物车抽屉 */
.cart-drawer-body {
  flex: 1;
  overflow-y: auto;
  padding: 14px 16px;
}

.cart-drawer-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
  color: var(--text-2);
  margin-bottom: 12px;
}

.clear-cart-btn {
  font-size: 12.5px;
  color: #FF8A70;
  transition: opacity 0.2s;
}

.clear-cart-btn:hover {
  opacity: 0.75;
}

.cart-lines {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.cart-line {
  display: flex;
  align-items: center;
  gap: 10px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 10px;
}

.cart-line-thumb {
  width: 54px;
  height: 54px;
  border-radius: 10px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 26px;
  flex-shrink: 0;
  background: rgba(255, 255, 255, 0.06);
}

.cart-line-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.cart-line-info {
  flex: 1;
  min-width: 0;
}

.cart-line-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-0);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.cart-line-price {
  font-size: 13px;
  color: var(--price);
  font-weight: 700;
  margin-top: 3px;
}

.cart-drawer-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.cart-drawer-total {
  font-size: 14px;
  color: var(--text-0);
}

.cart-drawer-total strong {
  font-size: 20px;
  color: #FFE04A;
  text-shadow: 0 0 14px rgba(255, 209, 0, 0.45);
}

/* 预订抽屉 */
.reservation-drawer-body {
  flex: 1;
  overflow-y: auto;
  padding: 14px 16px;
}

.reservation-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
  color: var(--text-2);
  margin-bottom: 12px;
}

.reservation-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.reservation-item {
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 12px 14px;
  background: rgba(255, 255, 255, 0.05);
}

.reservation-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 700;
  margin-bottom: 8px;
  font-size: 14px;
  color: var(--text-0);
}

.reservation-time {
  font-weight: 400;
  font-size: 12px;
  color: var(--text-2);
}

.reservation-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  font-size: 13px;
  color: var(--text-1);
}

.reservation-comments {
  margin-top: 8px;
  font-size: 13px;
  color: var(--text-0);
  background: rgba(255, 224, 74, 0.08);
  border: 1px solid rgba(255, 224, 74, 0.25);
  border-radius: 10px;
  padding: 8px 10px;
}

/* 结算对话框 */
.el-dialog.checkout-dialog,
.checkout-dialog .el-dialog {
  background: #0D1226;
  border: 1px solid var(--line);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.6), 0 0 40px rgba(255, 209, 0, 0.08);
}

.checkout-dialog .el-dialog__header {
  border-bottom: 1px solid var(--line);
  margin-right: 0;
  padding-bottom: 14px;
}

.checkout-dialog .el-dialog__title {
  font-weight: 800;
  color: var(--text-0);
}

.checkout-dialog .el-dialog__headerbtn .el-dialog__close {
  color: var(--text-2);
}

.checkout-dialog .el-dialog__body {
  color: var(--text-0);
}

.order-summary {
  max-height: 320px;
  overflow-y: auto;
}

.order-line {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 2px;
  border-bottom: 1px dashed var(--line);
  font-size: 14px;
}

.order-line-name {
  flex: 1;
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: var(--text-0);
}

.order-line-qty {
  color: var(--text-2);
  font-size: 13px;
}

.order-line-subtotal {
  color: var(--price);
  font-weight: 700;
  min-width: 70px;
  text-align: right;
}

.order-total-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 14px;
  font-size: 15px;
  color: var(--text-0);
}

.order-total-line strong {
  font-size: 22px;
  color: #FFE04A;
  text-shadow: 0 0 16px rgba(255, 209, 0, 0.5);
}

.checkout-dialog .el-button:not(.el-button--warning) {
  background: rgba(255, 255, 255, 0.08);
  border-color: var(--line);
  color: var(--text-0);
}

.confirm-order-btn {
  font-weight: 800;
  box-shadow: 0 0 16px rgba(255, 184, 0, 0.45);
}

/* 下单成功弹窗 */
.success-dialog .el-dialog__header {
  display: none;
}

.success-dialog .el-dialog__body {
  padding-top: 28px;
}

.order-success {
  text-align: center;
}

.success-icon {
  font-size: 56px;
  filter: drop-shadow(0 0 18px rgba(76, 210, 99, 0.6));
  animation: successPop 0.45s cubic-bezier(0.34, 1.56, 0.64, 1);
}

@keyframes successPop {
  from { transform: scale(0.4); opacity: 0; }
  to   { transform: scale(1); opacity: 1; }
}

.success-title {
  margin-top: 10px;
  font-size: 22px;
  font-weight: 800;
  background: linear-gradient(92deg, #FFE04A 10%, #7BE495 90%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.success-sub {
  margin-top: 4px;
  font-size: 13px;
  color: var(--text-2);
}

.success-card {
  margin-top: 18px;
  text-align: left;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 6px 16px;
}

.success-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 9px 0;
  border-bottom: 1px dashed var(--line);
  font-size: 13px;
  color: var(--text-2);
}

.success-line:last-child {
  border-bottom: none;
}

.success-line strong {
  color: var(--text-0);
  font-weight: 700;
  font-size: 12.5px;
  word-break: break-all;
  text-align: right;
}

.success-line .money {
  font-size: 17px;
  color: #FFE04A;
  text-shadow: 0 0 14px rgba(255, 209, 0, 0.45);
}

.success-line .status {
  color: #FF8A70;
}

.success-note {
  margin-top: 14px;
  font-size: 11.5px;
  line-height: 1.7;
  color: var(--text-2);
  background: rgba(34, 211, 238, 0.06);
  border: 1px solid rgba(34, 211, 238, 0.25);
  border-radius: 10px;
  padding: 8px 12px;
  text-align: left;
}

/* 我的订单列表 */
.order-item-lines {
  margin: 6px 0 2px;
}

.order-item-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 3px 0;
  font-size: 12.5px;
  color: var(--text-1);
}

.order-item-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed var(--line);
}

.order-status {
  font-size: 12px;
  color: #FF8A70;
}

.order-total {
  font-size: 13px;
  font-weight: 800;
  color: #FFE04A;
}

/* Element Plus 暗色细节 */
.el-empty__description p {
  color: var(--text-2);
}

.el-skeleton__item {
  background: rgba(255, 255, 255, 0.08) !important;
}

/* ============ 响应式适配 ============ */
@media (max-width: 980px) {
  .page {
    grid-template-columns: 1fr;
  }

  /* 聊天面板变为左侧滑出浮层 */
  .chat-panel {
    position: fixed;
    top: 0;
    bottom: 0;
    left: 0;
    width: min(430px, 92vw);
    height: auto;
    min-height: 0;
    z-index: 500;
    border-radius: 0 18px 18px 0;
    transform: translateX(-105%);
    transition: transform 0.32s cubic-bezier(0.22, 1, 0.36, 1);
    background: rgba(10, 13, 26, 0.96);
  }

  #app.chat-open .chat-panel {
    transform: none;
    box-shadow: 20px 0 60px rgba(0, 0, 0, 0.6);
  }

  .chat-close {
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .top-bar-inner {
    flex-wrap: wrap;
    gap: 10px;
  }

  .search-box {
    order: 3;
    max-width: none;
    width: 100%;
  }

  .brand-sub {
    display: none;
  }
}

@media (max-width: 640px) {
  .page {
    padding: 0 10px;
  }

  .shop-card {
    flex-direction: column;
    min-height: 0;
  }

  /* 小屏时分类变为横向滑动条 */
  .cate-rail {
    width: 100%;
    position: static;
    max-height: none;
    display: flex;
    overflow-x: auto;
    padding: 10px;
    gap: 6px;
    border-right: none;
    border-bottom: 1px solid var(--line);
  }

  .cate-rail-title {
    display: none;
  }

  .cate-item {
    flex-shrink: 0;
    border-left: none;
    border-radius: 999px;
    padding: 6px 14px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid var(--line);
    gap: 5px;
  }

  .cate-item.active {
    background: linear-gradient(135deg, #FFE04A, var(--yellow-2));
    color: #1A1A1A;
    text-shadow: none;
    border-color: transparent;
  }

  .cate-item.active .cate-count {
    background: rgba(0, 0, 0, 0.15);
    color: #1A1A1A;
  }

  .dish-thumb {
    width: 92px;
    height: 92px;
  }

  .thumb-emoji {
    font-size: 36px;
  }

  .top-btn {
    padding: 0 12px;
    font-size: 13px;
  }

  .shop-tags {
    display: none;
  }

  .cart-bar {
    padding: 8px 10px 12px;
  }

  .shop-strip {
    padding: 0 10px;
  }
}
</style>
