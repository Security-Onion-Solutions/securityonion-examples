import { store } from '../store'

const API_BASE_URL = '/api'

interface RequestOptions extends RequestInit {
  requiresAuth?: boolean
}

export async function apiRequest(
  endpoint: string,
  options: RequestOptions = {}
): Promise<any> {
  const { requiresAuth = true, ...fetchOptions } = options
  const url = `${API_BASE_URL}${endpoint}`

  // Add headers
  const headers = new Headers(fetchOptions.headers)
  
  // Add Authorization header if token exists and request requires auth
  if (requiresAuth) {
    const token = store.getters['auth/token']
    if (token) {
      headers.set('Authorization', `Bearer ${token}`)
    }
  }

  // Add default content type if not set
  if (!headers.has('Content-Type') && !(fetchOptions.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(url, {
    ...fetchOptions,
    headers
  })

  if (!response.ok) {
    // Handle 401 Unauthorized
    if (response.status === 401) {
      store.dispatch('auth/logout')
      throw new Error('Session expired. Please login again.')
    }
    throw new Error(response.statusText)
  }

  // Only try to parse JSON if there's content
  const contentType = response.headers.get('content-type')
  if (contentType && contentType.includes('application/json')) {
    return response.json()
  }

  return response
}
