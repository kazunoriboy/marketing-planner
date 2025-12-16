/**
 * API クライアント
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface SystemAdminResponse {
  id: number;
  email: string;
  name: string;
  is_active: boolean;
}

export interface FacilityAdminResponse {
  id: number;
  email: string;
  name: string;
  is_active: boolean;
  hotels?: HotelInfo[];
}

export interface HotelInfo {
  id: number;
  name: string;
  address?: string;
  role: string;
}

export interface HotelResponse {
  id: number;
  name: string;
  address: string;
  postal_code?: string;
  phone?: string;
  email?: string;
  website?: string;
  features: Record<string, unknown>;
  strengths: Record<string, unknown>;
  role: string;
}

export interface HotelCreateRequest {
  name: string;
  address: string;
  postal_code?: string;
  phone?: string;
  email?: string;
  website?: string;
  features?: Record<string, unknown>;
  strengths?: Record<string, unknown>;
}

export interface FacilityAdminCreateRequest {
  email: string;
  name: string;
  password: string;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string
  ) {
    super(detail);
    this.name = "ApiError";
  }
}

/**
 * 認証トークンを取得
 */
function getAuthToken(userType: "admin" | "facility"): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(`${userType}_access_token`);
}

/**
 * リフレッシュトークンを取得
 */
function getRefreshToken(userType: "admin" | "facility"): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(`${userType}_refresh_token`);
}

/**
 * トークンを保存
 */
export function saveTokens(
  userType: "admin" | "facility",
  tokens: TokenResponse
): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(`${userType}_access_token`, tokens.access_token);
  localStorage.setItem(`${userType}_refresh_token`, tokens.refresh_token);
}

/**
 * トークンを削除
 */
export function clearTokens(userType: "admin" | "facility"): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(`${userType}_access_token`);
  localStorage.removeItem(`${userType}_refresh_token`);
}

/**
 * APIリクエストを実行
 */
async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {},
  userType?: "admin" | "facility"
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((options.headers as Record<string, string>) || {}),
  };

  // 認証トークンを追加
  if (userType) {
    const token = getAuthToken(userType);
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    // 401エラーの場合はリフレッシュを試みる
    if (response.status === 401 && userType) {
      const refreshed = await refreshTokens(userType);
      if (refreshed) {
        // リトライ
        const newToken = getAuthToken(userType);
        headers["Authorization"] = `Bearer ${newToken}`;
        const retryResponse = await fetch(`${API_BASE_URL}${endpoint}`, {
          ...options,
          headers,
        });
        if (retryResponse.ok) {
          return retryResponse.json();
        }
      }
      // リフレッシュ失敗時はトークンをクリア
      clearTokens(userType);
    }

    const errorData = await response.json().catch(() => ({}));
    throw new ApiError(
      response.status,
      errorData.detail || "APIエラーが発生しました"
    );
  }

  // 204 No Content の場合
  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

/**
 * トークンをリフレッシュ
 */
async function refreshTokens(userType: "admin" | "facility"): Promise<boolean> {
  const refreshToken = getRefreshToken(userType);
  if (!refreshToken) return false;

  try {
    const endpoint =
      userType === "admin" ? "/admin/auth/refresh" : "/facility/auth/refresh";
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) return false;

    const tokens: TokenResponse = await response.json();
    saveTokens(userType, tokens);
    return true;
  } catch {
    return false;
  }
}

// ============================================
// システムアドミン API
// ============================================

export const adminApi = {
  /**
   * ログイン
   */
  async login(request: LoginRequest): Promise<TokenResponse> {
    const tokens = await apiRequest<TokenResponse>("/admin/auth/login", {
      method: "POST",
      body: JSON.stringify(request),
    });
    saveTokens("admin", tokens);
    return tokens;
  },

  /**
   * ログアウト
   */
  logout(): void {
    clearTokens("admin");
  },

  /**
   * 現在のユーザー情報を取得
   */
  async me(): Promise<SystemAdminResponse> {
    return apiRequest<SystemAdminResponse>("/admin/auth/me", {}, "admin");
  },

  /**
   * 施設管理者一覧を取得
   */
  async listUsers(
    skip = 0,
    limit = 100
  ): Promise<(FacilityAdminResponse & { hotel_count: number })[]> {
    return apiRequest<(FacilityAdminResponse & { hotel_count: number })[]>(
      `/admin/users?skip=${skip}&limit=${limit}`,
      {},
      "admin"
    );
  },

  /**
   * 施設管理者を作成
   */
  async createUser(
    request: FacilityAdminCreateRequest
  ): Promise<FacilityAdminResponse> {
    return apiRequest<FacilityAdminResponse>(
      "/admin/users",
      {
        method: "POST",
        body: JSON.stringify(request),
      },
      "admin"
    );
  },

  /**
   * 施設管理者詳細を取得
   */
  async getUser(
    userId: number
  ): Promise<FacilityAdminResponse & { hotels: HotelInfo[] }> {
    return apiRequest<FacilityAdminResponse & { hotels: HotelInfo[] }>(
      `/admin/users/${userId}`,
      {},
      "admin"
    );
  },

  /**
   * 施設管理者を更新
   */
  async updateUser(
    userId: number,
    data: { name?: string; is_active?: boolean }
  ): Promise<FacilityAdminResponse> {
    return apiRequest<FacilityAdminResponse>(
      `/admin/users/${userId}`,
      {
        method: "PUT",
        body: JSON.stringify(data),
      },
      "admin"
    );
  },

  /**
   * 施設管理者を削除
   */
  async deleteUser(userId: number): Promise<void> {
    await apiRequest<void>(
      `/admin/users/${userId}`,
      {
        method: "DELETE",
      },
      "admin"
    );
  },

  /**
   * 施設管理者に施設を紐付け
   */
  async assignHotel(
    userId: number,
    hotelId: number,
    role: "owner" | "editor" | "viewer" = "viewer"
  ): Promise<{ message: string; role: string }> {
    return apiRequest<{ message: string; role: string }>(
      `/admin/users/${userId}/hotels/${hotelId}?role=${role}`,
      {
        method: "POST",
      },
      "admin"
    );
  },

  /**
   * 施設管理者から施設の紐付けを解除
   */
  async removeHotel(userId: number, hotelId: number): Promise<void> {
    await apiRequest<void>(
      `/admin/users/${userId}/hotels/${hotelId}`,
      {
        method: "DELETE",
      },
      "admin"
    );
  },
};

