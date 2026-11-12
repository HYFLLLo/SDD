import request from '../utils/request'

export function listMyUploadBooks(params) {
    return request.get('/front/upload/books', { params });
}

export function updateBookStatus(bookId, bookStatus) {
    return request.put(`/front/upload/book/${bookId}/status`, { bookStatus });
}
export function updateBookAuthor(bookId, authorName) {
    return request.put(`/front/upload/book/${bookId}/author`, { authorName });
}

export function listAdminBooks(params) {
    return request.get('/front/upload/books/admin', { params });
}

export function updateBook(bookId, params) {
    return request.put(`/front/upload/book/${bookId}`, params);
}

export function updateBookCover(bookId, picUrl) {
    return request.put(`/front/upload/book/${bookId}/pic`, { picUrl });
}

export function replaceBookContent(bookId, formData) {
    return request.post(`/front/upload/book/${bookId}/content`, formData, {
        headers: {
            'Content-Type': undefined
        },
        timeout: 120000
    });
}

export function deleteBook(bookId) {
    return request.delete(`/front/upload/book/${bookId}`);
}
