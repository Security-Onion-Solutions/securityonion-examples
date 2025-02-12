/*
 * Copyright Security Onion Solutions LLC and/or licensed to Security Onion Solutions LLC under one
 * or more contributor license agreements. Licensed under the Elastic License 2.0 as shown at
 * https://securityonion.net/license; you may not use this file except in compliance with the
 * Elastic License 2.0.
 */

import { Module } from 'vuex'
import { RootState } from '..'

export interface ThemeState {
  isDark: boolean
}

const theme: Module<ThemeState, RootState> = {
  namespaced: true,
  
  state: () => ({
    isDark: localStorage.getItem('theme') === 'dark'
  }),
  
  mutations: {
    SET_DARK_MODE(state, isDark: boolean) {
      state.isDark = isDark
      localStorage.setItem('theme', isDark ? 'dark' : 'light')
    }
  },
  
  actions: {
    toggleTheme({ commit, state }) {
      commit('SET_DARK_MODE', !state.isDark)
    }
  },
  
  getters: {
    isDark: (state) => state.isDark
  }
}

export default theme
