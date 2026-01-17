import api from './api';
import {
  SimulationRun,
  CreateSimulationRequest,
  SimulationListParams,
  SimulationResponseParams,
  LLMResponse,
  PaginatedResponse,
} from '@/types';

export const simulationService = {
  async createSimulation(
    websiteId: string,
    config: CreateSimulationRequest
  ): Promise<SimulationRun> {
    const response = await api.post<SimulationRun>(
      `/websites/${websiteId}/simulations`,
      config
    );
    return response.data;
  },

  async getSimulations(
    websiteId: string,
    params?: SimulationListParams
  ): Promise<PaginatedResponse<SimulationRun>> {
    const response = await api.get<PaginatedResponse<SimulationRun>>(
      `/websites/${websiteId}/simulations`,
      { params }
    );
    return response.data;
  },

  async getSimulation(websiteId: string, simulationId: string): Promise<SimulationRun> {
    const response = await api.get<SimulationRun>(
      `/websites/${websiteId}/simulations/${simulationId}`
    );
    return response.data;
  },

  async getSimulationResponses(
    websiteId: string,
    simulationId: string,
    params?: SimulationResponseParams
  ): Promise<PaginatedResponse<LLMResponse>> {
    const response = await api.get<PaginatedResponse<LLMResponse>>(
      `/websites/${websiteId}/simulations/${simulationId}/responses`,
      { params }
    );
    return response.data;
  },
};
