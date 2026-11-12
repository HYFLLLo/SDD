import { Navigate, createBrowserRouter } from 'react-router-dom'
import AppShell from '../components/AppShell'
import HomePage from '../pages/HomePage'
import TagManagementPage from '../pages/TagManagementPage'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppShell />,
    children: [
      {
        index: true,
        element: <HomePage />,
      },
      {
        path: 'tags',
        element: <TagManagementPage />,
      },
      {
        path: '*',
        element: <Navigate to="/" replace />,
      },
    ],
  },
])
