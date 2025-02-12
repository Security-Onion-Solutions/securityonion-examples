import { store } from '../index'
import { jwtDecode } from 'jwt-decode'

const API_BASE_URL = '/api'

interface JwtPayload {
  exp: number
  sub: string
  is_superuser: boolean
}

// Refresh token 1 minute before expiry
const REFRESH_THRESHOLD = 60 * 1000 // 1 minute in milliseconds

async function refreshTokenIfNeeded(): Promise<void> {
  const token = store.getters['auth/token']
  if (!token) return

  try {
    const decoded = jwtDecode<JwtPayload>(token)
    const expiryTime = decoded.exp * 1000 // Convert to milliseconds
    const currentTime = Date.now()
    
    // If token will expire in less than threshold
    if (expiryTime - currentTime < REFRESH_THRESHOLD) {
      try {
        const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          credentials: 'include'
        })
        
        if (response.ok) {
          const data = await response.json()
          await store.commit('auth/SET_TOKEN', data.access_token)
        } else {
          // If refresh fails, clear the token
          await store.commit('auth/SET_TOKEN', null)
          throw new Error('Token refresh failed')
        }
      } catch (error) {
        // If refresh fails, clear the token
        await store.commit('auth/SET_TOKEN', null)
        throw error
      }
    }
  } catch (error) {
    console.error('Error refreshing token:', error)
  }
}

interface RequestOptions extends RequestInit {
  requiresAuth?: boolean
}

export async function apiRequest(
  endpoint: string,
  options: RequestOptions = {}
): Promise<any> {
  const { requiresAuth = true, ...fetchOptions } = options
  const url = `${API_BASE_URL}${endpoint}`
  console.log('Making API request to:', url)
  console.log('Request options:', { requiresAuth, ...fetchOptions })

  // Add headers
  const headers = new Headers(fetchOptions.headers)
  
  // Add Authorization header if token exists and request requires auth
  if (requiresAuth) {
    const token = store.getters['auth/token']
    if (token) {
      // Refresh token if needed before making request
      await refreshTokenIfNeeded()
      // Get potentially new token after refresh
      const currentToken = store.getters['auth/token']
      headers.set('Authorization', `Bearer ${currentToken}`)
    }
  }

  // Add default content type if not set
  if (!headers.has('Content-Type') && !(fetchOptions.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }

  try {
    console.log('Request headers:', Object.fromEntries(headers.entries()))
    const response = await fetch(url, {
      ...fetchOptions,
      headers,
      credentials: 'include'
    })
    console.log('Response status:', response.status)
    console.log('Response headers:', Object.fromEntries(response.headers.entries()))

    if (!response.ok) {
      // Handle 401 Unauthorized
      if (response.status === 401) {
        // For settings requests, handle more gracefully
        if (endpoint.startsWith('/settings')) {
          const data = await response.json().catch(() => ({ detail: 'Unknown error' }))
          
          // If it's a specific settings error (e.g. not found), don't logout
          if (data.detail?.includes('Setting') || window.location.pathname === '/login') {
            throw new Error('Failed to load settings')
          }
        }
        
        // For real auth failures, logout and redirect
        await store.dispatch('auth/logout')
        const currentRoute = window.location.pathname
        if (currentRoute !== '/login') {
          window.location.href = `/login?redirect=${encodeURIComponent(currentRoute)}`
        }
        throw new Error('Session expired. Please login again.')
      }
      const data = await response.json().catch(() => ({ detail: response.statusText }))
      console.error('API error response:', data)
      throw new Error(data.detail || response.statusText)
    }

    // Only try to parse JSON if there's content
    const contentType = response.headers.get('content-type')
    if (contentType && contentType.includes('application/json')) {
      const data = await response.json()
      console.log('API response data:', data)
      return data
    }

    return response
  } catch (error) {
    console.error('API request failed:', error)
    throw error
  }
}
