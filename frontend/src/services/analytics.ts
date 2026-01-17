import api from './api';
import {
  Brand,
  BrandAnalysis,
  ShareOfVoice,
  BrandListParams,
  PaginatedResponse,
} from '@/types';

export const analyticsService = {
  async getBrands(
    websiteId: string,
    params?: BrandListParams
  ): Promise<PaginatedResponse<Brand>> {
    const response = await api.get<PaginatedResponse<Brand>>(
      `/websites/${websiteId}/brands`,
      { params }
    );
    return response.data;
  },

  async trackBrand(websiteId: string, brandId: string): Promise<Brand> {
    const response = await api.post<Brand>(`/websites/${websiteId}/brands/track`, {
      brand_id: brandId,
    });
    return response.data;
  },

  async getBrandAnalysis(websiteId: string, brandId: string): Promise<BrandAnalysis> {
    const response = await api.get<BrandAnalysis>(
      `/websites/${websiteId}/brands/${brandId}/analysis`
    );
    return response.data;
  },

  async getShareOfVoice(
    websiteId: string,
    params?: { period_start?: string; period_end?: string }
  ): Promise<{ data: ShareOfVoice[] }> {
    const response = await api.get<{ data: ShareOfVoice[] }>(
      `/websites/${websiteId}/share-of-voice`,
      { params }
    );
    return response.data;
  },

  async getCompetitorAnalysis(
    websiteId: string
  ): Promise<{
    competitors: Array<{ brand: Brand; relationship_type: string }>;
    substitution_patterns: Array<{
      missing_brand: string;
      substitute_brand: string;
      occurrence_count: number;
    }>;
  }> {
    const response = await api.get(`/websites/${websiteId}/competitors`);
    return response.data;
  },
};
