<template>
  <Header />
  <div class="main box_center cf">
    <div class="userBox cf">
      <UserMenu />
      <div class="my_r">
        <div class="my_bookshelf">
          <div class="title cf">
            <h2 class="fl">阅读历史</h2>
          </div>
          <div v-if="total === 0" class="no_contet">暂无阅读记录</div>
          <div v-else class="historyList">
            <div
              v-for="(item, index) in histories"
              :key="index"
              class="history_item cf"
              @click="openHistory(item)"
            >
              <img
                class="cover"
                :src="imgBaseUrl + item.picUrl"
                onerror="this.src='default.gif';this.onerror=null"
              />
              <div class="info">
                <div class="book_name">{{ item.bookName }}</div>
                <div class="book_author">{{ item.authorName }}</div>
                <div class="chapter_name">上次看到：{{ item.chapterName }}</div>
              </div>
              <div class="update_time">{{ item.updateTime }}</div>
            </div>
          </div>
          <el-pagination
            v-if="total > 0"
            small
            layout="prev, pager, next"
            :background="background"
            :page-size="pageSize"
            :total="total"
            class="mt-4"
            @current-change="handleCurrentChange"
          />
        </div>
      </div>
    </div>
  </div>
  <Footer />
</template>

<script>
import "@/assets/styles/user.css";
import { reactive, toRefs, onMounted } from "vue";
import { useRouter } from "vue-router";
import { listReadHistory } from "@/api/user";
import Header from "@/components/common/Header";
import Footer from "@/components/common/Footer";
import UserMenu from "@/components/user/Menu";

export default {
  name: "userHistory",
  components: {
    Header,
    Footer,
    UserMenu,
  },
  setup() {
    const router = useRouter();
    const state = reactive({
      histories: [],
      total: 0,
      pageSize: 10,
      background: true,
      imgBaseUrl: process.env.VUE_APP_BASE_IMG_URL,
    });

    const loadHistory = async (pageNum) => {
      const { data } = await listReadHistory({
        pageNum,
        pageSize: state.pageSize,
      });
      state.histories = data.list;
      state.total = Number(data.total);
    };

    const handleCurrentChange = (pageNum) => {
      loadHistory(pageNum);
    };

    const openHistory = (item) => {
      if (item.chapterId) {
        router.push({ path: `/book/${item.bookId}/${item.chapterId}` });
      } else {
        router.push({ path: `/book/${item.bookId}` });
      }
    };

    onMounted(() => {
      loadHistory(1);
    });

    return {
      ...toRefs(state),
      handleCurrentChange,
      openHistory,
    };
  },
};
</script>

<style scoped>
.historyList {
  padding: 0 10px;
}
.history_item {
  padding: 16px 10px;
  border-bottom: 1px solid var(--nv-border-lighter);
  cursor: pointer;
}
.history_item:hover {
  background: var(--nv-bg-subtle);
}
.cover {
  width: 64px;
  height: 84px;
  float: left;
  margin-right: 16px;
  background: var(--nv-image-placeholder);
}
.info {
  float: left;
  width: 420px;
}
.book_name {
  font-size: 16px;
  color: var(--nv-text-primary);
  line-height: 28px;
}
.book_author,
.chapter_name {
  font-size: 13px;
  color: var(--nv-text-weak);
  line-height: 24px;
}
.update_time {
  float: right;
  font-size: 13px;
  color: var(--nv-text-time);
  line-height: 84px;
}
.no_contet {
  padding: 120px 0;
  text-align: center;
  color: var(--nv-text-weak);
}
.el-pagination {
  justify-content: center;
}
</style>
