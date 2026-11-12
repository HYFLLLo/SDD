package io.github.xxyopen.novel.core.config;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import io.github.xxyopen.novel.core.constant.DatabaseConsts;
import io.github.xxyopen.novel.dao.entity.UserInfo;
import io.github.xxyopen.novel.dao.mapper.UserInfoMapper;
import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.stereotype.Component;
import org.springframework.util.DigestUtils;
import org.springframework.util.StringUtils;

/**
 * 管理员账号初始化器。
 * <p>
 * 应用启动时幂等创建管理员账号（username 来自 novel.admin.username，密码来自 novel.admin.password）：
 * 先查 user_info 是否已存在该 username，不存在则插入，重复启动不会重复插入。
 * 密码加密口径与 {@code UserServiceImpl.login} 一致：MD5(明文)，salt='0'。
 */
@Component
@RequiredArgsConstructor
@EnableConfigurationProperties(NovelProperties.class)
@Slf4j
public class AdminUserInitializer implements CommandLineRunner {

    private final UserInfoMapper userInfoMapper;

    private final NovelProperties novelProperties;

    @Override
    public void run(String... args) {
        NovelProperties.Admin admin = novelProperties.admin();
        if (admin == null || !StringUtils.hasText(admin.username())) {
            log.warn("未配置 novel.admin.username，跳过管理员账号初始化");
            return;
        }
        String username = admin.username();
        String password = admin.password();

        QueryWrapper<UserInfo> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq(DatabaseConsts.UserInfoTable.COLUMN_USERNAME, username)
            .last(DatabaseConsts.SqlEnum.LIMIT_1.getSql());
        if (userInfoMapper.selectCount(queryWrapper) > 0) {
            log.info("管理员账号 {} 已存在，跳过初始化", username);
            return;
        }

        UserInfo userInfo = new UserInfo();
        userInfo.setUsername(username);
        // 与 UserServiceImpl.login 同口径：MD5(明文)，salt='0'
        userInfo.setPassword(
            DigestUtils.md5DigestAsHex(password.getBytes(StandardCharsets.UTF_8)));
        userInfo.setSalt("0");
        userInfo.setNickName(username);
        userInfo.setStatus(0);
        userInfo.setAccountBalance(0L);
        userInfo.setCreateTime(LocalDateTime.now());
        userInfo.setUpdateTime(LocalDateTime.now());
        try {
            userInfoMapper.insert(userInfo);
            log.info("管理员账号 {} 初始化成功", username);
        } catch (DuplicateKeyException e) {
            // 并发/重复启动场景：唯一键 uk_username 冲突视为已存在
            log.info("管理员账号 {} 已存在（唯一键冲突），忽略", username);
        }
    }
}
