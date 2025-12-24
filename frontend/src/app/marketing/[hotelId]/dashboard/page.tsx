"use client";

import { useEffect, useState } from "react";
import { Sparkles, UserCheck, Swords, Building, FileText, TrendingUp } from "lucide-react";
import { useHotel } from "@/lib/hotel-context";
import { marketingApi, AnalysisSession, MarketingPlan } from "@/lib/api";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export default function MarketingDashboard() {
  const { hotel, hotelId } = useHotel();
  const [session, setSession] = useState<AnalysisSession | null>(null);
  const [plans, setPlans] = useState<MarketingPlan[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [sessionData, plansData] = await Promise.all([
          marketingApi.getAnalysisSession(hotelId),
          marketingApi.listPlans(hotelId),
        ]);
        setSession(sessionData);
        setPlans(plansData);
      } catch (error) {
        console.error("Failed to load dashboard data:", error);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [hotelId]);

  const hasAnalysisData = session?.session_id !== null;
  const hasCustomerData = session?.csv_statistics && Object.keys(session.csv_statistics).length > 0;
  const hasMarketData = session?.competitors_list && Object.keys(session.competitors_list).length > 0;

  return (
    <section className="animate-fadeIn">
      <h2 className="text-3xl font-bold text-white mb-2">ダッシュボード</h2>
      <p className="text-slate-400 mb-8">
        {hotel.name}のマーケティング状況を一覧で確認できます
      </p>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-purple-500"></div>
        </div>
      ) : (
        <>
          {/* AIからの提案 */}
          <div className="glass-card p-8 mb-8">
            <div className="flex items-center gap-4 mb-6">
              <div className="w-12 h-12 bg-gradient-to-r from-purple-500 to-cyan-500 rounded-lg flex items-center justify-center">
                <Sparkles className="w-6 h-6 text-white" />
              </div>
              <h3 className="text-2xl font-bold text-white">AIからの提案</h3>
            </div>
            {hasAnalysisData && session?.csv_insights ? (
              <div className="max-h-64 overflow-y-auto prose prose-invert prose-sm max-w-none
                prose-headings:text-white prose-headings:font-semibold prose-headings:mt-4 prose-headings:mb-2
                prose-p:text-slate-300 prose-p:my-2
                prose-ul:text-slate-300 prose-ul:my-2 prose-ul:list-disc prose-ul:pl-4
                prose-ol:text-slate-300 prose-ol:my-2 prose-ol:list-decimal prose-ol:pl-4
                prose-li:text-slate-300 prose-li:my-1
                prose-strong:text-white prose-strong:font-semibold
                prose-code:text-cyan-400 prose-code:bg-white/10 prose-code:px-1 prose-code:py-0.5 prose-code:rounded
              ">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {session.csv_insights}
                </ReactMarkdown>
              </div>
            ) : (
              <div className="text-slate-400">
                <p className="mb-4">
                  まだ分析データがありません。以下のステップでマーケティングAIを活用しましょう：
                </p>
                <ol className="list-decimal list-inside space-y-2">
                  <li>「顧客を知る」で顧客データ（CSV）をアップロード</li>
                  <li>「市場を知る」で競合分析を実行</li>
                  <li>「プランを立てる」でマーケティングプランを生成</li>
                </ol>
              </div>
            )}
          </div>

          {/* ステータスカード */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <Link
              href={`/marketing/${hotelId}/persona`}
              className="glass-card p-6 hover:bg-white/10 transition-colors cursor-pointer"
            >
              <div className="flex items-center gap-3 mb-4">
                <UserCheck className="w-6 h-6 text-blue-400" />
                <h4 className="text-lg font-semibold text-white">顧客分析</h4>
              </div>
              <p className="text-slate-300">
                {hasCustomerData ? (
                  <span className="text-green-400">分析完了</span>
                ) : (
                  <span className="text-yellow-400">未分析</span>
                )}
              </p>
            </Link>

            <Link
              href={`/marketing/${hotelId}/market`}
              className="glass-card p-6 hover:bg-white/10 transition-colors cursor-pointer"
            >
              <div className="flex items-center gap-3 mb-4">
                <TrendingUp className="w-6 h-6 text-green-400" />
                <h4 className="text-lg font-semibold text-white">市場分析</h4>
              </div>
              <p className="text-slate-300">
                {hasMarketData ? (
                  <span className="text-green-400">分析完了</span>
                ) : (
                  <span className="text-yellow-400">未分析</span>
                )}
              </p>
            </Link>

            <Link
              href={`/marketing/${hotelId}/planner`}
              className="glass-card p-6 hover:bg-white/10 transition-colors cursor-pointer"
            >
              <div className="flex items-center gap-3 mb-4">
                <FileText className="w-6 h-6 text-orange-400" />
                <h4 className="text-lg font-semibold text-white">プラン</h4>
              </div>
              <p className="text-slate-300">
                {plans.length > 0 ? (
                  <span className="text-green-400">{plans.length}件のプラン</span>
                ) : (
                  <span className="text-yellow-400">プランなし</span>
                )}
              </p>
            </Link>
          </div>

          {/* プラン一覧（ある場合） */}
          {plans.length > 0 && (
            <div className="glass-card p-8">
              <div className="flex items-center gap-3 mb-6">
                <Swords className="w-6 h-6 text-purple-400" />
                <h3 className="text-2xl font-bold text-white">マーケティングプラン</h3>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {plans.slice(0, 3).map((plan) => (
                  <div
                    key={plan.id}
                    className="p-4 bg-white/5 rounded-lg border border-white/10"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="font-semibold text-white">{plan.plan_name}</h4>
                      <span
                        className={`text-xs px-2 py-1 rounded ${
                          plan.status === "approved"
                            ? "bg-green-500/20 text-green-400"
                            : "bg-yellow-500/20 text-yellow-400"
                        }`}
                      >
                        {plan.status === "approved" ? "承認済み" : "ドラフト"}
                      </span>
                    </div>
                    <p className="text-sm text-slate-400 line-clamp-2">
                      {plan.concept}
                    </p>
                  </div>
                ))}
              </div>
              {plans.length > 3 && (
                <Link
                  href={`/marketing/${hotelId}/planner`}
                  className="block mt-4 text-center text-cyan-400 hover:text-cyan-300"
                >
                  すべてのプランを見る →
                </Link>
              )}
            </div>
          )}
        </>
      )}
    </section>
  );
}