// ============================================
// 施設管理者 API
// ============================================

export const facilityApi = {
  /**
   * ログイン
   */
  async login(request: LoginRequest): Promise<TokenResponse> {
    const tokens = await apiRequest<TokenResponse>("/facility/auth/login", {
      method: "POST",
      body: JSON.stringify(request),
    });
    saveTokens("facility", tokens);
    return tokens;
  },

  /**
   * ログアウト
   */
  logout(): void {
    clearTokens("facility");
  },

  /**
   * 現在のユーザー情報を取得
   */
  async me(): Promise<FacilityAdminResponse> {
    return apiRequest<FacilityAdminResponse>("/facility/auth/me", {}, "facility");
  },

  /**
   * パスワード変更
   */
  async changePassword(
    currentPassword: string,
    newPassword: string
  ): Promise<{ message: string }> {
    return apiRequest<{ message: string }>(
      "/facility/auth/password",
      {
        method: "PUT",
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      },
      "facility"
    );
  },

  /**
   * 施設一覧を取得
   */
  async listHotels(): Promise<HotelResponse[]> {
    return apiRequest<HotelResponse[]>("/facility/hotels", {}, "facility");
  },

  /**
   * 施設を作成
   */
  async createHotel(request: HotelCreateRequest): Promise<HotelResponse> {
    return apiRequest<HotelResponse>(
      "/facility/hotels",
      {
        method: "POST",
        body: JSON.stringify(request),
      },
      "facility"
    );
  },

  /**
   * 施設詳細を取得
   */
  async getHotel(hotelId: number): Promise<HotelResponse> {
    return apiRequest<HotelResponse>(
      `/facility/hotels/${hotelId}`,
      {},
      "facility"
    );
  },

  /**
   * 施設を更新
   */
  async updateHotel(
    hotelId: number,
    data: Partial<HotelCreateRequest>
  ): Promise<HotelResponse> {
    return apiRequest<HotelResponse>(
      `/facility/hotels/${hotelId}`,
      {
        method: "PUT",
        body: JSON.stringify(data),
      },
      "facility"
    );
  },

  /**
   * 施設を削除
   */
  async deleteHotel(hotelId: number): Promise<void> {
    await apiRequest<void>(
      `/facility/hotels/${hotelId}`,
      {
        method: "DELETE",
      },
      "facility"
    );
  },
};

// ============================================
// マーケティングAI API（施設別・認証付き）
// ============================================

export interface AnalysisSession {
  session_id: number | null;
  hotel_id: number;
  csv_statistics: Record<string, unknown>;
  csv_insights: string | null;
  competitors_list: Record<string, unknown>;
  reviews_summary: Record<string, unknown>;
  regional_trends: string | null;
  created_at: string;
  updated_at: string;
}

export interface CSVAnalysisResponse {
  session_id: number;
  statistics: Record<string, unknown>;
  insights: string;
  created_at: string;
}

export interface MarketResearchResponse {
  session_id: number;
  competitors: Record<string, unknown>;
  reviews_summary: Record<string, unknown>;
  regional_trends: string;
  created_at: string;
}

