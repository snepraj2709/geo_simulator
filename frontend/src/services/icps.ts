import api from './api';
import {
  ICP,
  ConversationSequence,
  ConversationParams,
  PromptClassification,
  ClassificationParams,
  PaginatedResponse,
} from '@/types';

export const icpService = {
  async getICPs(websiteId: string): Promise<{ data: ICP[] }> {
    const response = await api.get<{ data: ICP[] }>(`/websites/${websiteId}/icps`);
    return response.data;
  },

  async getICP(websiteId: string, icpId: string): Promise<ICP> {
    const response = await api.get<ICP>(`/websites/${websiteId}/icps/${icpId}`);
    return response.data;
  },

  async updateICP(
    websiteId: string,
    icpId: string,
    data: Partial<ICP>
  ): Promise<ICP> {
    const response = await api.put<ICP>(`/websites/${websiteId}/icps/${icpId}`, data);
    return response.data;
  },

  async regenerateICPs(websiteId: string): Promise<{ job_id: string; status: string }> {
    const response = await api.post<{ job_id: string; status: string }>(
      `/websites/${websiteId}/icps/regenerate`
    );
    return response.data;
  },

  async getConversations(
    websiteId: string,
    params?: ConversationParams
  ): Promise<PaginatedResponse<ConversationSequence>> {
    const response = await api.get<PaginatedResponse<ConversationSequence>>(
      `/websites/${websiteId}/conversations`,
      { params }
    );
    return response.data;
  },

  async getConversation(
    websiteId: string,
    conversationId: string
  ): Promise<ConversationSequence> {
    const response = await api.get<ConversationSequence>(
      `/websites/${websiteId}/conversations/${conversationId}`
    );
    return response.data;
  },

  async getClassifications(
    websiteId: string,
    params?: ClassificationParams
  ): Promise<PaginatedResponse<PromptClassification> & { summary: any }> {
    const response = await api.get(
      `/websites/${websiteId}/classifications`,
      { params }
    );
    return response.data;
  },
};
