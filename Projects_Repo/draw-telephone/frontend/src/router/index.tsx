import { createBrowserRouter } from 'react-router-dom'
import AppLayout from '../components/AppLayout'
import ProtectedRoute from './ProtectedRoute'
import PlazaPage from '../pages/PlazaPage'
import LoginPage from '../pages/LoginPage'
import CreateChainPage from '../pages/CreateChainPage'
import JoinChainPage from '../pages/JoinChainPage'
import ChainHallPage from '../pages/ChainHallPage'
import RelayPage from '../pages/RelayPage'
import WorkDetailPage from '../pages/WorkDetailPage'
import ReplayPage from '../pages/ReplayPage'
import ProfilePage from '../pages/ProfilePage'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    children: [
      { index: true, element: <PlazaPage /> },
      { path: 'login', element: <LoginPage /> },
      {
        path: 'create',
        element: (
          <ProtectedRoute>
            <CreateChainPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'join',
        element: (
          <ProtectedRoute>
            <JoinChainPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'chain/:id',
        element: (
          <ProtectedRoute>
            <ChainHallPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'chain/:id/relay',
        element: (
          <ProtectedRoute>
            <RelayPage />
          </ProtectedRoute>
        ),
      },
      { path: 'work/:id', element: <WorkDetailPage /> },
      { path: 'work/:id/replay', element: <ReplayPage /> },
      {
        path: 'profile',
        element: (
          <ProtectedRoute>
            <ProfilePage />
          </ProtectedRoute>
        ),
      },
    ],
  },
])
