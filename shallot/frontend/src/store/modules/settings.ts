/*
 * Copyright Security Onion Solutions LLC and/or licensed to Security Onion Solutions LLC under one
 * or more contributor license agreements. Licensed under the Elastic License 2.0 as shown at
 * https://securityonion.net/license; you may not use this file except in compliance with the
 * Elastic License 2.0.
 */

import { Module } from 'vuex'
import { RootState } from '..'
import { apiRequest } from '../utils/api'

export interface Setting {
  key: string
  value: string
  description?: string
  updated_at: number
}

export interface SettingsState {
  settings: Setting[]
  loading: boolean
  error: string | null
}

const settings: Module<SettingsState, RootState> = {
  namespaced: true,
  
  state: () => ({
    settings: [],
    loading: false,
    error: null
  }),
  
  mutations: {
    SET_SETTINGS(state, settings: Setting[]) {
      state.settings = settings
    },
    
    SET_SETTING(state, setting: Setting) {
      const index = state.settings.findIndex(s => s.key === setting.key)
      if (index !== -1) {
        state.settings[index] = setting
      } else {
        state.settings.push(setting)
      }
    },
    
    DELETE_SETTING(state, key: string) {
      state.settings = state.settings.filter(s => s.key !== key)
    },
    
    SET_LOADING(state, loading: boolean) {
      state.loading = loading
    },
    
    SET_ERROR(state, error: string | null) {
      state.error = error
    }
  },
  
  actions: {
    async fetchSettings({ commit }) {
      commit('SET_LOADING', true)
      commit('SET_ERROR', null)
      try {
        const settings = await apiRequest('/settings/authenticated')
        commit('SET_SETTINGS', settings)
        return settings // Return the settings array for direct use
      } catch (error) {
        commit('SET_ERROR', error instanceof Error ? error.message : 'Failed to fetch settings')
        return [] // Return empty array on error to prevent undefined
      } finally {
        commit('SET_LOADING', false)
      }
    },
    
    async getSetting({ commit }, key: string) {
      commit('SET_LOADING', true)
      commit('SET_ERROR', null)
      try {
        const setting = await apiRequest(`/settings/${key}`)
        commit('SET_SETTING', setting)
        return setting
      } catch (error) {
        commit('SET_ERROR', error instanceof Error ? error.message : 'Failed to get setting')
        throw error
      } finally {
        commit('SET_LOADING', false)
      }
    },
    
    async createSetting({ commit }, { key, value, description }: { key: string, value: string, description?: string }) {
      commit('SET_LOADING', true)
      commit('SET_ERROR', null)
      try {
        const setting = await apiRequest('/settings', {
          method: 'POST',
          body: JSON.stringify({ key, value, description })
        })
        commit('SET_SETTING', setting)
        return setting
      } catch (error) {
        commit('SET_ERROR', error instanceof Error ? error.message : 'Failed to create setting')
        throw error
      } finally {
        commit('SET_LOADING', false)
      }
    },
    
    async updateSetting({ commit }, { key, value, description }: { key: string, value: string, description?: string }) {
      commit('SET_LOADING', true)
      commit('SET_ERROR', null)
      try {
        const setting = await apiRequest(`/settings/${key}`, {
          method: 'PUT',
          body: JSON.stringify({ value, description })
        })
        commit('SET_SETTING', setting)
        return setting
      } catch (error) {
        commit('SET_ERROR', error instanceof Error ? error.message : 'Failed to update setting')
        throw error
      } finally {
        commit('SET_LOADING', false)
      }
    },
    
    async deleteSetting({ commit }, key: string) {
      commit('SET_LOADING', true)
      commit('SET_ERROR', null)
      try {
        await apiRequest(`/settings/${key}`, {
          method: 'DELETE'
        })
        commit('DELETE_SETTING', key)
      } catch (error) {
        commit('SET_ERROR', error instanceof Error ? error.message : 'Failed to delete setting')
        throw error
      } finally {
        commit('SET_LOADING', false)
      }
    },

    async testSecurityOnionConnection({ commit }) {
      commit('SET_LOADING', true)
      commit('SET_ERROR', null)
      try {
        const result = await apiRequest('/settings/security-onion/test-connection', {
          method: 'POST'
        })
        if (!result.success) {
          commit('SET_ERROR', result.status?.error || 'Connection test failed')
        }
        return result
      } catch (error) {
        commit('SET_ERROR', error instanceof Error ? error.message : 'Failed to test connection')
        throw error
      } finally {
        commit('SET_LOADING', false)
      }
    },

    async getSecurityOnionStatus({ commit }) {
      commit('SET_LOADING', true)
      commit('SET_ERROR', null)
      try {
        return await apiRequest('/settings/security-onion/status')
      } catch (error) {
        commit('SET_ERROR', error instanceof Error ? error.message : 'Failed to get status')
        throw error
      } finally {
        commit('SET_LOADING', false)
      }
    },

    async getDiscordStatus({ commit }) {
      commit('SET_LOADING', true)
      commit('SET_ERROR', null)
      try {
        const data = await apiRequest('/health', { requiresAuth: false })
        console.log('Health endpoint response:', data)
        console.log('Discord status from response:', data.DISCORD)
        const status = {
          connected: data.DISCORD?.connected || false,
          error: data.DISCORD?.status.startsWith('error') ? data.DISCORD.status : null
        }
        console.log('Returning status:', status)
        return status
      } catch (error) {
        console.error('Error getting Discord status:', error)
        commit('SET_ERROR', error instanceof Error ? error.message : 'Failed to get Discord status')
        throw error
      } finally {
        commit('SET_LOADING', false)
      }
    },

    async getSlackStatus({ commit }) {
      commit('SET_LOADING', true)
      commit('SET_ERROR', null)
      try {
        const data = await apiRequest('/health', { requiresAuth: false })
        console.log('Health endpoint response:', data)
        console.log('Slack status from response:', data.SLACK)
        const status = {
          webClientConnected: data.SLACK?.web_client_connected || false,
          socketModeConnected: data.SLACK?.socket_mode_connected || false,
          error: data.SLACK?.status.startsWith('error') ? data.SLACK.status : null
        }
        console.log('Returning Slack status:', status)
        return status
      } catch (error) {
        console.error('Error getting Slack status:', error)
        commit('SET_ERROR', error instanceof Error ? error.message : 'Failed to get Slack status')
        throw error
      } finally {
        commit('SET_LOADING', false)
      }
    },

    async getMatrixStatus({ commit }) {
      commit('SET_LOADING', true)
      commit('SET_ERROR', null)
      try {
        const data = await apiRequest('/health', { requiresAuth: false })
        console.log('Health endpoint response:', data)
        console.log('Matrix status from response:', data.MATRIX)
        const status = {
          connected: data.MATRIX?.connected || false,
          e2eEnabled: data.MATRIX?.e2e_enabled || false,
          error: data.MATRIX?.status.startsWith('error') ? data.MATRIX.status : null
        }
        console.log('Returning Matrix status:', status)
        return status
      } catch (error) {
        console.error('Error getting Matrix status:', error)
        commit('SET_ERROR', error instanceof Error ? error.message : 'Failed to get Matrix status')
        throw error
      } finally {
        commit('SET_LOADING', false)
      }
    }
  },
  
  getters: {
    getSettingByKey: (state) => (key: string) => {
      return state.settings.find(s => s.key === key)
    },
    allSettings: (state) => state.settings,
    isLoading: (state) => state.loading,
    error: (state) => state.error
  }
}

export default settings
