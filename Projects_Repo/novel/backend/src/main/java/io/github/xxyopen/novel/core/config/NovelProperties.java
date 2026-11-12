package io.github.xxyopen.novel.core.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

/**
 * novel 自定义配置属性（管理员账号等）
 *
 * @author xiongxiaoyang
 * @date 2026/10/20
 */
@ConfigurationProperties(prefix = "novel")
public record NovelProperties(Admin admin) {

    /**
     * 管理员账号配置
     *
     * @param username 管理员账号名
     * @param password 管理员账号密码
     */
    public record Admin(String username, String password) {

    }
}
