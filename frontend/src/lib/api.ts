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
  cv_url?: string;
  hotel_assets?: HotelAssets;
  role: string;
}

// 施設の資産情報
export interface HotelAssets {
  room_amenities?: string[];    // 部屋の設備・備品
  shared_facilities?: string[]; // 共有施設
  dining?: string[];            // 料理・食事
  services?: string[];          // サービス
  experiences?: string[];       // 体験・アクティビティ
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
  cv_url?: string;
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

  /**
   * 施設の資産情報を取得
   */
  async getHotelAssets(hotelId: number): Promise<HotelAssets> {
    return apiRequest<HotelAssets>(
      `/facility/hotels/${hotelId}/assets`,
      {},
      "facility"
    );
  },

  /**
   * 施設の資産情報を更新
   */
  async updateHotelAssets(hotelId: number, assets: Partial<HotelAssets>): Promise<HotelAssets> {
    return apiRequest<HotelAssets>(
      `/facility/hotels/${hotelId}/assets`,
      {
        method: "PUT",
        body: JSON.stringify(assets),
      },
      "facility"
    );
  },

  /**
   * 画像から施設の資産を自動抽出
   */
  async extractAssetsFromImage(hotelId: number, file: File): Promise<HotelAssets> {
    const formData = new FormData();
    formData.append("file", file);

    const makeRequest = async (token: string | null) => {
      return fetch(
        `${API_BASE_URL}/facility/hotels/${hotelId}/assets/extract-from-image`,
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
            token = tokens.access_token;
            response = await makeRequest(token);
          } else {
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
        errorData.detail || "画像からの資産抽出に失敗しました"
      );
    }

    return response.json();
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
  upload_count?: number;
  period_overlap_warning?: string;
}

export interface CSVUploadHistory {
  id: number;
  hotel_id: number;
  filename: string;
  upload_date: string;
  record_count: number;
  data_period_start: string | null;
  data_period_end: string | null;
  is_migrated: boolean;
  notes: string | null;
}

export interface CSVUploadHistoryListResponse {
  hotel_id: number;
  histories: CSVUploadHistory[];
  total_count: number;
}

export interface CSVHistoryDeleteResponse {
  deleted_id: number;
  remaining_count: number;
  statistics: Record<string, unknown>;
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
  lp_image_urls: Record<string, unknown>;
  ad_image_urls: Record<string, unknown>;
  ad_copy: Record<string, unknown>;
  ota_text: OTATextContent;
  generation_prompts: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

// OTAテキストの型定義
export interface OTAPlatformText {
  plan_title: string;
  catch_copy: string;
  plan_description: string;
  features: string[];
}

export interface OTATextContent {
  jalan?: OTAPlatformText;
  rakuten?: OTAPlatformText;
}

export interface CreativeGenerationRequest {
  plan_id: number;
  generate_lp?: boolean;
  generate_images?: boolean;
  generate_ad_copy?: boolean;
  generate_ota_text?: boolean;  // OTAテキスト（じゃらん、楽天トラベル向け）
}

// オペレーション関連の型
export interface OperationChatMessage {
  id: number;
  operation_manual_id: number;
  role: "user" | "assistant";
  content: string;
  msg_metadata: {
    extracted_context?: Record<string, unknown>;
    is_ready_for_manual?: boolean;
  };
  created_at: string;
}

export interface OperationManual {
  id: number;
  marketing_plan_id: number;
  status: "in_progress" | "completed";
  manual_content: ManualContent | Record<string, never>;
  facility_context: Record<string, unknown>;
  chat_messages?: OperationChatMessage[];
  created_at: string;
  updated_at: string;
}

export interface ManualTask {
  title: string;
  description: string;
  estimated_time?: string;
  responsible?: string;
  tools?: string[];
  tips?: string;
}

export interface ManualPhase {
  name: string;
  description?: string;
  duration?: string;
  tasks: ManualTask[];
}

export interface ManualContent {
  title: string;
  overview: string;
  phases: ManualPhase[];
  timeline?: string;
  budget_estimate?: string;
  success_metrics?: string[];
  notes?: string;
}

// SNS投稿生成関連の型
export interface SNSPostGenerationRequest {
  platform: string;
  post_type: string;
  description: string;
}

export interface SNSPostResponse {
  platform: string;
  post_type: string;
  content: string;
  hashtags: string[];
  generated_at: string;
}

// 口コミ関連の型
export interface ReviewUrlsUpdate {
  jalan?: string;
  google?: string;
}

export interface ReviewUrlsResponse {
  hotel_id: number;
  review_urls: Record<string, string>;
  updated_at: string;
}

export interface ReviewAnalysisResponse {
  session_id: number;
  reviews_summary: Record<string, unknown>;
  sources: Array<Record<string, unknown>>;
  total_reviews: number;
  analyzed_at: string;
}

// ペルソナ関連の型
export interface Persona {
  name: string;
  age_range: string;
  gender: string;
  location: string;  // 住んでいるところ
  occupation: string;
  travel_purpose: string;
  values: string[];
  budget_range: string;
  information_source: string[];
  needs: string[];
  pain_points: string[];
  description: string;
  rationale: string;  // このペルソナを作成した根拠
}

export interface PersonaGenerationResponse {
  session_id: number;
  personas: Persona[];
  generated_at: string;
}

export interface PersonasResponse {
  session_id: number;
  personas: Persona[];
  updated_at: string | null;
}

export interface PersonaEditRequest {
  persona_index: number;
  instruction: string;
}

export interface PersonaEditResponse {
  session_id: number;
  persona: Persona;
  persona_index: number;
  updated_at: string;
}

// 既存プラン関連の型
export interface ExistingPlan {
  id: number;
  hotel_id: number;
  plan_title: string;
  plan_description: string;
  room_facilities: string[];
  hotel_assets: string[];
  price_info: {
    min?: number;
    max?: number;
    standard?: number;
  };
  meal_info: {
    breakfast?: string;
    dinner?: string;
    options?: string[];
  };
  notes?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ExistingPlanCreate {
  plan_title: string;
  plan_description: string;
  room_facilities?: string[];
  hotel_assets?: string[];
  price_info?: {
    min?: number;
    max?: number;
    standard?: number;
  };
  meal_info?: {
    breakfast?: string;
    dinner?: string;
    options?: string[];
  };
  notes?: string;
}

export interface ExistingPlanUpdate {
  plan_title?: string;
  plan_description?: string;
  room_facilities?: string[];
  hotel_assets?: string[];
  price_info?: {
    min?: number;
    max?: number;
    standard?: number;
  };
  meal_info?: {
    breakfast?: string;
    dinner?: string;
    options?: string[];
  };
  notes?: string;
  is_active?: boolean;
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
   * CSVアップロード履歴を取得
   */
  async getCSVUploadHistory(hotelId: number): Promise<CSVUploadHistoryListResponse> {
    return apiRequest<CSVUploadHistoryListResponse>(
      `/api/analysis/hotels/${hotelId}/csv-history`,
      {},
      "facility"
    );
  },

