import { createRouter, createWebHistory, RouteLocationNormalized, NavigationGuardNext, RouteLocation } from 'vue-router'
import { store } from '../store'
import LoginView from '../views/auth/LoginView.vue'
import SetupView from '../views/setup/SetupView.vue'
import DashboardView from '../views/dashboard/DashboardView.vue'
import ApiTestView from '../views/dashboard/ApiTestView.vue'
import DocumentationView from '../views/docs/DocumentationView.vue'

const routes = [
  {
    path: '/setup',
    name: 'setup',
    component: SetupView,
    meta: { requiresAuth: false }
  },
  {
    path: '/login',
    name: 'login',
    component: LoginView,
    meta: { requiresAuth: false }
  },
  {
    path: '/dashboard',
    name: 'dashboard',
    component: DashboardView,
    meta: { requiresAuth: true }
  },
  {
    path: '/dashboard/api-test',
    name: 'api-test',
    component: ApiTestView,
    meta: { requiresAuth: true }
  },
  {
    path: '/',
    redirect: (to: RouteLocation) => {
      return store.getters['auth/isAuthenticated'] ? { name: 'dashboard' } : { name: 'login' }
    }
  },
  {
    path: '/docs/:path*',
    name: 'documentation',
    component: DocumentationView,
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Navigation guard
router.beforeEach(async (to, from, next) => {
  const requiresAuth = to.matched.some(record => record.meta.requiresAuth !== false)
  const isAuthenticated = store.getters['auth/isAuthenticated']

  try {
    // Check if setup is required
    const setupRequired = await store.dispatch('auth/checkSetupRequired')

    // Handle root path
    if (to.path === '/') {
      next({ name: setupRequired ? 'setup' : 'login' })
      return
    }

    // Handle other paths
    if (setupRequired && to.name !== 'setup') {
      next({ name: 'setup' })
    } else if (!setupRequired && to.name === 'setup') {
      next({ name: 'login' })
    } else if (requiresAuth && !isAuthenticated) {
      next({ name: 'login' })
    } else if (to.name === 'login' && isAuthenticated) {
      // If there's a redirect query parameter, use that instead of dashboard
      const redirect = to.query.redirect as string
      if (redirect) {
        next(decodeURIComponent(redirect))
      } else {
        next({ name: 'dashboard' })
      }
    } else {
      next()
    }
  } catch (error) {
    console.error('Failed to check setup status:', error)
    next()
  }
})

export default router
