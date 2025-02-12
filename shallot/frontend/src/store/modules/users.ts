/*
 * Copyright Security Onion Solutions LLC and/or licensed to Security Onion Solutions LLC under one
 * or more contributor license agreements. Licensed under the Elastic License 2.0 as shown at
 * https://securityonion.net/license; you may not use this file except in compliance with the
 * Elastic License 2.0.
 */

import { Module } from 'vuex'
import { RootState } from '..'
import { apiRequest } from '../utils/api'
import { ChatService } from '../../types/chat'

export interface User {
  id: number
  username: string
  display_name?: string
  is_active: boolean
  is_superuser: boolean
  created_at: string
  user_type: 'web' | 'chat'
  role?: string
  service?: ChatService
}

export interface UsersState {
  users: User[]
  loading: boolean
  error: string | null
}

const users: Module<UsersState, RootState> = {
  namespaced: true,

  state: () => ({
    users: [],
    loading: false,
    error: null
  }),

  mutations: {
    setUsers(state, users: User[]) {
      state.users = users
    },
    setLoading(state, loading: boolean) {
      state.loading = loading
    },
    setError(state, error: string | null) {
      state.error = error
    },
    addUser(state, user: User) {
      state.users.push(user)
    },
    updateUser(state, updatedUser: User) {
      const index = state.users.findIndex(u => u.id === updatedUser.id)
      if (index !== -1) {
        state.users[index] = updatedUser
      }
    }
  },

  actions: {
    async fetchUsers({ commit }, { userType }: { userType: 'web' | 'chat' }) {
      commit('setLoading', true)
      commit('setError', null)
      try {
        let response
        if (userType === 'chat') {
          response = await apiRequest('/chat-users/')
        } else {
          response = await apiRequest('/users/')
        }
        commit('setUsers', response)
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Failed to fetch users'
        commit('setError', errorMessage)
        console.error('Error fetching users:', error)
      } finally {
        commit('setLoading', false)
      }
    },

    async createUser({ commit }, { username, password, is_superuser, user_type }: { username: string; password: string; is_superuser: boolean; user_type: 'web' | 'chat' }) {
      commit('setError', null)
      try {
        const response = await apiRequest('/users/', {
          method: 'POST',
          body: JSON.stringify({
            username,
            password,
            is_superuser,
            user_type
          })
        })
        commit('addUser', response)
        return response
      } catch (error) {
        commit('setError', 'Failed to create user')
        console.error('Error creating user:', error)
        throw error
      }
    },

    async updateUser({ commit }, { id, data, userType }: { id: number; data: { username?: string; password?: string; is_active?: boolean; is_superuser?: boolean; role?: string; user_type: 'web' | 'chat' }; userType: 'web' | 'chat' }) {
      commit('setError', null)
      try {
        let response
        if (userType === 'chat') {
          // For chat users, we only update role
          response = await apiRequest(`/chat-users/${id}/role`, {
            method: 'PUT',
            body: JSON.stringify({ role: data.role })
          })
        } else {
          response = await apiRequest(`/users/${id}/`, {
            method: 'PUT',
            body: JSON.stringify(data)
          })
        }
        commit('updateUser', response)
        return response
      } catch (error) {
        commit('setError', 'Failed to update user')
        console.error('Error updating user:', error)
        throw error
      }
    },

    async deleteUser({ commit, state }, { id, userType }: { id: number; userType: 'web' | 'chat' }) {
      commit('setError', null)
      try {
        if (userType === 'chat') {
          await apiRequest(`/chat-users/${id}`, {
            method: 'DELETE'
          })
          commit('setUsers', state.users.filter((u: User) => u.id !== id))
        } else {
          throw new Error('Deletion of web users not supported')
        }
      } catch (error) {
        commit('setError', 'Failed to delete user')
        console.error('Error deleting user:', error)
        throw error
      }
    }
  },

  getters: {
    getUsers: (state) => state.users,
    isLoading: (state) => state.loading,
    getError: (state) => state.error
  }
}

export default users
