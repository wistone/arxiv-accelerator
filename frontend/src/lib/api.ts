const API_BASE_URL = process.env.NODE_ENV === 'development' 
  ? 'http://localhost:8080' 
  : '';

export class ApiClient {
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error || `HTTP ${response.status}`);
    }

    return response.json();
  }

  async searchArticles(date: string, category: string) {
    return this.request('/api/search_articles', {
      method: 'POST',
      body: JSON.stringify({ date, category }),
    });
  }

  async checkAnalysisExists(date: string, category: string) {
    return this.request('/api/check_analysis_exists', {
      method: 'POST',
      body: JSON.stringify({ date, category }),
    });
  }

  async analyzeArticles(date: string, category: string, testCount?: string) {
    return this.request('/api/analyze_papers', {
      method: 'POST',
      body: JSON.stringify({ 
        date, 
        category, 
        test_count: testCount || '' 
      }),
    });
  }

  async getAnalysisResults(date: string, category: string, testCount?: string) {
    return this.request('/api/get_analysis_results', {
      method: 'POST',
      body: JSON.stringify({ 
        date, 
        category, 
        test_count: testCount || '' 
      }),
    });
  }

  async getAvailableDates() {
    return this.request('/api/available_dates');
  }

  createSSEConnection(url: string): EventSource {
    return new EventSource(`${API_BASE_URL}${url}`);
  }
}

export const apiClient = new ApiClient();