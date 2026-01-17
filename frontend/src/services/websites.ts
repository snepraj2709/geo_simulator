import api from './api';
import {
  Website,
  PaginatedResponse,
  WebsiteListParams,
  ScrapedPage,
  ScrapedPageParams,
  ScrapeRequest,
  ScrapeJob,
} from '@/types';

export const websiteService = {
  async getWebsites(params?: WebsiteListParams): Promise<PaginatedResponse<Website>> {
    const response = await api.get<PaginatedResponse<Website>>('/websites', { params });
    return response.data;
  },

  async getWebsite(id: string): Promise<Website> {
    const response = await api.get<Website>(`/websites/${id}`);
    return response.data;
  },

  async createWebsite(data: {
    url: string;
    name: string;
    scrape_depth?: number;
  }): Promise<Website> {
    const response = await api.post<Website>('/websites', data);
    return response.data;
  },

  async triggerScrape(id: string, scrapeRequest: ScrapeRequest): Promise<ScrapeJob> {
    const response = await api.post<ScrapeJob>(`/websites/${id}/scrape`, scrapeRequest);
    return response.data;
  },

  async deleteWebsite(id: string): Promise<void> {
    await api.delete(`/websites/${id}`);
  },

  async getScrapedPages(
    websiteId: string,
    params?: ScrapedPageParams
  ): Promise<PaginatedResponse<ScrapedPage>> {
    const response = await api.get<PaginatedResponse<ScrapedPage>>(
      `/websites/${websiteId}/pages`,
      { params }
    );
    return response.data;
  },

  async getScrapedPage(websiteId: string, pageId: string): Promise<ScrapedPage> {
    const response = await api.get<ScrapedPage>(`/websites/${websiteId}/pages/${pageId}`);
    return response.data;
  },
};
