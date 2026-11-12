<template>
  <Header />

  <div class="main box_center cf">
    <div class="uploadManageBox">
      <div class="uploadManageHeader">
        <h3 class="uploadManageTitle">书籍管理</h3>
        <div class="searchBar">
          <el-input
            v-model="query.bookName"
            placeholder="书名关键字"
            clearable
            style="width: 220px"
            @keyup.enter="handleSearch"
            @clear="handleSearch"
          />
          <el-select
            v-model="query.bookStatus"
            clearable
            placeholder="全部状态"
            style="width: 140px"
            @change="handleSearch"
          >
            <el-option label="连载中" :value="0" />
            <el-option label="已完结" :value="1" />
          </el-select>
          <el-button type="primary" @click="handleSearch">查询</el-button>
        </div>
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
        <el-table :data="books" style="width: 100%" empty-text="暂无书籍">
          <el-table-column label="封面" width="90">
            <template #default="scope">
              <img
                class="bookCover"
                :src="imgBaseUrl + scope.row.picUrl"
                onerror="this.src='default.gif';this.onerror=null"
              />
            </template>
          </el-table-column>
          <el-table-column prop="bookName" label="书名" min-width="160" show-overflow-tooltip />
          <el-table-column prop="authorName" label="作者" min-width="100" show-overflow-tooltip />
          <el-table-column prop="categoryName" label="分类" min-width="100" />
          <el-table-column label="字数" width="100">
            <template #default="scope">{{ Number(scope.row.wordCount || 0) }}</template>
          </el-table-column>
          <el-table-column label="章节数" width="90">
            <template #default="scope">{{ Number(scope.row.chapterCount || 0) }}</template>
          </el-table-column>
          <el-table-column prop="updateTime" label="更新时间" width="170" />
          <el-table-column label="状态" width="90">
            <template #default="scope">
              <el-tag :type="Number(scope.row.bookStatus) === 1 ? 'success' : 'info'">
                {{ Number(scope.row.bookStatus) === 1 ? '已完结' : '连载中' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="320" fixed="right">
            <template #default="scope">
              <el-button size="small" @click="openEditDialog(scope.row)">编辑</el-button>
              <el-button size="small" type="primary" @click="openContentDialog(scope.row)">
                替换内容
              </el-button>
              <el-button size="small" @click="openCoverDialog(scope.row)">封面</el-button>
              <el-button size="small" type="danger" @click="removeBook(scope.row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <div v-if="books.length" class="uploadManagePager">
          <el-pagination
            background
            layout="total, prev, pager, next"
            :total="total"
            :page-size="pageSize"
            :current-page="pageNum"
            @current-change="handlePageChange"
          />
        </div>
      </div>
    </div>
  </div>

  <el-dialog v-model="editDialogVisible" title="编辑书籍信息" width="560px">
    <el-form :model="editForm" label-width="90px">
      <el-form-item label="书名">
        <el-input v-model="editForm.bookName" maxlength="50" clearable />
      </el-form-item>
      <el-form-item label="作者名">
        <el-input v-model="editForm.authorName" maxlength="50" clearable />
      </el-form-item>
      <el-form-item label="作品方向">
        <el-radio-group v-model="editForm.workDirection" @change="handleWorkDirectionChange">
          <el-radio :label="0">男频</el-radio>
          <el-radio :label="1">女频</el-radio>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="分类">
        <el-select
          v-model="editForm.categoryId"
          filterable
          placeholder="请选择分类"
          style="width: 100%"
          @change="handleCategoryChange"
        >
          <el-option
            v-for="item in categoryList"
            :key="item.id"
            :label="item.name"
            :value="item.id"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="简介">
        <el-input
          v-model="editForm.bookDesc"
          type="textarea"
          :rows="4"
          maxlength="2000"
          show-word-limit
        />
      </el-form-item>
      <el-form-item label="状态">
        <el-radio-group v-model="editForm.bookStatus">
          <el-radio :label="0">连载中</el-radio>
          <el-radio :label="1">已完结</el-radio>
        </el-radio-group>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="editDialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="savingId !== null" @click="submitEdit">保存</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="contentDialogVisible" title="替换书籍内容" width="560px">
    <el-alert
      title="替换后会删除原章节并重新导入，原阅读进度将失效。"
      type="warning"
      :closable="false"
      show-icon
      class="contentAlert"
    />
    <div class="currentBook">
      当前书籍：{{ currentBook ? currentBook.bookName : '' }}
    </div>
    <el-upload
      drag
      action="#"
      :auto-upload="false"
      :limit="1"
      accept=".txt,.epub"
      :on-change="handleContentFileChange"
      :on-remove="handleContentFileRemove"
    >
      <div class="el-upload__text">将 txt / epub 文件拖到此处，或<em>点击上传</em></div>
    </el-upload>
    <template #footer>
      <el-button @click="contentDialogVisible = false">取消</el-button>
      <el-button
        type="primary"
        :disabled="!contentFile"
        :loading="replacingId !== null"
        @click="submitContent"
      >
        开始替换
      </el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="coverDialogVisible" title="修改书籍封面" width="420px">
    <div class="currentBook">
      当前书籍：{{ currentBook ? currentBook.bookName : '' }}
    </div>
    <div class="coverUploader">
      <el-upload
        action="#"
        :auto-upload="false"
        :show-file-list="false"
        accept="image/*"
        :on-change="handleCoverFileChange"
      >
        <img v-if="coverPreviewUrl" :src="coverPreviewUrl" class="coverPreview" />
        <div v-else class="uploadPlus">+</div>
      </el-upload>
    </div>
    <template #footer>
      <el-button @click="coverDialogVisible = false">取消</el-button>
      <el-button
        type="primary"
        :disabled="!coverFile"
        :loading="uploadingCoverId !== null"
        @click="submitCover"
      >
        上传并保存
      </el-button>
    </template>
  </el-dialog>

  <Footer />
</template>

<script>
import { reactive, toRefs, onMounted } from "vue";
import {
  listAdminBooks,
  updateBook,
  updateBookCover,
  replaceBookContent,
  deleteBook,
} from "@/api/upload";
import { listCategorys } from "@/api/book";
import { uploadImage } from "@/api/resource";
import { ElMessage, ElMessageBox } from "element-plus";
import Header from "@/components/common/Header";
import Footer from "@/components/common/Footer";

export default {
  name: "BookManage",
  components: {
    Header,
    Footer,
  },
  setup() {
    const state = reactive({
      books: [],
      loading: false,
      errorText: "",
      pageNum: 1,
      pageSize: 10,
      total: 0,
      imgBaseUrl: process.env.VUE_APP_BASE_IMG_URL,
      query: {
        bookName: "",
        bookStatus: null,
      },
      editDialogVisible: false,
      editForm: {
        bookName: "",
        authorName: "",
        workDirection: 0,
        categoryId: null,
        categoryName: "",
        bookDesc: "",
        bookStatus: 0,
      },
      editingBookId: null,
      savingId: null,
      categoryList: [],
      contentDialogVisible: false,
      currentBook: null,
      contentFile: null,
      replacingId: null,
      coverDialogVisible: false,
      coverFile: null,
      coverPreviewUrl: "",
      uploadingCoverId: null,
    });

    const loadBooks = async () => {
      state.loading = true;
      state.errorText = "";
      try {
        const params = {
          pageNum: state.pageNum,
          pageSize: state.pageSize,
        };
        if (state.query.bookName) {
          params.bookName = state.query.bookName.trim();
        }
        if (state.query.bookStatus !== null && state.query.bookStatus !== "") {
          params.bookStatus = Number(state.query.bookStatus);
        }
        const { data } = await listAdminBooks(params);
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

    const handleSearch = () => {
      state.pageNum = 1;
      loadBooks();
    };

    const handlePageChange = (page) => {
      state.pageNum = page;
      loadBooks();
    };

    const loadCategoryList = async (workDirection) => {
      const { data } = await listCategorys({ workDirection });
      state.categoryList = data || [];
    };

    const openEditDialog = async (book) => {
      if (!book) {
        return;
      }
      state.editingBookId = book.id;
      state.editForm = {
        bookName: book.bookName || "",
        authorName: book.authorName || "",
        workDirection: Number(book.workDirection || 0),
        categoryId: book.categoryId || null,
        categoryName: book.categoryName || "",
        bookDesc: book.bookDesc || "",
        bookStatus: Number(book.bookStatus || 0),
      };
      try {
        await loadCategoryList(state.editForm.workDirection);
      } catch (err) {
        state.categoryList = [];
      }
      state.editDialogVisible = true;
    };

    const handleWorkDirectionChange = async () => {
      await loadCategoryList(state.editForm.workDirection);
      state.editForm.categoryId = state.categoryList.length
        ? state.categoryList[0].id
        : null;
      state.editForm.categoryName = state.categoryList.length
        ? state.categoryList[0].name
        : "";
    };

    const handleCategoryChange = (categoryId) => {
      const item = state.categoryList.find((v) => v.id === categoryId);
      state.editForm.categoryName = item ? item.name : "";
    };

    const submitEdit = async () => {
      const form = state.editForm;
      if (!form.bookName || !form.authorName || !form.categoryId) {
        ElMessage.error("请填写书名、作者名和分类");
        return;
      }
      if (!state.editingBookId || state.savingId !== null) {
        return;
      }
      state.savingId = state.editingBookId;
      try {
        await updateBook(state.editingBookId, {
          bookName: form.bookName.trim(),
          authorName: form.authorName.trim(),
          workDirection: Number(form.workDirection),
          categoryId: form.categoryId,
          categoryName: form.categoryName,
          bookDesc: form.bookDesc || "",
          bookStatus: Number(form.bookStatus),
        });
        state.editDialogVisible = false;
        await loadBooks();
      } catch (err) {
        // request.js 已统一弹出错误提示
      } finally {
        state.savingId = null;
      }
    };

    const openContentDialog = (book) => {
      if (!book) {
        return;
      }
      state.currentBook = book;
      state.contentFile = null;
      state.contentDialogVisible = true;
    };

    const handleContentFileChange = (uploadFile) => {
      state.contentFile = uploadFile.raw || null;
    };

    const handleContentFileRemove = () => {
      state.contentFile = null;
    };

    const submitContent = async () => {
      if (!state.currentBook || !state.contentFile || state.replacingId !== null) {
        return;
      }
      const formData = new FormData();
      formData.append("file", state.contentFile);
      state.replacingId = state.currentBook.id;
      try {
        const { data } = await replaceBookContent(state.currentBook.id, formData);
        state.contentDialogVisible = false;
        ElMessage.success((data && data.message) || "替换成功");
        await loadBooks();
      } catch (err) {
        // request.js 已统一弹出错误提示
      } finally {
        state.replacingId = null;
      }
    };

    const openCoverDialog = (book) => {
      if (!book) {
        return;
      }
      state.currentBook = book;
      state.coverFile = null;
      state.coverPreviewUrl = "";
      state.coverDialogVisible = true;
    };

    const handleCoverFileChange = (uploadFile) => {
      state.coverFile = uploadFile.raw || null;
      state.coverPreviewUrl = state.coverFile
        ? URL.createObjectURL(state.coverFile)
        : "";
    };

    const submitCover = async () => {
      if (!state.currentBook || !state.coverFile || state.uploadingCoverId !== null) {
        return;
      }
      const formData = new FormData();
      formData.append("file", state.coverFile);
      state.uploadingCoverId = state.currentBook.id;
      try {
        const { data: picUrl } = await uploadImage(formData);
        await updateBookCover(state.currentBook.id, picUrl);
        state.coverDialogVisible = false;
        await loadBooks();
      } catch (err) {
        // request.js 已统一弹出错误提示
      } finally {
        state.uploadingCoverId = null;
      }
    };

    const removeBook = (book) => {
      if (!book) {
        return;
      }
      ElMessageBox.confirm(`确定删除《${book.bookName}》吗？此操作不可恢复。`, "删除确认", {
        confirmButtonText: "删除",
        cancelButtonText: "取消",
        type: "warning",
      })
        .then(async () => {
          await deleteBook(book.id);
          ElMessage.success("删除成功");
          if (state.books.length === 1 && state.pageNum > 1) {
            state.pageNum -= 1;
          }
          await loadBooks();
        })
        .catch(() => {
          // 用户取消删除
        });
    };

    onMounted(() => {
      loadBooks();
    });

    return {
      ...toRefs(state),
      handleSearch,
      handlePageChange,
      openEditDialog,
      handleWorkDirectionChange,
      handleCategoryChange,
      submitEdit,
      openContentDialog,
      handleContentFileChange,
      handleContentFileRemove,
      submitContent,
      openCoverDialog,
      handleCoverFileChange,
      submitCover,
      removeBook,
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
.searchBar {
  display: flex;
  align-items: center;
  gap: 10px;
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
.bookCover {
  width: 52px;
  height: 68px;
  object-fit: cover;
  background: var(--nv-image-placeholder);
}
.contentAlert {
  margin-bottom: 14px;
}
.currentBook {
  margin-bottom: 14px;
  color: var(--nv-text-secondary);
}
.coverUploader {
  display: flex;
  justify-content: center;
  padding: 12px 0;
}
.coverPreview {
  width: 160px;
  height: 210px;
  object-fit: cover;
  background: var(--nv-image-placeholder);
}
.uploadPlus {
  width: 160px;
  height: 210px;
  border: 1px dashed var(--nv-border-muted);
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  color: var(--nv-text-weak);
}
</style>
