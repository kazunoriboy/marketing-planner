"use client";

import { useEffect, useState } from "react";
import { Instagram, Loader2, Wand2, FileCode, Image, MessageSquare } from "lucide-react";
import { useHotel } from "@/lib/hotel-context";
import { marketingApi, MarketingPlan, CreativeAsset } from "@/lib/api";

export default function ContentPage() {
  const { hotel, hotelId } = useHotel();
  const [plans, setPlans] = useState<MarketingPlan[]>([]);
  const [selectedPlan, setSelectedPlan] = useState<MarketingPlan | null>(null);
  const [assets, setAssets] = useState<CreativeAsset[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [generateOptions, setGenerateOptions] = useState({
    generate_lp: true,
    generate_images: true,
    generate_ad_copy: true,
  });

  useEffect(() => {
    async function loadData() {
      try {
        const plansData = await marketingApi.listPlans(hotelId);
        setPlans(plansData);
        // 承認済みプランがあれば選択
        const approvedPlan = plansData.find((p) => p.status === "approved");
        if (approvedPlan) {
          setSelectedPlan(approvedPlan);
        } else if (plansData.length > 0) {
          setSelectedPlan(plansData[0]);
        }
      } catch (error) {
        console.error("Failed to load plans:", error);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [hotelId]);

  useEffect(() => {
    async function loadAssets() {
      if (!selectedPlan) {
        setAssets([]);
        return;
      }
      try {
        const assetsData = await marketingApi.listCreativeAssets(hotelId, selectedPlan.id);
        setAssets(assetsData);
      } catch (error) {
        console.error("Failed to load assets:", error);
      }
    }
    loadAssets();
  }, [hotelId, selectedPlan]);

  const handleGenerate = async () => {
    if (!selectedPlan) return;
    setGenerating(true);
    try {
      const newAsset = await marketingApi.generateCreative(hotelId, {
        plan_id: selectedPlan.id,
        ...generateOptions,
      });
      setAssets([newAsset]);
    } catch (error) {
      console.error("Generation failed:", error);
    } finally {
      setGenerating(false);
    }
  };

  const currentAsset = assets[0];

  return (
    <section className="animate-fadeIn">
      <h2 className="text-3xl font-bold text-white mb-2">発信する</h2>
      <p className="text-slate-400 mb-8">
        {hotel.name}のマーケティングコンテンツをAIで生成します
      </p>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-purple-500"></div>
        </div>
      ) : plans.length === 0 ? (
        <div className="glass-card p-8 text-center">
          <Wand2 className="w-16 h-16 text-slate-500 mx-auto mb-4" />
          <p className="text-slate-400">
            コンテンツを生成するには、先に「プランを立てる」でマーケティングプランを作成してください。
          </p>
        </div>
      ) : (
        <>
          {/* プラン選択 & 生成オプション */}
          <div className="glass-card p-8 mb-8">
            <div className="flex items-center gap-3 mb-6">
              <Wand2 className="w-6 h-6 text-purple-400" />
              <h3 className="text-2xl font-bold text-white">コンテンツ生成</h3>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
              <div>
                <label className="block text-slate-300 text-sm mb-2">
                  マーケティングプラン
                </label>
                <select
                  value={selectedPlan?.id || ""}
                  onChange={(e) => {
                    const plan = plans.find((p) => p.id === Number(e.target.value));
                    setSelectedPlan(plan || null);
                  }}
                  className="w-full bg-white/5 border border-white/10 rounded-lg p-3 text-white"
                >
                  {plans.map((plan) => (
                    <option key={plan.id} value={plan.id}>
                      {plan.plan_name} {plan.status === "approved" ? "✓" : "(ドラフト)"}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-slate-300 text-sm mb-2">
                  生成するコンテンツ
                </label>
                <div className="space-y-2">
                  <label className="flex items-center gap-2 text-slate-300">
                    <input
                      type="checkbox"
                      checked={generateOptions.generate_lp}
                      onChange={(e) =>
                        setGenerateOptions((prev) => ({
                          ...prev,
                          generate_lp: e.target.checked,
                        }))
                      }
                      className="rounded"
                    />
                    ランディングページ
                  </label>
                  <label className="flex items-center gap-2 text-slate-300">
                    <input
                      type="checkbox"
                      checked={generateOptions.generate_images}
                      onChange={(e) =>
                        setGenerateOptions((prev) => ({
                          ...prev,
                          generate_images: e.target.checked,
                        }))
                      }
                      className="rounded"
                    />
                    広告画像プロンプト
                  </label>
                  <label className="flex items-center gap-2 text-slate-300">
                    <input
                      type="checkbox"
                      checked={generateOptions.generate_ad_copy}
                      onChange={(e) =>
                        setGenerateOptions((prev) => ({
                          ...prev,
                          generate_ad_copy: e.target.checked,
                        }))
                      }
                      className="rounded"
                    />
                    広告コピー
                  </label>
                </div>
              </div>
            </div>

            <button
              onClick={handleGenerate}
              disabled={generating || !selectedPlan}
              className="w-full bg-gradient-to-r from-purple-500 to-cyan-500 text-white py-4 rounded-lg hover:from-purple-600 hover:to-cyan-600 transition-all font-semibold disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {generating ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  生成中...
                </>
              ) : (
                <>
                  <Wand2 className="w-5 h-5" />
                  コンテンツを生成
                </>
              )}
            </button>
          </div>

          {/* 生成結果 */}
          {currentAsset && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              {/* ランディングページ */}
              {currentAsset.lp_source_code && (
                <div className="glass-card p-6">
                  <div className="flex items-center gap-3 mb-4">
                    <FileCode className="w-6 h-6 text-blue-400" />
                    <h4 className="text-xl font-bold text-white">ランディングページ</h4>
                  </div>
                  <div className="bg-white/5 rounded-lg p-4 max-h-96 overflow-auto">
                    <pre className="text-slate-300 text-xs whitespace-pre-wrap">
                      {currentAsset.lp_source_code}
                    </pre>
                  </div>
                </div>
              )}

              {/* 広告コピー */}
              {currentAsset.ad_copy && Object.keys(currentAsset.ad_copy).length > 0 && (
                <div className="glass-card p-6">
                  <div className="flex items-center gap-3 mb-4">
                    <MessageSquare className="w-6 h-6 text-green-400" />
                    <h4 className="text-xl font-bold text-white">広告コピー</h4>
                  </div>
                  <div className="space-y-4">
                    {Object.entries(currentAsset.ad_copy).map(([key, value]) => (
                      <div key={key} className="p-4 bg-white/5 rounded-lg">
                        <p className="text-sm text-slate-400 mb-1">{key}</p>
                        <p className="text-slate-300">{String(value)}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 画像プロンプト */}
              {currentAsset.ad_image_urls && Object.keys(currentAsset.ad_image_urls).length > 0 && (
                <div className="glass-card p-6 lg:col-span-2">
                  <div className="flex items-center gap-3 mb-4">
                    <Image className="w-6 h-6 text-orange-400" />
                    <h4 className="text-xl font-bold text-white">画像生成プロンプト</h4>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {Object.entries(currentAsset.ad_image_urls).map(([key, value]) => (
                      <div key={key} className="p-4 bg-white/5 rounded-lg">
                        <p className="text-sm text-slate-400 mb-1">{key}</p>
                        <p className="text-slate-300 text-sm">{String(value)}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* SNS投稿ジェネレーター（モック） */}
          <div className="glass-card p-8 mt-8">
            <div className="flex items-center gap-3 mb-6">
              <Instagram className="w-6 h-6 text-pink-400" />
              <h3 className="text-2xl font-bold text-white">SNS投稿ジェネレーター</h3>
            </div>

            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <select className="bg-white/5 border border-white/10 rounded-lg p-3 text-slate-200 focus:outline-none focus:border-purple-500">
                  <option>プラットフォームを選択</option>
                  <option>Instagram</option>
                  <option>Facebook</option>
                  <option>Twitter</option>
                </select>
                <select className="bg-white/5 border border-white/10 rounded-lg p-3 text-slate-200 focus:outline-none focus:border-purple-500">
                  <option>投稿タイプを選択</option>
                  <option>温泉紹介</option>
                  <option>料理紹介</option>
                  <option>イベント告知</option>
                </select>
              </div>

              <button className="w-full bg-gradient-to-r from-purple-500 to-cyan-500 text-white py-4 rounded-lg hover:from-purple-600 hover:to-cyan-600 transition-all font-semibold">
                SNS投稿を作成
              </button>

              <div className="bg-white/5 border border-white/10 rounded-lg p-6">
                <h4 className="text-lg font-semibold text-white mb-3">生成された投稿</h4>
                <p className="text-slate-300 leading-relaxed">
                  🌸 春の訪れとともに、{hotel.name}も新緑の季節を迎えました。
                  <br />
                  <br />
                  #温泉 #旅館 #春 #リフレッシュ #癒し
                </p>
              </div>
            </div>
          </div>
        </>
      )}
    </section>
  );
}
