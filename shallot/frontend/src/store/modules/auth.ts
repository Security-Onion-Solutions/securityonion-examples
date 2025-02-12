/*
 * Copyright Security Onion Solutions LLC and/or licensed to Security Onion Solutions LLC under one
 * or more contributor license agreements. Licensed under the Elastic License 2.0 as shown at
 * https://securityonion.net/license; you may not use this file except in compliance with the
 * Elastic License 2.0.
 */

import { Module } from 'vuex'
import { RootState } from '../index'
import { apiRequest } from '../utils/api'

interface AuthState {
  token: string | null
  user: {
    username: string
    is_superuser: boolean
  } | null
  isAuthenticated: boolean
}

export const auth: Module<AuthState, RootState> = {
  namespaced: true,

  state: () => {
    // Load state from localStorage if available
    const token = localStorage.getItem('token')
    const userStr = localStorage.getItem('user')
    const user = userStr ? JSON.parse(userStr) : null

    return {
      token,
      user,
      isAuthenticated: !!token
    }
  },

  getters: {
    isAuthenticated: (state) => state.isAuthenticated,
    currentUser: (state) => state.user,
    token: (state) => state.token
  },

  mutations: {
    SET_TOKEN(state, token: string | null) {
      state.token = token
      state.isAuthenticated = !!token
      if (token) {
        localStorage.setItem('token', token)
      } else {
        localStorage.removeItem('token')
      }
    },
    SET_USER(state, user: { username: string; is_superuser: boolean } | null) {
      state.user = user
      if (user) {
        localStorage.setItem('user', JSON.stringify(user))
      } else {
        localStorage.removeItem('user')
      }
    },
    CLEAR_AUTH(state) {
      state.token = null
      state.user = null
      state.isAuthenticated = false
      localStorage.removeItem('token')
      localStorage.removeItem('user')
    }
  },

  actions: {
    async checkSetupRequired() {
      try {
        const data = await apiRequest('/auth/setup-required', { requiresAuth: false })
        return data.setup_required
      } catch (error) {
        throw new Error('Failed to check setup status')
      }
    },

    async setup({ commit }, credentials: { username: string; password: string }) {
      try {
        const data = await apiRequest('/auth/first-user', {
          method: 'POST',
          body: JSON.stringify(credentials),
          requiresAuth: false
        })
        commit('SET_TOKEN', data.access_token)
        commit('SET_USER', {
          username: credentials.username,
          is_superuser: true
        })

        return data
      } catch (error) {
        commit('CLEAR_AUTH')
        throw error
      }
    },

    async login({ commit }, credentials: { username: string; password: string }) {
      try {
        const formData = new FormData()
        formData.append('username', credentials.username)
        formData.append('password', credentials.password)
        
        const data = await apiRequest('/auth/token', {
          method: 'POST',
          body: formData,
          requiresAuth: false
        })
        commit('SET_TOKEN', data.access_token)
        // Try to decode the JWT to get user info
        const [, payload] = data.access_token.split('.')
        const decodedPayload = JSON.parse(atob(payload))
        
        commit('SET_USER', {
          username: decodedPayload.sub,
          is_superuser: decodedPayload.is_superuser || false
        })

        return data
      } catch (error) {
        commit('CLEAR_AUTH')
        throw error
      }
    },

    logout({ commit, dispatch }) {
      commit('CLEAR_AUTH')
      // Reset other store modules
      commit('settings/SET_SETTINGS', [], { root: true })
    }
  }
}
