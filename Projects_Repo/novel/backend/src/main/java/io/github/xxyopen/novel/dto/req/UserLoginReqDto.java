package io.github.xxyopen.novel.dto.req;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;

/**
 * 用户登录 请求DTO
 *
 * @author xiongxiaoyang
 * @date 2022/5/16
 */
@Data
public class UserLoginReqDto {

    @Schema(description = "用户名/手机号", required = true, example = "18888888888")
    @NotBlank(message = "用户名不能为空！")
    private String username;

    @Schema(description = "密码", required = true, example = "123456")
    @NotBlank(message = "密码不能为空！")
    private String password;

}
