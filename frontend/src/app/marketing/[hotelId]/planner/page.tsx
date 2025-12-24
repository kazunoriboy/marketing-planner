"use client";

import { useEffect, useState } from "react";
import { Lightbulb, FileText, Loader2, Trash2, CheckCircle, Clock, Plus, Users, DollarSign, Gift, Target, Globe } from "lucide-react";
import { useHotel } from "@/lib/hotel-context";
import { marketingApi, MarketingPlan, AnalysisSession } from "@/lib/api";

// 型定義
interface TargetAudience {
  age_range?: string;
  demographics?: string;
  psychographics?: string;
  needs?: string[];
}

interface PriceRange {
  min?: number;
  max?: number;
  recommended?: number;
  rationale?: string;
}

interface Benefits {
  main_benefits?: string[];
  unique_value?: string;
  amenities?: string[];
}

interface Strategy3C {
  customer?: string;
  competitor?: string;
  company?: string;
}

interface StrategyPEST {
  political?: string;
  economic?: string;
  social?: string;
  technological?: string;
}

// 価格をフォーマット
function formatPrice(price: number): string {
  return `¥${price.toLocaleString("ja-JP")}`;
}

export default function PlannerPage() {
  const { hotel, hotelId } = useHotel();
  const [session, setSession] = useState<AnalysisSession | null>(null);
  const [plans, setPlans] = useState<MarketingPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [numPlans, setNumPlans] = useState(3);
  const [selectedPlan, setSelectedPlan] = useState<MarketingPlan | null>(null);

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
        console.error("Failed to load data:", error);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [hotelId]);

  const handleGeneratePlans = async () => {
    setGenerating(true);
    try {
      const newPlans = await marketingApi.generatePlans(hotelId, numPlans);
      setPlans((prev) => [...newPlans, ...prev]);
    } catch (error) {
      console.error("Plan generation failed:", error);
    } finally {
      setGenerating(false);
    }
  };

  const handleUpdateStatus = async (planId: number, status: "draft" | "approved") => {
    try {
      const updated = await marketingApi.updatePlanStatus(hotelId, planId, status);
      setPlans((prev) => prev.map((p) => (p.id === planId ? updated : p)));
      if (selectedPlan?.id === planId) {
        setSelectedPlan(updated);
      }
    } catch (error) {
      console.error("Status update failed:", error);
    }
  };

  const handleDeletePlan = async (planId: number) => {
    if (!confirm("このプランを削除しますか？")) return;
    try {
      await marketingApi.deletePlan(hotelId, planId);
      setPlans((prev) => prev.filter((p) => p.id !== planId));
      if (selectedPlan?.id === planId) {
        setSelectedPlan(null);
      }
    } catch (error) {
      console.error("Delete failed:", error);
    }
  };

  const hasAnalysisData = session?.session_id !== null && (
    (session?.csv_statistics && Object.keys(session.csv_statistics).length > 0) ||
    (session?.competitors_list && Object.keys(session.competitors_list).length > 0)
  );

  return (
    <section className="animate-fadeIn">
      <h2 className="text-3xl font-bold text-white mb-2">プランを立てる</h2>
      <p className="text-slate-400 mb-8">
        {hotel.name}のマーケティングプランをAIで生成します
      </p>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-purple-500"></div>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* 左側：プラン生成＆一覧 */}
          <div className="lg:col-span-1 space-y-6">
            {/* プラン生成セクション */}
            <div className="glass-card p-6">
              <div className="flex items-center gap-3 mb-4">
                <Lightbulb className="w-6 h-6 text-yellow-400" />
                <h3 className="text-xl font-bold text-white">プラン生成</h3>
              </div>

              {!hasAnalysisData ? (
                <p className="text-slate-400 text-sm">
                  プランを生成するには、先に「顧客を知る」または「市場を知る」で分析を実行してください。
                </p>
              ) : (
                <>
                  <div className="flex items-center gap-4 mb-4">
                    <label className="text-slate-300 text-sm">生成数：</label>
                    <select
                      value={numPlans}
                      onChange={(e) => setNumPlans(Number(e.target.value))}
                      className="bg-white/5 border border-white/10 rounded-lg p-2 text-white text-sm"
                    >
                      <option value={1}>1件</option>
                      <option value={3}>3件</option>
                      <option value={5}>5件</option>
                    </select>
                  </div>

                  <button
                    onClick={handleGeneratePlans}
                    disabled={generating}
                    className="w-full bg-gradient-to-r from-purple-500 to-cyan-500 text-white py-3 rounded-lg hover:from-purple-600 hover:to-cyan-600 transition-all font-semibold disabled:opacity-50 flex items-center justify-center gap-2"
                  >
                    {generating ? (
                      <>
                        <Loader2 className="w-5 h-5 animate-spin" />
                        生成中...
                      </>
                    ) : (
                      <>
                        <Plus className="w-5 h-5" />
                        プランを生成
                      </>
                    )}
                  </button>
                </>
              )}
            </div>

            {/* プラン一覧 */}
            <div className="glass-card p-6">
              <div className="flex items-center gap-3 mb-4">
                <FileText className="w-6 h-6 text-blue-400" />
                <h3 className="text-xl font-bold text-white">プラン一覧</h3>
              </div>

              {plans.length === 0 ? (
                <p className="text-slate-400 text-sm">プランがありません</p>
              ) : (
                <div className="space-y-2 max-h-96 overflow-y-auto">
                  {plans.map((plan) => (
                    <div
                      key={plan.id}
                      onClick={() => setSelectedPlan(plan)}
                      className={`p-3 rounded-lg cursor-pointer transition-colors ${
                        selectedPlan?.id === plan.id
                          ? "bg-white/20 border border-white/30"
                          : "bg-white/5 border border-white/10 hover:bg-white/10"
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-medium text-white text-sm truncate">
                          {plan.plan_name}
                        </span>
                        {plan.status === "approved" ? (
                          <CheckCircle className="w-4 h-4 text-green-400 flex-shrink-0" />
                        ) : (
                          <Clock className="w-4 h-4 text-yellow-400 flex-shrink-0" />
                        )}
                      </div>
                      <p className="text-xs text-slate-400 line-clamp-1">
                        {plan.concept}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* 右側：プラン詳細 */}
          <div className="lg:col-span-2">
            {selectedPlan ? (
              <div className="glass-card p-8">
                <div className="flex items-start justify-between mb-6">
                  <div>
                    <h3 className="text-2xl font-bold text-white mb-2">
                      {selectedPlan.plan_name}
                    </h3>
                    <span
                      className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm ${
                        selectedPlan.status === "approved"
                          ? "bg-green-500/20 text-green-400"
                          : "bg-yellow-500/20 text-yellow-400"
                      }`}
                    >
                      {selectedPlan.status === "approved" ? (
                        <>
                          <CheckCircle className="w-4 h-4" />
                          承認済み
                        </>
                      ) : (
                        <>
                          <Clock className="w-4 h-4" />
                          ドラフト
                        </>
                      )}
                    </span>
                  </div>
                  <div className="flex gap-2">
                    {selectedPlan.status === "draft" ? (
                      <button
                        onClick={() => handleUpdateStatus(selectedPlan.id, "approved")}
                        className="px-4 py-2 bg-green-500/20 text-green-400 rounded-lg hover:bg-green-500/30 transition-colors text-sm"
                      >
                        承認
                      </button>
                    ) : (
                      <button
                        onClick={() => handleUpdateStatus(selectedPlan.id, "draft")}
                        className="px-4 py-2 bg-yellow-500/20 text-yellow-400 rounded-lg hover:bg-yellow-500/30 transition-colors text-sm"
                      >
                        ドラフトに戻す
                      </button>
                    )}
                    <button
                      onClick={() => handleDeletePlan(selectedPlan.id)}
                      className="px-4 py-2 bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30 transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {/* コンセプト */}
                <div className="mb-6">
                  <h4 className="text-lg font-semibold text-white mb-2">コンセプト</h4>
                  <p className="text-slate-300 p-4 bg-white/5 rounded-lg">
                    {selectedPlan.concept}
                  </p>
                </div>

                {/* ターゲット顧客 */}
                {selectedPlan.target_audience && Object.keys(selectedPlan.target_audience).length > 0 && (
                  <div className="mb-6">
                    <div className="flex items-center gap-2 mb-3">
                      <Users className="w-5 h-5 text-blue-400" />
                      <h4 className="text-lg font-semibold text-white">ターゲット顧客</h4>
                    </div>
                    <div className="p-4 bg-white/5 rounded-lg space-y-3">
                      {(() => {
                        const target = selectedPlan.target_audience as TargetAudience;
                        return (
                          <>
                            {target.age_range && (
                              <div className="flex items-start gap-3">
                                <span className="text-slate-400 text-sm min-w-[100px]">年齢層</span>
                                <span className="text-white">{target.age_range}</span>
                              </div>
                            )}
                            {target.demographics && (
                              <div className="flex items-start gap-3">
                                <span className="text-slate-400 text-sm min-w-[100px]">属性</span>
                                <span className="text-white">{target.demographics}</span>
                              </div>
                            )}
                            {target.psychographics && (
                              <div className="flex items-start gap-3">
                                <span className="text-slate-400 text-sm min-w-[100px]">志向</span>
                                <span className="text-white">{target.psychographics}</span>
                              </div>
                            )}
                            {target.needs && target.needs.length > 0 && (
                              <div className="flex items-start gap-3">
                                <span className="text-slate-400 text-sm min-w-[100px]">ニーズ</span>
                                <div className="flex flex-wrap gap-2">
                                  {target.needs.map((need, idx) => (
                                    <span key={idx} className="px-2 py-1 bg-blue-500/20 text-blue-300 rounded-full text-sm">
                                      {need}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}
                          </>
                        );
                      })()}
                    </div>
                  </div>
                )}

                {/* 価格帯 */}
                {selectedPlan.price_range && Object.keys(selectedPlan.price_range).length > 0 && (
                  <div className="mb-6">
                    <div className="flex items-center gap-2 mb-3">
                      <DollarSign className="w-5 h-5 text-green-400" />
                      <h4 className="text-lg font-semibold text-white">価格帯</h4>
                    </div>
                    <div className="p-4 bg-white/5 rounded-lg">
                      {(() => {
                        const price = selectedPlan.price_range as PriceRange;
                        return (
                          <>
                            <div className="grid grid-cols-3 gap-4 mb-4">
                              {price.min !== undefined && (
                                <div className="text-center p-3 bg-white/5 rounded-lg">
                                  <p className="text-slate-400 text-xs mb-1">最低価格</p>
                                  <p className="text-white font-semibold">{formatPrice(price.min)}</p>
                                </div>
                              )}
                              {price.recommended !== undefined && (
                                <div className="text-center p-3 bg-green-500/20 rounded-lg border border-green-500/30">
                                  <p className="text-green-400 text-xs mb-1">推奨価格</p>
                                  <p className="text-green-300 font-bold text-lg">{formatPrice(price.recommended)}</p>
                                </div>
                              )}
                              {price.max !== undefined && (
                                <div className="text-center p-3 bg-white/5 rounded-lg">
                                  <p className="text-slate-400 text-xs mb-1">最高価格</p>
                                  <p className="text-white font-semibold">{formatPrice(price.max)}</p>
                                </div>
                              )}
                            </div>
                            {price.rationale && (
                              <div className="p-3 bg-white/5 rounded-lg">
                                <p className="text-slate-400 text-xs mb-1">価格設定の根拠</p>
                                <p className="text-slate-300 text-sm">{price.rationale}</p>
                              </div>
                            )}
                          </>
                        );
                      })()}
                    </div>
                  </div>
                )}

                {/* 特典 */}
                {selectedPlan.benefits && Object.keys(selectedPlan.benefits).length > 0 && (
                  <div className="mb-6">
                    <div className="flex items-center gap-2 mb-3">
                      <Gift className="w-5 h-5 text-pink-400" />
                      <h4 className="text-lg font-semibold text-white">特典・特徴</h4>
                    </div>
                    <div className="p-4 bg-white/5 rounded-lg space-y-4">
                      {(() => {
                        const benefits = selectedPlan.benefits as Benefits;
                        return (
                          <>
                            {benefits.unique_value && (
                              <div className="p-3 bg-gradient-to-r from-purple-500/20 to-pink-500/20 rounded-lg border border-purple-500/30">
                                <p className="text-purple-300 text-xs mb-1">独自の価値提案</p>
                                <p className="text-white font-medium">{benefits.unique_value}</p>
                              </div>
                            )}
                            {benefits.main_benefits && benefits.main_benefits.length > 0 && (
                              <div>
                                <p className="text-slate-400 text-xs mb-2">主な特典</p>
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                                  {benefits.main_benefits.map((benefit, idx) => (
                                    <div key={idx} className="flex items-center gap-2 p-2 bg-white/5 rounded-lg">
                                      <CheckCircle className="w-4 h-4 text-green-400 flex-shrink-0" />
                                      <span className="text-slate-300 text-sm">{benefit}</span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                            {benefits.amenities && benefits.amenities.length > 0 && (
                              <div>
                                <p className="text-slate-400 text-xs mb-2">アメニティ</p>
                                <div className="flex flex-wrap gap-2">
                                  {benefits.amenities.map((amenity, idx) => (
                                    <span key={idx} className="px-2 py-1 bg-pink-500/20 text-pink-300 rounded-full text-sm">
                                      {amenity}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}
                          </>
                        );
                      })()}
                    </div>
                  </div>
                )}

                {/* 3C分析 */}
                {selectedPlan.strategy_3c && Object.keys(selectedPlan.strategy_3c).length > 0 && (
                  <div className="mb-6">
                    <div className="flex items-center gap-2 mb-3">
                      <Target className="w-5 h-5 text-orange-400" />
                      <h4 className="text-lg font-semibold text-white">3C分析</h4>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      {(() => {
                        const strategy = selectedPlan.strategy_3c as Strategy3C;
                        return (
                          <>
                            {strategy.customer && (
                              <div className="p-4 bg-white/5 rounded-lg border-l-4 border-blue-500">
                                <p className="text-blue-400 text-xs font-semibold mb-2">Customer（顧客）</p>
                                <p className="text-slate-300 text-sm">{strategy.customer}</p>
                              </div>
                            )}
                            {strategy.competitor && (
                              <div className="p-4 bg-white/5 rounded-lg border-l-4 border-red-500">
                                <p className="text-red-400 text-xs font-semibold mb-2">Competitor（競合）</p>
                                <p className="text-slate-300 text-sm">{strategy.competitor}</p>
                              </div>
                            )}
                            {strategy.company && (
                              <div className="p-4 bg-white/5 rounded-lg border-l-4 border-green-500">
                                <p className="text-green-400 text-xs font-semibold mb-2">Company（自社）</p>
                                <p className="text-slate-300 text-sm">{strategy.company}</p>
                              </div>
                            )}
                          </>
                        );
                      })()}
                    </div>
                  </div>
                )}

                {/* PEST分析 */}
                {selectedPlan.strategy_pest && Object.keys(selectedPlan.strategy_pest).length > 0 && (
                  <div className="mb-6">
                    <div className="flex items-center gap-2 mb-3">
                      <Globe className="w-5 h-5 text-cyan-400" />
                      <h4 className="text-lg font-semibold text-white">PEST分析</h4>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {(() => {
                        const pest = selectedPlan.strategy_pest as StrategyPEST;
                        return (
                          <>
                            {pest.political && (
                              <div className="p-4 bg-white/5 rounded-lg">
                                <p className="text-purple-400 text-xs font-semibold mb-2">Political（政治的要因）</p>
                                <p className="text-slate-300 text-sm">{pest.political}</p>
                              </div>
                            )}
                            {pest.economic && (
                              <div className="p-4 bg-white/5 rounded-lg">
                                <p className="text-green-400 text-xs font-semibold mb-2">Economic（経済的要因）</p>
                                <p className="text-slate-300 text-sm">{pest.economic}</p>
                              </div>
                            )}
                            {pest.social && (
                              <div className="p-4 bg-white/5 rounded-lg">
                                <p className="text-blue-400 text-xs font-semibold mb-2">Social（社会的要因）</p>
                                <p className="text-slate-300 text-sm">{pest.social}</p>
                              </div>
                            )}
                            {pest.technological && (
                              <div className="p-4 bg-white/5 rounded-lg">
                                <p className="text-cyan-400 text-xs font-semibold mb-2">Technological（技術的要因）</p>
                                <p className="text-slate-300 text-sm">{pest.technological}</p>
                              </div>
                            )}
                          </>
                        );
                      })()}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="glass-card p-8 flex flex-col items-center justify-center h-full min-h-[400px]">
                <FileText className="w-16 h-16 text-slate-500 mb-4" />
                <p className="text-slate-400">左側のリストからプランを選択してください</p>
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  );
}