  /**
   * CSVアップロード履歴を削除
   */
  async deleteCSVUploadHistory(hotelId: number, historyId: number): Promise<CSVHistoryDeleteResponse> {
    return apiRequest<CSVHistoryDeleteResponse>(
      `/api/analysis/hotels/${hotelId}/csv-history/${historyId}`,
      {
        method: "DELETE",
      },
      "facility"
    );
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
  // 口コミ収集・分析 API
  // ============================================

  /**
   * 口コミURLを取得
   */
  async getReviewUrls(hotelId: number): Promise<ReviewUrlsResponse> {
    return apiRequest<ReviewUrlsResponse>(
      `/api/analysis/hotels/${hotelId}/review-urls`,
      {},
      "facility"
    );
  },

  /**
   * 口コミURLを登録・更新
   */
  async updateReviewUrls(hotelId: number, urls: ReviewUrlsUpdate): Promise<ReviewUrlsResponse> {
    return apiRequest<ReviewUrlsResponse>(
      `/api/analysis/hotels/${hotelId}/review-urls`,
      {
        method: "PUT",
        body: JSON.stringify(urls),
      },
      "facility"
    );
  },

  /**
   * 口コミを収集・分析（Dify + Jina Reader）
   */
  async analyzeReviews(hotelId: number): Promise<ReviewAnalysisResponse> {
    return apiRequest<ReviewAnalysisResponse>(
      `/api/analysis/hotels/${hotelId}/reviews/analyze`,
      {
        method: "POST",
      },
      "facility"
    );
  },

  // ============================================
  // ペルソナ API
  // ============================================

  /**
   * ペルソナを生成
   */
  async generatePersonas(hotelId: number, numPersonas: number = 3): Promise<PersonaGenerationResponse> {
    return apiRequest<PersonaGenerationResponse>(
      `/api/analysis/hotels/${hotelId}/personas/generate?num_personas=${numPersonas}`,
      {
        method: "POST",
      },
      "facility"
    );
  },

  /**
   * 生成済みのペルソナを取得
   */
  async getPersonas(hotelId: number): Promise<PersonasResponse> {
    return apiRequest<PersonasResponse>(
      `/api/analysis/hotels/${hotelId}/personas`,
      {},
      "facility"
    );
  },

  /**
   * ペルソナを修正
   */
  async editPersona(hotelId: number, personaIndex: number, instruction: string): Promise<PersonaEditResponse> {
    return apiRequest<PersonaEditResponse>(
      `/api/analysis/hotels/${hotelId}/personas/${personaIndex}`,
      {
        method: "PUT",
        body: JSON.stringify({ persona_index: personaIndex, instruction }),
      },
      "facility"
    );
  },

  // ============================================
  // プランニング API
  // ============================================

  /**
   * マーケティングプランを生成
   * @param hotelId 施設ID
   * @param numPlans 生成するプラン数
   * @param personaIndex 特定のペルソナに対して生成する場合のインデックス（0始まり）
   */
  async generatePlans(hotelId: number, numPlans: number = 3, personaIndex?: number): Promise<MarketingPlan[]> {
    let url = `/api/planning/hotels/${hotelId}/generate?num_plans=${numPlans}`;
    if (personaIndex !== undefined) {
      url += `&persona_index=${personaIndex}`;
    }
    return apiRequest<MarketingPlan[]>(
      url,
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

  /**
   * プランのセクションを修正
   */
  async editPlanSection(
    hotelId: number,
    planId: number,
    section: "concept" | "target_audience" | "price_range" | "benefits",
    instruction: string
  ): Promise<MarketingPlan> {
    return apiRequest<MarketingPlan>(
      `/api/planning/hotels/${hotelId}/plans/${planId}/edit-section`,
      {
        method: "PUT",
        body: JSON.stringify({ section, instruction }),
      },
      "facility"
    );
  },

  // ============================================
  // 既存プラン API
  // ============================================

  /**
   * 既存プラン一覧を取得
   */
  async listExistingPlans(hotelId: number): Promise<ExistingPlan[]> {
    return apiRequest<ExistingPlan[]>(
      `/api/planning/hotels/${hotelId}/existing-plans`,
      {},
      "facility"
    );
  },

  /**
   * 既存プランを作成
   */
  async createExistingPlan(hotelId: number, data: ExistingPlanCreate): Promise<ExistingPlan> {
    return apiRequest<ExistingPlan>(
      `/api/planning/hotels/${hotelId}/existing-plans`,
      {
        method: "POST",
        body: JSON.stringify(data),
      },
      "facility"
    );
  },

  /**
   * 既存プランを取得
   */
  async getExistingPlan(hotelId: number, planId: number): Promise<ExistingPlan> {
    return apiRequest<ExistingPlan>(
      `/api/planning/hotels/${hotelId}/existing-plans/${planId}`,
      {},
      "facility"
    );
  },

  /**
   * 既存プランを更新
   */
  async updateExistingPlan(hotelId: number, planId: number, data: ExistingPlanUpdate): Promise<ExistingPlan> {
    return apiRequest<ExistingPlan>(
      `/api/planning/hotels/${hotelId}/existing-plans/${planId}`,
      {
        method: "PUT",
        body: JSON.stringify(data),
      },
      "facility"
    );
  },

  /**
   * 既存プランを削除
   */
  async deleteExistingPlan(hotelId: number, planId: number): Promise<void> {
    await apiRequest<void>(
      `/api/planning/hotels/${hotelId}/existing-plans/${planId}`,
      {
        method: "DELETE",
      },
      "facility"
    );
  },

  /**
   * 既存プランベースでマーケティングプランを生成
   */
  async generatePlansFromExisting(
    hotelId: number,
    existingPlanId: number,
    numPlans: number = 3,
    personaIndex?: number
  ): Promise<MarketingPlan[]> {
    return apiRequest<MarketingPlan[]>(
      `/api/planning/hotels/${hotelId}/generate-from-existing`,
      {
        method: "POST",
        body: JSON.stringify({
          existing_plan_id: existingPlanId,
          num_plans: numPlans,
          persona_index: personaIndex,
        }),
      },
      "facility"
    );
  },

  /**
   * 施設の資産＋既存プラン全体からマーケティングプランを生成
   */
  async generatePlansFromAssets(
    hotelId: number,
    numPlans: number = 3,
    personaIndex?: number
  ): Promise<MarketingPlan[]> {
    return apiRequest<MarketingPlan[]>(
      `/api/planning/hotels/${hotelId}/generate-from-assets`,
      {
        method: "POST",
        body: JSON.stringify({
          num_plans: numPlans,
          persona_index: personaIndex,
        }),
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

  /**
   * LPをファイルとして保存しプレビューURLを取得
   */
  async saveLpToFile(hotelId: number, assetId: number): Promise<{ message: string; preview_url: string; asset_id: number }> {
    return apiRequest<{ message: string; preview_url: string; asset_id: number }>(
      `/api/creative/hotels/${hotelId}/assets/${assetId}/save-lp`,
      {
        method: "POST",
      },
      "facility"
    );
  },

  /**
   * SNS投稿を生成
   */
  async generateSNSPost(
    hotelId: number,
    request: SNSPostGenerationRequest
  ): Promise<SNSPostResponse> {
    return apiRequest<SNSPostResponse>(
      `/api/creative/hotels/${hotelId}/generate-sns-post`,
      {
        method: "POST",
        body: JSON.stringify(request),
      },
      "facility"
    );
  },

  /**
   * LP用画像をアップロードして差し替え
   */
  async uploadLpImage(
    hotelId: number,
    assetId: number,
    imageType: "hero" | "feature" | "ambiance",
    file: File
  ): Promise<{
    message: string;
    image_type: string;
    new_url: string;
    filename: string;
    lp_image_urls: Record<string, string>;
  }> {
    const formData = new FormData();
    formData.append("file", file);

    const makeRequest = async (token: string | null) => {
      return fetch(
        `${API_BASE_URL}/api/creative/hotels/${hotelId}/assets/${assetId}/lp-images/${imageType}`,
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
            token = tokens.access_token;
            response = await makeRequest(token);
          } else {
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
        errorData.detail || "画像アップロードに失敗しました"
      );
    }

    return response.json();
  },

  // ============================================
  // オペレーション API
  // ============================================

  /**
   * オペレーションチャットを開始（または既存セッションを取得）
   */
  async startOperationChat(hotelId: number, planId: number): Promise<OperationManual> {
    return apiRequest<OperationManual>(
      `/api/operation/hotels/${hotelId}/plans/${planId}/start`,
      {
        method: "POST",
      },
      "facility"
    );
  },

  /**
   * チャットメッセージを送信
   */
  async sendOperationMessage(
    hotelId: number,
    manualId: number,
    message: string
  ): Promise<OperationChatMessage> {
    return apiRequest<OperationChatMessage>(
      `/api/operation/hotels/${hotelId}/manuals/${manualId}/chat`,
      {
        method: "POST",
        body: JSON.stringify({ message }),
      },
      "facility"
    );
  },

  /**
   * マニュアルを生成
   */
  async generateOperationManual(
    hotelId: number,
    manualId: number,
    additionalInstructions?: string
  ): Promise<OperationManual> {
    return apiRequest<OperationManual>(
      `/api/operation/hotels/${hotelId}/manuals/${manualId}/generate`,
      {
        method: "POST",
        body: JSON.stringify({ additional_instructions: additionalInstructions }),
      },
      "facility"
    );
  },

  /**
   * オペレーションマニュアルを取得
   */
  async getOperationManual(hotelId: number, planId: number): Promise<OperationManual> {
    return apiRequest<OperationManual>(
      `/api/operation/hotels/${hotelId}/plans/${planId}/manual`,
      {},
      "facility"
    );
  },

  /**
   * オペレーションマニュアルを削除
   */
  async deleteOperationManual(hotelId: number, manualId: number): Promise<void> {
    await apiRequest<void>(
      `/api/operation/hotels/${hotelId}/manuals/${manualId}`,
      {
        method: "DELETE",
      },
      "facility"
    );
  },
};
