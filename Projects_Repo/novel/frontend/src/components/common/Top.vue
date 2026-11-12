 <template>
  <div class="topMain">
    <div class="box_center cf">
      <router-link :to="{ name: 'home' }" class="logo fl"
        ><img :src="logoUrl" alt="小说精品屋"
      /></router-link>
      <div class="searchBar fl">
        <div class="search cf">
          <input
            v-model="keyword"
            type="text"
            placeholder="书名、作者、关键字"
            class="s_int"
            v-on:keyup.enter="searchByK"
          />
          <label class="search_btn" id="btnSearch" @click="searchByK()"
            ><i class="icon"></i
          ></label>
        </div>
      </div>

      <div class="bookShelf fr" id="headerUserInfo">
        <!--
        <a class="sj_link" href="/user/favorites.html">我的书架</a>-->
        <a
          href="javascript:void(0)"
          class="theme_switch"
          role="button"
          :title="themeTitle"
          :aria-label="themeTitle"
          @click="onToggleTheme"
        >
          <el-icon :size="20">
            <Sunny v-if="dark" />
            <Moon v-else />
          </el-icon>
        </a>
        <span v-if="!token" class="user_link"
          ><!--<i class="line mr20">|</i
          >-->
          <router-link :to="{ name: 'login' }" class="mr15">登录</router-link>
          <router-link :to="{ name: 'register' }" class="mr15"
            >注册</router-link
          >
        </span>
        <span v-if="token" class="user_link"
          ><!--<i class="line mr20">|</i
          >--><router-link :to="{name:'userSetup'}" class="mr15">{{ nickName }}</router-link>
          <a @click="logout" href="javascript:void(0)">退出</a></span
        >
      </div>
    </div>
  </div>
</template>

<script>
import logo from "@/assets/images/logo.png";
import logoWhite from "@/assets/images/logo_white.png";
import { reactive, toRefs, onMounted, ref, computed } from "vue";
import { Moon, Sunny } from "@element-plus/icons-vue";
import { useRouter, useRoute } from "vue-router";
import { getToken, getNickName, removeToken, removeNickName,removeUid, removeAdmin } from "@/utils/auth";
import { isDark, toggleTheme } from "@/utils/theme";
export default {
  name: "Top",
  components: { Moon, Sunny },
  setup(props, context) {
    const state = reactive({
      keyword: "",
      nickName: getNickName(),
      token: getToken(),
    });
    state.nickName = getNickName();
    state.token = getToken();
    const dark = ref(isDark());
    // 深色下顶栏为深底，深色字 logo 不可读，切换为同源白字版本（其余尺寸不变）
    const logoUrl = computed(() => (dark.value ? logoWhite : logo));
    const themeTitle = computed(() =>
      dark.value ? "切换为浅色主题" : "切换为深色主题"
    );
    const onToggleTheme = () => {
      toggleTheme();
      dark.value = isDark();
    };
    const route = useRoute();
    const router = useRouter();
    state.keyword = route.query.key;
    const searchByK = () => {
      router.push({ path: "/bookclass", query: { key: state.keyword } });
      context.emit("eventSerch", state.keyword);
    };
    const logout = () => {
      removeToken();
      removeNickName();
      removeUid()
      removeAdmin()
      state.nickName = "";
      state.token = "";
    };
    return {
      ...toRefs(state),
      logoUrl,
      dark,
      themeTitle,
      onToggleTheme,
      searchByK,
      logout,
    };
  },
};
</script>

<style scoped>
/* 主题切换入口：只控制色彩与内联尺寸，不改变 .topMain / .bookShelf 的高度与浮动布局 */
.theme_switch {
  float: right;
  display: flex;
  align-items: center;
  height: 38px;
  margin-left: 20px;
  cursor: pointer;
  color: var(--nv-text-regular);
}
.theme_switch:hover {
  color: var(--nv-brand-hover);
}
</style>