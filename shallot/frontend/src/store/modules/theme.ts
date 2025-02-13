/*
 * Copyright Security Onion Solutions LLC and/or licensed to Security Onion Solutions LLC under one
 * or more contributor license agreements. Licensed under the Elastic License 2.0 as shown at
 * https://securityonion.net/license; you may not use this file except in compliance with the
 * Elastic License 2.0.
 */

import { Module, MutationTree, ActionTree, GetterTree } from 'vuex'
import { RootState } from '..'

export interface ThemeState {
  isDark: boolean
}

const state = () => ({
  isDark: localStorage.getItem('theme') !== 'light'
})

const mutations: MutationTree<ThemeState> = {
  SET_DARK_MODE(state: ThemeState, isDark: boolean) {
    state.isDark = isDark
    localStorage.setItem('theme', isDark ? 'dark' : 'light')
  }
}

const actions: ActionTree<ThemeState, RootState> = {
  toggleTheme({ commit, state }: { commit: any; state: ThemeState }) {
    commit('SET_DARK_MODE', !state.isDark)
  }
}

const getters: GetterTree<ThemeState, RootState> = {
  isDark: (state: ThemeState) => state.isDark
}

const theme: Module<ThemeState, RootState> = {
  namespaced: true,
  state,
  mutations,
  actions,
  getters
}

export default theme
