import { expect, test, type Page } from '@playwright/test'

const unique = `T008回归-${Date.now()}`

test('T-008 final browser regression', async ({ page }) => {
  await page.goto('/')
  await page.evaluate(() => localStorage.clear())
  await page.reload()
  await expect(page.getByRole('heading', { name: '创作者选题灵感库' })).toBeVisible()

  // Quick create: empty title validation, then valid record.
  await page.getByRole('button', { name: '快速记录' }).click()
  await expect(page.getByRole('dialog', { name: '快速灵感' })).toBeVisible()
  await page.getByRole('button', { name: '保存选题' }).click()
  await expect(page.getByText('标题不能为空')).toBeVisible()
  await page.getByPlaceholder('用一句话概括选题').fill(unique)
  await page.getByPlaceholder('补充内容方向或切入点').fill('E2E 回归内容')
  await page.getByRole('button', { name: '保存选题' }).click()
  await expect(page.getByText('保存成功').last()).toBeVisible()
  await expect(page.getByRole('dialog', { name: '快速灵感' })).toBeHidden()
  await expect(page.locator('.topic-card', { hasText: unique })).toBeVisible()

  // Search and clear.
  await page.getByPlaceholder('搜索标题、内容或标签').fill(unique)
  await expect(page.locator('.topic-card')).toHaveCount(1)
  await page.getByRole('button', { name: '清除' }).click()
  await page.getByPlaceholder('搜索标题、内容或标签').clear()
  await expect(page.getByText(/共 [7-9] 条/)).toBeVisible()

  // Status filter and sort.
  await page.locator('.topic-filter-select').nth(0).click()
  await page.locator('.ant-select-dropdown:not(.ant-select-dropdown-hidden)').getByTitle('已发布').click()
  await expect(page.getByText(/共 1 条/)).toBeVisible()
  await page.locator('.topic-filter-select').nth(0).click()
  await page.locator('.ant-select-dropdown:not(.ant-select-dropdown-hidden)').getByTitle('全部状态').click()
  await page.locator('.topic-filter-select').nth(3).click()
  await page.locator('.ant-select-dropdown:not(.ant-select-dropdown-hidden)').getByTitle('创建时间').click()
  await expect(page.getByText(/共 [7-9] 条/)).toBeVisible()
  await page.getByRole('button', { name: '清除' }).click()

  // Edit title.
  const edited = `${unique}-已编辑`
  await page.getByPlaceholder('搜索标题、内容或标签').fill(unique)
  await page.locator('.topic-card', { hasText: unique }).click()
  await expect(page.getByRole('dialog', { name: '选题详情' })).toBeVisible()
  await page.getByRole('button', { name: /编\s*辑/ }).click()
  await page.getByPlaceholder('请输入标题').fill(edited)
  await page.getByRole('button', { name: /保\s*存/ }).click()
  await expect(page.getByText('保存成功').last()).toBeVisible()
  await expect(page.getByRole('dialog', { name: '选题详情' }).getByRole('heading', { name: edited })).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog', { name: '选题详情' })).toBeHidden()

  // Kanban drag to working status.
  await page.locator('.ant-segmented-item', { hasText: '看板' }).click()
  await expect(page.locator('.kanban-column', { hasText: '待验证' }).locator('.kanban-card', { hasText: edited })).toBeVisible()
  await page.locator('.kanban-card', { hasText: edited }).dragTo(
    page.locator('.kanban-column', { hasText: '创作中' }).locator('.kanban-column__body'),
  )
  await expect(page.locator('.kanban-column', { hasText: '创作中' }).locator('.kanban-card', { hasText: edited })).toBeVisible()

  // Random topic from current non-empty pool.
  await page.getByRole('button', { name: '随机选题' }).click()
  await expect(page.getByRole('dialog', { name: '随机选题' })).toBeVisible()
  await expect(page.locator('.random-picker__card')).toBeVisible()
  await page.getByRole('button', { name: '换一个' }).click()
  await expect(page.locator('.random-picker__card')).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog', { name: '随机选题' })).toBeHidden()

  // Random empty pool from a genuinely empty filtered result set.
  await page.getByPlaceholder('搜索标题、内容或标签').fill('绝不存在的选题空池')
  await expect(page.getByText(/共 0 条/)).toBeVisible()
  await page.getByRole('button', { name: '随机选题' }).click()
  await expect(page.getByRole('dialog', { name: '随机选题' }).getByText('没有符合条件的选题，试试调整搜索或筛选条件')).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog', { name: '随机选题' })).toBeHidden()
  await page.getByPlaceholder('搜索标题、内容或标签').fill('')
  await expect(page.getByText(/共 [7-9] 条/)).toBeVisible()

  // Tag create, edit, delete on tag manager.
  await page.getByRole('button', { name: '标签管理' }).click()
  await expect(page.getByRole('heading', { name: '标签管理' })).toBeVisible()
  const tagName = `标${Date.now()}`
  await page.getByRole('button', { name: '新建标签' }).click()
  await page.getByPlaceholder('输入标签名称').fill(tagName)
  await page.getByRole('button', { name: /保\s*存/ }).click()
  await expect(page.locator('.tag-manager__card', { hasText: tagName })).toBeVisible()
  const editedTagName = `${tagName}-改`
  await page.locator('.tag-manager__card', { hasText: tagName }).getByRole('button', { name: /编\s*辑/ }).click()
  await page.getByPlaceholder('输入标签名称').fill(editedTagName)
  await page.getByRole('button', { name: /保\s*存/ }).click()
  await expect(page.locator('.tag-manager__card', { hasText: editedTagName })).toBeVisible()

  // Persistence after reload: topic title/status and tag edit remain.
  await page.reload()
  await expect(page.getByRole('heading', { name: '标签管理' })).toBeVisible()
  await expect(page.locator('.tag-manager__card', { hasText: editedTagName })).toBeVisible()
  const persistedTopics = await page.evaluate(() => localStorage.getItem('creator-topic-library.topics.v1'))
  const persistedTags = await page.evaluate(() => localStorage.getItem('creator-topic-library.tags.v1'))
  expect(persistedTopics).toBeTruthy()
  expect(persistedTags).toBeTruthy()
  expect(JSON.parse(persistedTopics ?? '[]').map((topic: { title: string }) => topic.title)).toContain(edited)
  expect(JSON.parse(persistedTags ?? '[]').map((tag: { name: string }) => tag.name)).toContain(editedTagName)
  const persistedTopic = JSON.parse(persistedTopics ?? '[]').find((topic: { title: string }) => topic.title === edited)
  expect(persistedTopic.status).toBe('working')

  // Delete created tag, then delete topic.
  await page.locator('.tag-manager__card', { hasText: editedTagName }).getByRole('button', { name: /删\s*除/ }).click()
  await page.locator('.ant-modal').getByRole('button', { name: /删\s*除/ }).click()
  await expect(page.locator('.tag-manager__card', { hasText: editedTagName })).toHaveCount(0)
  await page.getByRole('button', { name: '返回选题库' }).click()
  await page.getByPlaceholder('搜索标题、内容或标签').fill(edited)
  await expect(page.locator('.topic-card', { hasText: edited })).toBeVisible()
  await page.locator('.topic-card', { hasText: edited }).getByRole('button', { name: /删\s*除/ }).click()
  await page.locator('.ant-modal').getByRole('button', { name: /删\s*除/ }).click()
  await expect(page.getByText('没有符合条件的选题，试试调整搜索或筛选条件')).toBeVisible()
  await expect(page.locator('.topic-card', { hasText: edited })).toHaveCount(0)

  // No visible mock/debug/placeholder residue.
  const bodyText = await page.locator('body').innerText()
  expect(bodyText).not.toContain('[Mock]')
  expect(bodyText).not.toContain('调试')
  expect(bodyText).not.toContain('占位提示')
  expect(page.locator('text=/TODO|FIXME|HACK/')).toHaveCount(0)
})
