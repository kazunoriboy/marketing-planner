/**
 * 認証ユーティリティ
 */

import {
  adminApi,
  facilityApi,
  SystemAdminResponse,
  FacilityAdminResponse,
  ApiError,
} from "./api";

export type UserType = "admin" | "facility";

export interface AuthState<T> {
  isAuthenticated: boolean;
  user: T | null;
  loading: boolean;
  error: string | null;
}

/**
 * トークンの存在を確認
 */
export function hasToken(userType: UserType): boolean {
  if (typeof window === "undefined") return false;
  return localStorage.getItem(`${userType}_access_token`) !== null;
}

/**
 * システムアドミンの認証状態を確認
 */
export async function checkAdminAuth(): Promise<AuthState<SystemAdminResponse>> {
  if (!hasToken("admin")) {
    return {
      isAuthenticated: false,
      user: null,
      loading: false,
      error: null,
    };
  }

  try {
    const user = await adminApi.me();
    return {
      isAuthenticated: true,
      user,
      loading: false,
      error: null,
    };
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      return {
        isAuthenticated: false,
        user: null,
        loading: false,
        error: null,
      };
    }
    return {
      isAuthenticated: false,
      user: null,
      loading: false,
      error: error instanceof Error ? error.message : "認証エラー",
    };
  }
}

/**
 * 施設管理者の認証状態を確認
 */
export async function checkFacilityAuth(): Promise<
  AuthState<FacilityAdminResponse>
> {
  if (!hasToken("facility")) {
    return {
      isAuthenticated: false,
      user: null,
      loading: false,
      error: null,
    };
  }

  try {
    const user = await facilityApi.me();
    return {
      isAuthenticated: true,
      user,
      loading: false,
      error: null,
    };
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      return {
        isAuthenticated: false,
        user: null,
        loading: false,
        error: null,
      };
    }
    return {
      isAuthenticated: false,
      user: null,
      loading: false,
      error: error instanceof Error ? error.message : "認証エラー",
    };
  }
}

/**
 * パスワード強度を検証（クライアント側）
 */
export function validatePassword(password: string): {
  isValid: boolean;
  errors: string[];
} {
  const errors: string[] = [];

  if (password.length < 8) {
    errors.push("パスワードは8文字以上である必要があります");
  }

  if (!/[A-Z]/.test(password)) {
    errors.push("パスワードには英大文字を含める必要があります");
  }

  if (!/[a-z]/.test(password)) {
    errors.push("パスワードには英小文字を含める必要があります");
  }

  if (!/\d/.test(password)) {
    errors.push("パスワードには数字を含める必要があります");
  }

  return {
    isValid: errors.length === 0,
    errors,
  };
}
