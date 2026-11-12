<template>
  <Header />

  <div class="main box_center cf">
    <div class="uploadManageBox">
      <div class="uploadManageHeader">
        <h3 class="uploadManageTitle">我的上传</h3>
        <el-radio-group v-model="filterStatus" @change="handleFilterChange">
          <el-radio-button label="all">全部</el-radio-button>
          <el-radio-button label="0">连载中</el-radio-button>
          <el-radio-button label="1">已完结</el-radio-button>
        </el-radio-group>
      </div>

      <el-alert
        v-if="errorText"
        :title="errorText"
        type="error"
        :closable="false"
        show-icon
        class="uploadManageError"
      />

      <div v-loading="loading" class="uploadManageBody">
        <el-table :data="books" style="width: 100%" empty-text="暂无上传图书">
          <el-table-column prop="bookName" label="书名" min-width="180" show-overflow-tooltip />
          <el-table-column prop="authorName" label="作者" min-width="100" show-overflow-tooltip />
          <el-table-column prop="categoryName" label="分类" min-width="100" />
          <el-table-column label="字数" width="110">
            <template #default="scope">{{ Number(scope.row.wordCount || 0) }}</template>
          </el-table-column>
          <el-table-column label="章节数" width="90">
            <template #default="scope">{{ Number(scope.row.chapterCount || 0) }}</template>
          </el-table-column>
          <el-table-column prop="createTime" label="上传时间" width="170" />
          <el-table-column label="状态" width="90">
            <template #default="scope">
              <el-tag :type="Number(scope.row.bookStatus) === 1 ? 'success' : 'info'">
                {{ Number(scope.row.bookStatus) === 1 ? '已完结' : '连载中' }}
              </el-tag>
            </template>
          </el-table-column>
                    <el-table-column label="操作" width="230">
            <template #default="scope">
              <el-button
                size="small"
                :type="Number(scope.row.bookStatus) === 1 ? 'warning' : 'success'"
                :loading="updatingId === scope.row.id"
                :disabled="updatingId !== null && updatingId !== scope.row.id"
                @click="toggleStatus(scope.row)"
              >
                {{ Number(scope.row.bookStatus) === 1 ? '设为连载中' : '设为已完结' }}
              </el-button>
              <el-button size="small" @click="openAuthorDialog(scope.row)">改作者</el-button>
            </template>
          </el-table-column>
        </el-table>

        <div v-if="books.length" class="uploadManagePager">
          <el-pagination
            background
            layout="total, prev, pager, next"
            :total="total"
            :page-size="10"
            :current-page="pageNum"
            @current-change="handlePageChange"
          />
        </div>
      </div>
    </div>
  </div>

  <el-dialog v-model="authorDialogVisible" title="修改作者名" width="420px">
    <el-form :model="authorForm" label-width="80px">
      <el-form-item label="作者名">
        <el-input v-model="authorForm.authorName" maxlength="50" placeholder="请输入作者名" clearable />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="authorDialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="savingAuthorId !== null" @click="submitAuthor">保存</el-button>
    </template>
  </el-dialog>
  <Footer />
</template>

<script>
import { reactive, toRefs, onMounted } from "vue";
import { listMyUploadBooks, updateBookStatus, updateBookAuthor } from "@/api/upload";
import { ElMessage } from "element-plus";
import Header from "@/components/common/Header";
import Footer from "@/components/common/Footer";

export default {
  name: "MyUpload",
  components: {
    Header,
    Footer,
  },
  setup() {
    const state = reactive({
      books: [],
      loading: false,
      errorText: "",
      filterStatus: "all",
      pageNum: 1,
      pageSize: 10,
      total: 0,
      updatingId: null,
      authorDialogVisible: false,
      authorForm: { authorName: "" },
      editingBookId: null,
      savingAuthorId: null,
    });

    const loadBooks = async () => {
      state.loading = true;
      state.errorText = "";
      try {
        const params = { pageNum: state.pageNum, pageSize: state.pageSize };
        if (state.filterStatus !== "all") {
          params.bookStatus = Number(state.filterStatus);
        }
        const { data } = await listMyUploadBooks(params);
        state.books = data.list || [];
        state.total = Number(data.total || 0);
      } catch (err) {
        state.books = [];
        state.total = 0;
        state.errorText = (err && err.message) || "加载失败";
      } finally {
        state.loading = false;
      }
    };

    const handleFilterChange = () => {
      state.pageNum = 1;
      loadBooks();
    };

    const handlePageChange = (page) => {
      state.pageNum = page;
      loadBooks();
    };

    const toggleStatus = async (book) => {
      if (!book || state.updatingId) {
        return;
      }
      const target = Number(book.bookStatus) === 1 ? 0 : 1;
      state.updatingId = book.id;
      try {
        await updateBookStatus(book.id, target);
        await loadBooks();
      } catch (err) {
        // request.js 已统一弹出错误提示
      } finally {
        state.updatingId = null;
      }
    };

    const openAuthorDialog = (book) => {
      if (!book) {
        return;
      }
      state.editingBookId = book.id;
      state.authorForm.authorName = book.authorName || "";
      state.authorDialogVisible = true;
    };

    const submitAuthor = async () => {
      const name = (state.authorForm.authorName || "").trim();
      if (!name) {
        ElMessage.error("作者名不能为空！");
        return;
      }
      if (!state.editingBookId || state.savingAuthorId !== null) {
        return;
      }
      state.savingAuthorId = state.editingBookId;
      try {
        await updateBookAuthor(state.editingBookId, name);
        state.authorDialogVisible = false;
        await loadBooks();
      } catch (err) {
        // request.js 已统一弹出错误提示
      } finally {
        state.savingAuthorId = null;
      }
    };
    onMounted(() => {
      loadBooks();
    });

    return {
      ...toRefs(state),
      handleFilterChange,
      handlePageChange,
      toggleStatus,
      openAuthorDialog,
      submitAuthor,
    };
  },
};
</script>

<style scoped>
.uploadManageBox {
  width: 100%;
  min-height: 560px;
  background: var(--nv-bg-container);
  border-radius: 6px;
  padding: 20px;
  box-sizing: border-box;
}
.uploadManageHeader {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.uploadManageTitle {
  margin: 0;
  font-size: 20px;
  color: var(--nv-text-primary);
  font-weight: normal;
}
.uploadManageError {
  margin-bottom: 12px;
}
.uploadManageBody {
  min-height: 420px;
}
.uploadManagePager {
  margin-top: 16px;
  text-align: right;
}
</style>
