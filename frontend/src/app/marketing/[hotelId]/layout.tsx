"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { checkFacilityAuth, AuthState } from "@/lib/auth";
import { facilityApi, FacilityAdminResponse, HotelResponse, ApiError } from "@/lib/api";
import { HotelProvider } from "@/lib/hotel-context";
import MarketingSidebar from "@/components/MarketingSidebar";
import { AlertTriangle, ArrowLeft } from "lucide-react";
import Link from "next/link";

interface MarketingLayoutState {
  authState: AuthState<FacilityAdminResponse>;
  hotel: HotelResponse | null;
  error: string | null;
  loading: boolean;
}

export default function MarketingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const params = useParams();
  const hotelId = Number(params.hotelId);

  const [state, setState] = useState<MarketingLayoutState>({
    authState: {
      isAuthenticated: false,
      user: null,
      loading: true,
      error: null,
    },
    hotel: null,
    error: null,
    loading: true,
  });

  useEffect(() => {
    async function checkAccess() {
      // 1. 認証チェック
      const authState = await checkFacilityAuth();
      
      if (!authState.isAuthenticated) {
        router.push("/facility/login");
        return;
      }

      // 2. 施設へのアクセス権限チェック
      try {
        const hotel = await facilityApi.getHotel(hotelId);
        setState({
          authState,
          hotel,
          error: null,
          loading: false,
        });
      } catch (err) {
        if (err instanceof ApiError) {
          if (err.status === 403) {
            setState({
              authState,
              hotel: null,
              error: "この施設へのアクセス権限がありません",
              loading: false,
            });
          } else if (err.status === 404) {
            setState({
              authState,
              hotel: null,
              error: "施設が見つかりません",
              loading: false,
            });
          } else {
            setState({
              authState,
              hotel: null,
              error: err.detail,
              loading: false,
            });
          }
        } else {
          setState({
            authState,
            hotel: null,
            error: "エラーが発生しました",
            loading: false,
          });
        }
      }
    }

    if (!isNaN(hotelId)) {
      checkAccess();
    } else {
      setState((prev) => ({
        ...prev,
        error: "無効な施設IDです",
        loading: false,
      }));
    }
  }, [hotelId, router]);

  // ローディング中
  if (state.loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-purple-500"></div>
      </div>
    );
  }

  // エラー（アクセス拒否など）
  if (state.error || !state.hotel) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
        <div className="glass-card p-8 max-w-md w-full mx-4 text-center">
          <div className="w-16 h-16 bg-red-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
            <AlertTriangle className="w-8 h-8 text-red-400" />
          </div>
          <h1 className="text-2xl font-bold text-white mb-4">
            アクセスできません
          </h1>
          <p className="text-slate-300 mb-6">
            {state.error || "この施設へのアクセス権限がありません"}
          </p>
          <Link
            href="/facility/hotels"
            className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-purple-500 to-cyan-500 text-white rounded-lg hover:from-purple-600 hover:to-cyan-600 transition-all"
          >
            <ArrowLeft className="w-4 h-4" />
            施設一覧に戻る
          </Link>
        </div>
      </div>
    );
  }

  // 正常表示
  return (
    <HotelProvider hotel={state.hotel}>
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
        <main className="flex h-screen overflow-hidden">
          <MarketingSidebar hotel={state.hotel} />
          <div className="flex-1 p-8 overflow-y-auto">{children}</div>
        </main>
      </div>
    </HotelProvider>
  );
}


