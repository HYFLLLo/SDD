import request from '../utils/request'

export function getImgVerifyCode() {
    return request.get('/front/resource/img_verify_code');
}

export function uploadImage(formData) {
    return request.post('/front/resource/image', formData, {
        headers: {
            'Content-Type': undefined
        }
    });
}
