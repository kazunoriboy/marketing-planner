"use client";

import { useEffect, useState } from "react";
import { TrendingUp, Search, Loader2, Building2, MapPin } from "lucide-react";
import { useHotel } from "@/lib/hotel-context";
import { marketingApi, AnalysisSession } from "@/lib/api";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export default function MarketPage() {
  const { hotel, hotelId } = useHotel();
  const [session, setSession] = useState<AnalysisSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [radiusKm, setRadiusKm] = useState(10);

  useEffect(() => {
    async function loadData() {
      try {
        const sessionData = await marketingApi.getAnalysisSession(hotelId);
        setSession(sessionData);
      } catch (error) {
        console.error("Failed to load session:", error);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [hotelId]);

  const handleAnalyzeMarket = async () => {
    setAnalyzing(true);
    try {
      await marketingApi.analyzeMarket(hotelId, radiusKm);
      // Reload session data
      const sessionData = await marketingApi.getAnalysisSession(hotelId);
      setSession(sessionData);
    } catch (error) {
      console.error("Market analysis failed:", error);
    } finally {
      setAnalyzing(false);
    }
  };

  const hasMarketData = session?.competitors_list && Object.keys(session.competitors_list).length > 0;

  return (
    <section className="animate-fadeIn">
      <h2 className="text-3xl font-bold text-white mb-2">市場を知る</h2>
      <p className="text-slate-400 mb-8">
        {hotel.name}周辺の競合分析と市場動向を把握します
      </p>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-purple-500"></div>
        </div>
      ) : (
        <>
          {/* 市場調査実行セクション */}
          <div className="glass-card p-8 mb-8">
            <div className="flex items-center gap-3 mb-6">
              <Search className="w-6 h-6 text-green-400" />
              <h3 className="text-2xl font-bold text-white">エリア市場調査</h3>
            </div>

            <div className="flex items-center gap-2 mb-4 text-slate-300">
              <MapPin className="w-4 h-4" />
              <span>{hotel.address}</span>
            </div>

            <div className="flex items-center gap-4 mb-6">
              <label className="text-slate-300">調査範囲：</label>
              <select
                value={radiusKm}
                onChange={(e) => setRadiusKm(Number(e.target.value))}
                className="bg-white/5 border border-white/10 rounded-lg p-2 text-white"
              >
                <option value={5}>5km</option>
                <option value={10}>10km</option>
                <option value={20}>20km</option>
                <option value={50}>50km</option>
              </select>
            </div>

            <button
              onClick={handleAnalyzeMarket}
              disabled={analyzing}
              className="w-full bg-gradient-to-r from-purple-500 to-cyan-500 text-white py-4 rounded-lg hover:from-purple-600 hover:to-cyan-600 transition-all font-semibold disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {analyzing ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  分析中...
                </>
              ) : (
                <>
                  <TrendingUp className="w-5 h-5" />
                  市場調査を開始
                </>
              )}
            </button>
          </div>

          {/* 市場分析結果 */}
          {hasMarketData && (
            <>
              {/* 競合情報 */}
              <div className="glass-card p-8 mb-8">
                <div className="flex items-center gap-3 mb-6">
                  <Building2 className="w-6 h-6 text-orange-400" />
                  <h3 className="text-2xl font-bold text-white">競合状況</h3>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {session?.competitors_list && (
                    <>
                      <div className="p-4 bg-white/5 rounded-lg border border-white/10">
                        <p className="text-sm text-slate-400 mb-1">エリアタイプ</p>
                        <p className="text-lg font-semibold text-white">
                          {(session.competitors_list as Record<string, unknown>).area_type as string || "不明"}
                        </p>
                      </div>
                      <div className="p-4 bg-white/5 rounded-lg border border-white/10">
                        <p className="text-sm text-slate-400 mb-1">推定競合数</p>
                        <p className="text-lg font-semibold text-white">
                          {(session.competitors_list as Record<string, unknown>).estimated_competitors as string || "不明"}
                        </p>
                      </div>
                    </>
                  )}
                </div>

                {session?.competitors_list && Boolean((session.competitors_list as Record<string, unknown>).competitive_factors) && (
                  <div className="mt-6">
                    <p className="text-sm text-slate-400 mb-2">競合の強み</p>
                    <div className="flex flex-wrap gap-2">
                      {((session.competitors_list as Record<string, unknown>).competitive_factors as string[]).map((factor, idx) => (
                        <span
                          key={idx}
                          className="px-3 py-1 bg-orange-500/20 text-orange-300 rounded-full text-sm"
                        >
                          {factor}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* 地域トレンド */}
              {session?.regional_trends && (
                <div className="glass-card p-8">
                  <div className="flex items-center gap-3 mb-6">
                    <TrendingUp className="w-6 h-6 text-purple-400" />
                    <h3 className="text-2xl font-bold text-white">地域トレンド</h3>
                  </div>
                  <div className="p-6 bg-white/5 rounded-lg border border-white/10 prose prose-invert prose-sm max-w-none
                    prose-headings:text-white prose-headings:font-semibold prose-headings:mt-4 prose-headings:mb-2
                    prose-p:text-slate-300 prose-p:my-2
                    prose-ul:text-slate-300 prose-ul:my-2 prose-ul:list-disc prose-ul:pl-4
                    prose-ol:text-slate-300 prose-ol:my-2 prose-ol:list-decimal prose-ol:pl-4
                    prose-li:text-slate-300 prose-li:my-1
                    prose-strong:text-white prose-strong:font-semibold
                    prose-code:text-cyan-400 prose-code:bg-white/10 prose-code:px-1 prose-code:py-0.5 prose-code:rounded
                  ">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {session.regional_trends}
                    </ReactMarkdown>
                  </div>
                </div>
              )}
            </>
          )}
        </>
      )}
    </section>
  );
}


