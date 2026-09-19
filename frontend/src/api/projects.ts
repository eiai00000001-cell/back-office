import { apiClient } from './client'
import type { Project, ProjectDetail, ProjectListItem, ProjectStatus } from '../types'

export interface ProjectPayload {
  name: string
  client_id: number | null
  status: ProjectStatus
  due_date: string | null
  description: string | null
}

export interface ProjectListFilters {
  status?: ProjectStatus
  client_id?: number
}

export const projectsApi = {
  list: async (filters: ProjectListFilters = {}): Promise<ProjectListItem[]> =>
    (await apiClient.get('/projects', { params: filters })).data,
  get: async (id: number): Promise<ProjectDetail> => (await apiClient.get(`/projects/${id}`)).data,
  create: async (payload: ProjectPayload): Promise<Project> => (await apiClient.post('/projects', payload)).data,
  update: async (id: number, payload: ProjectPayload): Promise<Project> =>
    (await apiClient.put(`/projects/${id}`, payload)).data,
  changeStatus: async (id: number, status: ProjectStatus): Promise<Project> =>
    (await apiClient.patch(`/projects/${id}/status`, { status })).data,
  remove: async (id: number): Promise<void> => {
    await apiClient.delete(`/projects/${id}`)
  },
}
