import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
// Element Plus 深色变量（选择器 html.dark）。必须用 require 而非 import：
// element-plus 的 sideEffects 声明为 "theme-chalk/*.css"，webpack 按 globstar=false 匹配，
// 不覆盖 theme-chalk/dark/ 子目录，production 构建会把 `import '...dark/css-vars.css'` 当纯副作用剔除，
// 导致 dist 里没有 html.dark 变量、深色下 el-* 组件仍是浅色。require 声明式引入可绕过该 tree-shaking。
require('element-plus/theme-chalk/dark/css-vars.css')
import App from './App.vue'
import router from '@/router'
import '@/assets/styles/base.css'
import '@/assets/styles/main.css'
import '@/assets/styles/theme.css'
import { Loading } from '@element-plus/icons-vue'
import { initTheme } from '@/utils/theme'

// 必须在挂载前同步执行，避免深色偏好用户刷新时首帧闪白
initTheme()

const app = createApp(App)

app.use(ElementPlus)

app.use(router)

app.mount('#app')

app.component('Loading', Loading)
