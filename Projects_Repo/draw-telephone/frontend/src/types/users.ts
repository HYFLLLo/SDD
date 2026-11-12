/** GET /api/users/me 个人资料 */
export interface UserProfile {
  id: string
  username: string
  nickname: string
  avatar_url: string | null
  created_at: string
  participated_chains: number
  created_chains: number
}
