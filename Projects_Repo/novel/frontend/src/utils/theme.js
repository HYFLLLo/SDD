const themeKey = "novel-theme";

const darkClass = "dark";

const lightTheme = "light";

const darkTheme = "dark";

// localStorage 在隐私模式 / 禁用存储时读写会抛错，必须容错，不能阻断渲染
const readStoredTheme = () => {
  try {
    const value = localStorage.getItem(themeKey);
    return value === darkTheme || value === lightTheme ? value : "";
  } catch (e) {
    /* 存储不可用时按未设置处理 */
    return "";
  }
};

const writeStoredTheme = (theme) => {
  try {
    localStorage.setItem(themeKey, theme);
  } catch (e) {
    /* 存储不可用时忽略，仅本次会话生效 */
  }
};

// 同步 Element Plus 深色选择器（html.dark）与浏览器原生控件配色
const applyTheme = (theme) => {
  const root = document.documentElement;
  if (theme === darkTheme) {
    root.classList.add(darkClass);
  } else {
    root.classList.remove(darkClass);
  }
  root.style.colorScheme = theme;
};

// 只读：无值或非法值一律按 light
export const getStoredTheme = () => {
  return readStoredTheme() || lightTheme;
};

export const isDark = () => {
  return document.documentElement.classList.contains(darkClass);
};

export const setTheme = (theme) => {
  const next = theme === darkTheme ? darkTheme : lightTheme;
  applyTheme(next);
  writeStoredTheme(next);
  return next;
};

export const toggleTheme = () => {
  return setTheme(isDark() ? lightTheme : darkTheme);
};

// 必须在 app.mount('#app') 之前同步调用，避免深色偏好用户刷新时首帧闪白
export const initTheme = () => {
  const theme = readStoredTheme() || lightTheme;
  applyTheme(theme);
  return theme;
};
