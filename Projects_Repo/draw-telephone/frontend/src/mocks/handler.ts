import MockAdapter from 'axios-mock-adapter'
import api from '../services/api'
import {
  loginSuccessResponse,
  loginFailResponse,
  registerSuccessResponse,
  registerFailResponse,
} from './auth'
import { worksListResponse, buildWorkDetailResponse } from './works'
import {
  createChainResponse,
  chainLookupResponse,
  chainJoinResponse,
  chainDetailResponse,
} from './chains'
import { nodePreviousTextResponse, submitNodeResponse } from './nodes'
import { voteSubmitResponse, voteResultResponse } from './votes'
import { notificationsListResponse, notificationsReadResponse } from './notifications'
import { userProfileResponse, myWorksListResponse } from './users'
import { aiPromptResponse } from './ai'
import { uploadImageResponse } from './upload'

/**
 * 启用 Mock：VITE_USE_MOCK=true 时由 main.tsx 调用。
 * 所有响应均按 api-contracts.md 的 endpoint 显式构造 DTO。
 */
export function setupMock() {
  const mock = new MockAdapter(api, { delayResponse: 200 })

  // POST /api/auth/login
  mock.onPost('/auth/login').reply((config) => {
    const body = JSON.parse(config.data ?? '{}')
    if (body.username === 'mockuser' && body.password === 'mockpass') {
      return [200, loginSuccessResponse]
    }
    return [401, loginFailResponse]
  })

  // POST /api/auth/register
  mock.onPost('/auth/register').reply((config) => {
    const body = JSON.parse(config.data ?? '{}')
    if (body.username === 'mockuser') {
      return [400, registerFailResponse]
    }
    return [200, registerSuccessResponse]
  })

  // GET /api/works
  mock.onGet('/works').reply(() => [200, worksListResponse])

  // GET /api/works/:id
  mock.onGet(/\/works\/[^/]+$/).reply((config) => {
    const id = config.url?.split('/').pop() ?? ''
    return [200, buildWorkDetailResponse(id)]
  })

  // POST /api/chains
  mock.onPost('/chains').reply(() => [200, createChainResponse])

  // GET /api/chains/:room_code （加入前校验，room_code 为短码）
  mock.onGet(/\/chains\/[^/]+$/).reply(() => [200, chainLookupResponse])

  // POST /api/chains/:id/join
  mock.onPost(/\/chains\/[^/]+\/join$/).reply(() => [200, chainJoinResponse])

  // GET /api/chains/:id （链大厅详情）
  mock.onGet(/\/chains\/[^/]+$/).reply(() => [200, chainDetailResponse])

  // GET /api/nodes/:id/previous
  mock.onGet(/\/nodes\/[^/]+\/previous$/).reply(() => [200, nodePreviousTextResponse])

  // POST /api/nodes/:id/submit
  mock.onPost(/\/nodes\/[^/]+\/submit$/).reply(() => [200, submitNodeResponse])

  // POST /api/chains/:id/votes
  mock.onPost(/\/chains\/[^/]+\/votes$/).reply(() => [200, voteSubmitResponse])

  // GET /api/chains/:id/votes/result
  mock.onGet(/\/chains\/[^/]+\/votes\/result$/).reply(() => [200, voteResultResponse])

  // GET /api/notifications
  mock.onGet('/notifications').reply(() => [200, notificationsListResponse])

  // POST /api/notifications/read
  mock.onPost('/notifications/read').reply(() => [200, notificationsReadResponse])

  // GET /api/users/me
  mock.onGet('/users/me').reply(() => [200, userProfileResponse])

  // GET /api/users/me/works
  mock.onGet('/users/me/works').reply(() => [200, myWorksListResponse])

  // POST /api/ai/prompt
  mock.onPost('/ai/prompt').reply(() => [200, aiPromptResponse])

  // POST /api/upload/image
  mock.onPost('/upload/image').reply(() => [200, uploadImageResponse])

  return mock
}
