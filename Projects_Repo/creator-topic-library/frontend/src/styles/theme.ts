import type { ThemeConfig } from 'antd'

export const warmPaperTheme: ThemeConfig = {
  token: {
    colorPrimary: '#B85C38',
    colorInfo: '#B85C38',
    colorTextBase: '#3F2E22',
    colorBgBase: '#FBF4E8',
    colorBgLayout: '#F6ECDC',
    colorBgContainer: '#FFF9EF',
    colorBorder: '#E7D5BF',
    colorBorderSecondary: '#EFE2CE',
    borderRadius: 10,
    fontSize: 14,
    fontFamily:
      "'PingFang SC', 'Microsoft YaHei', 'Helvetica Neue', Arial, sans-serif",
  },
  components: {
    Layout: {
      headerBg: '#F6ECDC',
      bodyBg: '#F6ECDC',
    },
    Menu: {
      itemBg: 'transparent',
      horizontalItemSelectedColor: '#B85C38',
      horizontalItemHoverColor: '#8E4327',
    },
    Card: {
      headerBg: '#FFF9EF',
    },
    Tag: {
      defaultBg: '#F3E4D3',
    },
  },
}