export interface MarketingPlan {
  id: number;
  analysis_session_id: number;
  status: "draft" | "approved";
  plan_name: string;
  concept: string;
  target_audience: Record<string, unknown>;
  price_range: Record<string, unknown>;
  benefits: Record<string, unknown>;
  strategy_3c: Record<string, unknown>;
  strategy_pest: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface CreativeAsset {
  id: number;
  marketing_plan_id: number;
  lp_source_code: string | null;
  lp_preview_url: string | null;
  ad_image_urls: Record<string, unknown>;
  ad_copy: Record<string, unknown>;
  generation_prompts: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface CreativeGenerationRequest {
  plan_id: number;
  generate_lp?: boolean;
  generate_images?: boolean;
  generate_ad_copy?: boolean;
}

export const marketingApi = {
  // ============================================
  // 分析 API
  // ============================================
  
  /**
   * 分析セッションを取得
   */
  async getAnalysisSession(hotelId: number): Promise<AnalysisSession> {
    return apiRequest<AnalysisSession>(
      `/api/analysis/hotels/${hotelId}/session`,
      {},
      "facility"
    );
  },

  /**
   * 顧客データ（CSV）を分析
   */
  async analyzeCustomerCSV(hotelId: number, file: File): Promise<CSVAnalysisResponse> {
    const formData = new FormData();
    formData.append("file", file);

    const makeRequest = async (token: string | null) => {
      return fetch(
        `${API_BASE_URL}/api/analysis/hotels/${hotelId}/upload-csv`,
        {
          method: "POST",
          headers: token ? { Authorization: `Bearer ${token}` } : {},
          body: formData,
        }
      );
    };

    let token = localStorage.getItem("facility_access_token");
    let response = await makeRequest(token);

    // 401エラーの場合はトークンリフレッシュを試みる
    if (response.status === 401) {
      const refreshToken = localStorage.getItem("facility_refresh_token");
      if (refreshToken) {
        try {
          const refreshResponse = await fetch(`${API_BASE_URL}/facility/auth/refresh`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ refresh_token: refreshToken }),
          });

          if (refreshResponse.ok) {
            const tokens: TokenResponse = await refreshResponse.json();
            saveTokens("facility", tokens);
            // 新しいトークンでリトライ
            token = tokens.access_token;
            response = await makeRequest(token);
          } else {
            // リフレッシュ失敗時はトークンをクリア
            clearTokens("facility");
          }
        } catch {
          clearTokens("facility");
        }
      }
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ApiError(
        response.status,
        errorData.detail || "CSVアップロードに失敗しました"
      );
    }

    return response.json();
  },

  /**
   * 市場調査を実行
   */
  async analyzeMarket(hotelId: number, radiusKm: number = 10): Promise<MarketResearchResponse> {
    return apiRequest<MarketResearchResponse>(
      `/api/analysis/hotels/${hotelId}/market?radius_km=${radiusKm}`,
      {
        method: "POST",
      },
      "facility"
    );
  },

  // ============================================
  // プランニング API
  // ============================================

  /**
   * マーケティングプランを生成
   */
  async generatePlans(hotelId: number, numPlans: number = 3): Promise<MarketingPlan[]> {
    return apiRequest<MarketingPlan[]>(
      `/api/planning/hotels/${hotelId}/generate?num_plans=${numPlans}`,
      {
        method: "POST",
      },
      "facility"
    );
  },

  /**
   * 施設のプラン一覧を取得
   */
  async listPlans(hotelId: number): Promise<MarketingPlan[]> {
    return apiRequest<MarketingPlan[]>(
      `/api/planning/hotels/${hotelId}/plans`,
      {},
      "facility"
    );
  },

  /**
   * プラン詳細を取得
   */
  async getPlan(hotelId: number, planId: number): Promise<MarketingPlan> {
    return apiRequest<MarketingPlan>(
      `/api/planning/hotels/${hotelId}/plans/${planId}`,
      {},
      "facility"
    );
  },

  /**
   * プランのステータスを更新
   */
  async updatePlanStatus(
    hotelId: number,
    planId: number,
    status: "draft" | "approved"
  ): Promise<MarketingPlan> {
    return apiRequest<MarketingPlan>(
      `/api/planning/hotels/${hotelId}/plans/${planId}/status`,
      {
        method: "PUT",
        body: JSON.stringify({ status }),
      },
      "facility"
    );
  },

  /**
   * プランを削除
   */
  async deletePlan(hotelId: number, planId: number): Promise<void> {
    await apiRequest<void>(
      `/api/planning/hotels/${hotelId}/plans/${planId}`,
      {
        method: "DELETE",
      },
      "facility"
    );
  },

  // ============================================
  // クリエイティブ API
  // ============================================

  /**
   * クリエイティブアセットを生成
   */
  async generateCreative(
    hotelId: number,
    request: CreativeGenerationRequest
  ): Promise<CreativeAsset> {
    return apiRequest<CreativeAsset>(
      `/api/creative/hotels/${hotelId}/generate`,
      {
        method: "POST",
        body: JSON.stringify(request),
      },
      "facility"
    );
  },

  /**
   * プランのクリエイティブアセット一覧を取得
   */
  async listCreativeAssets(hotelId: number, planId: number): Promise<CreativeAsset[]> {
    return apiRequest<CreativeAsset[]>(
      `/api/creative/hotels/${hotelId}/plans/${planId}/assets`,
      {},
      "facility"
    );
  },

  /**
   * クリエイティブアセットを削除
   */
  async deleteCreativeAsset(hotelId: number, assetId: number): Promise<void> {
    await apiRequest<void>(
      `/api/creative/hotels/${hotelId}/assets/${assetId}`,
      {
        method: "DELETE",
      },
      "facility"
    );
  },
};
