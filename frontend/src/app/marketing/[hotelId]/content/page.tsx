"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { Instagram, Loader2, Wand2, FileCode, Image, MessageSquare, CheckCircle, AlertCircle, Eye, ExternalLink, X, Link2 } from "lucide-react";
import { useHotel } from "@/lib/hotel-context";
import { marketingApi, facilityApi, MarketingPlan, CreativeAsset, HotelResponse } from "@/lib/api";
import Link from "next/link";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function ContentPage() {
  const { hotel: initialHotel, hotelId } = useHotel();
  const [hotel, setHotel] = useState<HotelResponse>(initialHotel);
  const [allPlans, setAllPlans] = useState<MarketingPlan[]>([]);
  const [approvedPlans, setApprovedPlans] = useState<MarketingPlan[]>([]);
  const [selectedPlan, setSelectedPlan] = useState<MarketingPlan | null>(null);
  const [assets, setAssets] = useState<CreativeAsset[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [generateOptions, setGenerateOptions] = useState({
    generate_lp: true,
    generate_images: true,
    generate_ad_copy: true,
  });
  
  // プレビュー関連のstate
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [savingLp, setSavingLp] = useState(false);
  
  // CV URL設定モーダル関連のstate
  const [showCvUrlModal, setShowCvUrlModal] = useState(false);
  const [cvUrlInput, setCvUrlInput] = useState("");
  const [savingCvUrl, setSavingCvUrl] = useState(false);
  const [cvUrlError, setCvUrlError] = useState("");

  useEffect(() => {
    async function loadData() {
      try {
        const plansData = await marketingApi.listPlans(hotelId);
        setAllPlans(plansData);
        // 承認済みプランのみをフィルタリング
        const approved = plansData.filter((p) => p.status === "approved");
        setApprovedPlans(approved);
        // 承認済みプランがあれば最初のものを選択
        if (approved.length > 0) {
          setSelectedPlan(approved[0]);
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
    
    // LP生成時にCV URLが必須かチェック
    if (generateOptions.generate_lp && !hotel.cv_url) {
      setShowCvUrlModal(true);
      setCvUrlInput("");
      setCvUrlError("");
      return;
    }
    
    await executeGenerate();
  };

  const executeGenerate = async () => {
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

  const handleSaveCvUrl = async () => {
    if (!cvUrlInput.trim()) {
      setCvUrlError("CV用URLを入力してください");
      return;
    }
    
    // 簡易的なURL検証
    try {
      new URL(cvUrlInput);
    } catch {
      setCvUrlError("有効なURLを入力してください");
      return;
    }
    
    setSavingCvUrl(true);
    setCvUrlError("");
    
    try {
      const updatedHotel = await facilityApi.updateHotel(hotelId, {
        cv_url: cvUrlInput,
      });
      setHotel(updatedHotel);
      setShowCvUrlModal(false);
      
      // CV URL保存後、自動的にコンテンツ生成を開始
      await executeGenerate();
    } catch (error) {
      console.error("Failed to save CV URL:", error);
      setCvUrlError("CV URLの保存に失敗しました");
    } finally {
      setSavingCvUrl(false);
    }
  };

  // LPプレビューを開く
  const handleOpenPreview = async () => {
    const asset = assets[0];
    if (!asset || !asset.lp_source_code) return;
    
    // 既にプレビューURLがある場合はそれを使用
    if (asset.lp_preview_url) {
      setPreviewUrl(`${API_BASE_URL}${asset.lp_preview_url}`);
      setShowPreviewModal(true);
      return;
    }
    
    // プレビューURLがない場合は保存APIを呼び出す
    setSavingLp(true);
    try {
      const result = await marketingApi.saveLpToFile(hotelId, asset.id);
      const fullUrl = `${API_BASE_URL}${result.preview_url}`;
      setPreviewUrl(fullUrl);
      setShowPreviewModal(true);
      // アセットを更新
      setAssets([{ ...asset, lp_preview_url: result.preview_url }]);
    } catch (error) {
      console.error("Failed to save LP:", error);
      alert("LPの保存に失敗しました");
    } finally {
      setSavingLp(false);
    }
  };

  // 新しいタブでプレビューを開く
  const handleOpenInNewTab = async () => {
    const asset = assets[0];
    if (!asset || !asset.lp_source_code) return;
    
    // 既にプレビューURLがある場合はそれを使用
    if (asset.lp_preview_url) {
      window.open(`${API_BASE_URL}${asset.lp_preview_url}`, "_blank");
      return;
    }
    
    // プレビューURLがない場合は保存APIを呼び出す
    setSavingLp(true);
    try {
      const result = await marketingApi.saveLpToFile(hotelId, asset.id);
      const fullUrl = `${API_BASE_URL}${result.preview_url}`;
      window.open(fullUrl, "_blank");
      // アセットを更新
      setAssets([{ ...asset, lp_preview_url: result.preview_url }]);
    } catch (error) {
      console.error("Failed to save LP:", error);
      alert("LPの保存に失敗しました");
    } finally {
      setSavingLp(false);
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
      ) : allPlans.length === 0 ? (
        <div className="glass-card p-8 text-center">
          <Wand2 className="w-16 h-16 text-slate-500 mx-auto mb-4" />
          <h3 className="text-xl font-bold text-white mb-3">プランがありません</h3>
          <p className="text-slate-400 mb-6">
            コンテンツを生成するには、先にマーケティングプランを作成してください。
          </p>
          <Link
            href={`/marketing/${hotelId}/planner`}
            className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-purple-500 to-cyan-500 text-white rounded-lg hover:from-purple-600 hover:to-cyan-600 transition-all font-semibold"
          >
            <Wand2 className="w-5 h-5" />
            プランを作成する
          </Link>
        </div>
      ) : approvedPlans.length === 0 ? (
        <div className="glass-card p-8 text-center">
          <AlertCircle className="w-16 h-16 text-yellow-500 mx-auto mb-4" />
          <h3 className="text-xl font-bold text-white mb-3">承認済みのプランがありません</h3>
          <p className="text-slate-400 mb-4">
            コンテンツを生成するには、マーケティングプランを承認する必要があります。
          </p>
          <div className="bg-white/5 rounded-lg p-4 mb-6 text-left max-w-md mx-auto">
            <p className="text-sm text-slate-300 mb-2">
              <span className="text-yellow-400 font-semibold">{allPlans.length}件</span>のドラフトプランがあります
            </p>
            <p className="text-xs text-slate-500">
              「プランを立てる」ページでプランを確認し、承認してください。
            </p>
          </div>
          <Link
            href={`/marketing/${hotelId}/planner`}
            className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-purple-500 to-cyan-500 text-white rounded-lg hover:from-purple-600 hover:to-cyan-600 transition-all font-semibold"
          >
            <CheckCircle className="w-5 h-5" />
            プランを承認する
          </Link>
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
                  マーケティングプラン（承認済みのみ）
                </label>
                <select
                  value={selectedPlan?.id || ""}
                  onChange={(e) => {
                    const plan = approvedPlans.find((p) => p.id === Number(e.target.value));
                    setSelectedPlan(plan || null);
                  }}
                  className="w-full bg-white/5 border border-white/10 rounded-lg p-3 text-white"
                >
                  {approvedPlans.map((plan) => (
                    <option key={plan.id} value={plan.id}>
                      ✓ {plan.plan_name}
                    </option>
                  ))}
                </select>
                <p className="text-xs text-slate-500 mt-1">
                  {approvedPlans.length}件の承認済みプランから選択
                </p>
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
                    {generateOptions.generate_lp && !hotel.cv_url && (
                      <span className="text-xs text-yellow-400 ml-1">（要CV URL設定）</span>
                    )}
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
                    広告画像
                  </label>
                </div>
              </div>
            </div>

            {/* CV URL設定状況 */}
            {generateOptions.generate_lp && (
              <div className={`mb-6 p-4 rounded-lg border ${hotel.cv_url ? 'bg-green-500/10 border-green-500/30' : 'bg-yellow-500/10 border-yellow-500/30'}`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Link2 className={`w-4 h-4 ${hotel.cv_url ? 'text-green-400' : 'text-yellow-400'}`} />
                    <span className={`text-sm font-medium ${hotel.cv_url ? 'text-green-400' : 'text-yellow-400'}`}>
                      {hotel.cv_url ? 'CV URL設定済み' : 'CV URL未設定'}
                    </span>
                  </div>
                  {hotel.cv_url ? (
                    <button
                      onClick={() => {
                        setCvUrlInput(hotel.cv_url || "");
                        setShowCvUrlModal(true);
                        setCvUrlError("");
                      }}
                      className="text-xs text-slate-400 hover:text-white transition-colors"
                    >
                      変更する
                    </button>
                  ) : (
                    <button
                      onClick={() => {
                        setCvUrlInput("");
                        setShowCvUrlModal(true);
                        setCvUrlError("");
                      }}
                      className="text-xs text-yellow-400 hover:text-yellow-300 transition-colors"
                    >
                      設定する
                    </button>
                  )}
                </div>
                {hotel.cv_url && (
                  <p className="text-xs text-slate-400 mt-2 truncate">
                    {hotel.cv_url}
                  </p>
                )}
              </div>
            )}

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
                <div className="glass-card p-6 lg:col-span-2">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <FileCode className="w-6 h-6 text-blue-400" />
                      <h4 className="text-xl font-bold text-white">ランディングページ</h4>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={handleOpenPreview}
                        disabled={savingLp}
                        className="flex items-center gap-2 px-4 py-2 bg-blue-500/20 text-blue-400 rounded-lg hover:bg-blue-500/30 transition-all text-sm disabled:opacity-50"
                      >
                        {savingLp ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <Eye className="w-4 h-4" />
                        )}
                        プレビュー
                      </button>
                      <button
                        onClick={handleOpenInNewTab}
                        disabled={savingLp}
                        className="flex items-center gap-2 px-4 py-2 bg-purple-500/20 text-purple-400 rounded-lg hover:bg-purple-500/30 transition-all text-sm disabled:opacity-50"
                      >
                        <ExternalLink className="w-4 h-4" />
                        新しいタブで開く
                      </button>
                    </div>
                  </div>
                  
                  {/* LP用画像セクション */}
                  {currentAsset.lp_image_urls && Object.keys(currentAsset.lp_image_urls).length > 0 && (
                    <div className="mb-4">
                      <p className="text-sm text-slate-400 mb-3">LP用画像</p>
                      <div className="grid grid-cols-3 gap-3">
                        {Object.entries(currentAsset.lp_image_urls).map(([key, value]) => {
                          const imageValue = value as Record<string, unknown> | string | null;
                          const isError = typeof imageValue === "object" && imageValue !== null && "error" in imageValue;
                          
                          return (
                            <div key={key} className="relative">
                              <p className="text-xs text-slate-500 mb-1">{key}</p>
                              {typeof imageValue === "string" && imageValue.startsWith("/static/") ? (
                                <div className="relative aspect-video rounded-lg overflow-hidden bg-slate-800">
                                  <img
                                    src={`${API_BASE_URL}${imageValue}`}
                                    alt={key}
                                    className="w-full h-full object-cover"
                                  />
                                </div>
                              ) : isError ? (
                                <div className="aspect-video rounded-lg bg-red-500/10 border border-red-500/30 flex items-center justify-center">
                                  <span className="text-red-400 text-xs">生成失敗</span>
                                </div>
                              ) : (
                                <div className="aspect-video rounded-lg bg-slate-700 flex items-center justify-center">
                                  <span className="text-slate-500 text-xs">未生成</span>
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                  
                  <div className="bg-white/5 rounded-lg p-4 max-h-64 overflow-auto">
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
                        <p className="text-sm text-slate-400 mb-2 font-medium">{key}</p>
                        {typeof value === "object" && value !== null ? (
                          <div className="space-y-2">
                            {Object.entries(value as Record<string, unknown>).map(([subKey, subValue]) => (
                              <div key={subKey}>
                                <span className="text-xs text-slate-500">{subKey}: </span>
                                {Array.isArray(subValue) ? (
                                  <span className="text-slate-300">{subValue.join(" ")}</span>
                                ) : (
                                  <span className="text-slate-300">{String(subValue)}</span>
                                )}
                              </div>
                            ))}
                          </div>
                        ) : (
                          <p className="text-slate-300">{String(value)}</p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 広告用画像 */}
              {currentAsset.ad_image_urls && Object.keys(currentAsset.ad_image_urls).length > 0 && (
                <div className="glass-card p-6 lg:col-span-2">
                  <div className="flex items-center gap-3 mb-4">
                    <Image className="w-6 h-6 text-orange-400" />
                    <h4 className="text-xl font-bold text-white">広告用画像</h4>
                    <span className="text-xs text-slate-500">（ディスプレイ広告・SNS広告用）</span>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {Object.entries(currentAsset.ad_image_urls).map(([key, value]) => {
                      const imageValue = value as Record<string, unknown> | string | null;
                      const isError = typeof imageValue === "object" && imageValue !== null && "error" in imageValue;
                      const isQuotaError = isError && imageValue.error === "quota_exceeded";
                      
                      return (
                        <div key={key} className="p-4 bg-white/5 rounded-lg">
                          <p className="text-sm text-slate-400 mb-3 font-medium">{key}</p>
                          {typeof imageValue === "string" && imageValue.startsWith("/static/") ? (
                            // 画像URLの場合は実際の画像を表示
                            <div className="relative aspect-video rounded-lg overflow-hidden bg-slate-800">
                              <img
                                src={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}${imageValue}`}
                                alt={key}
                                className="w-full h-full object-cover"
                              />
                            </div>
                          ) : isQuotaError ? (
                            // APIクォータエラーの場合
                            <div className="p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
                              <p className="text-yellow-400 text-sm font-medium mb-1">⚠️ API制限エラー</p>
                              <p className="text-yellow-300/80 text-xs">
                                {String((imageValue as Record<string, unknown>).message || "API利用制限に達しました。しばらく待ってから再度お試しください。")}
                              </p>
                            </div>
                          ) : isError ? (
                            // その他のエラーの場合
                            <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
                              <p className="text-red-400 text-sm font-medium mb-1">❌ 生成エラー</p>
                              <p className="text-red-300/80 text-xs">
                                {String((imageValue as Record<string, unknown>).message || "画像生成に失敗しました")}
                              </p>
                            </div>
                          ) : imageValue ? (
                            <p className="text-slate-300 text-sm">{String(imageValue)}</p>
                          ) : (
                            <p className="text-slate-500 text-sm italic">生成に失敗しました</p>
                          )}
                        </div>
                      );
                    })}
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

      {/* LPプレビューモーダル - Portalで画面全体に表示 */}
      {showPreviewModal && previewUrl && typeof document !== "undefined" && createPortal(
        <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="relative w-full max-w-6xl h-[90vh] bg-slate-900 rounded-2xl overflow-hidden shadow-2xl border border-white/10">
            {/* ヘッダー */}
            <div className="flex items-center justify-between px-6 py-4 bg-slate-800/50 border-b border-white/10">
              <div className="flex items-center gap-3">
                <Eye className="w-5 h-5 text-blue-400" />
                <h3 className="text-lg font-semibold text-white">LPプレビュー</h3>
              </div>
              <div className="flex items-center gap-3">
                <a
                  href={previewUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 px-4 py-2 bg-purple-500/20 text-purple-400 rounded-lg hover:bg-purple-500/30 transition-all text-sm"
                >
                  <ExternalLink className="w-4 h-4" />
                  新しいタブで開く
                </a>
                <button
                  onClick={() => setShowPreviewModal(false)}
                  className="p-2 text-slate-400 hover:text-white hover:bg-white/10 rounded-lg transition-all"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>
            
            {/* iframe プレビュー */}
            <div className="w-full h-[calc(100%-72px)] bg-white">
              <iframe
                src={previewUrl}
                className="w-full h-full border-0"
                title="LP Preview"
              />
            </div>
          </div>
        </div>,
        document.body
      )}

      {/* CV URL設定モーダル - Portalで画面全体に表示 */}
      {showCvUrlModal && typeof document !== "undefined" && createPortal(
        <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="relative w-full max-w-lg bg-slate-900 rounded-2xl overflow-hidden shadow-2xl border border-white/10">
            {/* ヘッダー */}
            <div className="flex items-center justify-between px-5 py-3 bg-slate-800/50 border-b border-white/10">
              <div className="flex items-center gap-2">
                <Link2 className="w-5 h-5 text-purple-400" />
                <h3 className="text-base font-semibold text-white">CV用URLの設定</h3>
              </div>
              <button
                onClick={() => setShowCvUrlModal(false)}
                className="p-1.5 text-slate-400 hover:text-white hover:bg-white/10 rounded-lg transition-all"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            
            {/* コンテンツ */}
            <div className="p-5">
              <div className="mb-4">
                <div className="flex items-center gap-2 mb-2 text-yellow-400">
                  <AlertCircle className="w-4 h-4" />
                  <span className="text-sm font-medium">CV用URLが設定されていません</span>
                </div>
                <p className="text-slate-400 text-xs leading-relaxed">
                  LP生成には予約ページへのリンク（CV用URL）が必要です。じゃらん、楽天トラベル、公式サイトなどのURLを入力してください。
                </p>
              </div>
              
              <div className="mb-4">
                <label className="block text-slate-300 text-sm mb-1.5">
                  CV用URL（予約ページのリンク）
                </label>
                <input
                  type="url"
                  value={cvUrlInput}
                  onChange={(e) => setCvUrlInput(e.target.value)}
                  placeholder="https://www.jalan.net/yad123456/"
                  className="w-full bg-white/5 border border-white/10 rounded-lg p-2.5 text-white placeholder-slate-500 focus:outline-none focus:border-purple-500 text-sm"
                />
                {cvUrlError && (
                  <p className="text-red-400 text-xs mt-1.5">{cvUrlError}</p>
                )}
              </div>
              
              <div className="text-xs text-slate-500 mb-4">
                <p className="mb-1">例: jalan.net/yad... / travel.rakuten.co.jp/HOTEL/...</p>
              </div>
              
              <div className="flex gap-2">
                <button
                  onClick={() => setShowCvUrlModal(false)}
                  className="flex-1 px-3 py-2.5 bg-white/5 text-slate-300 rounded-lg hover:bg-white/10 transition-all font-medium text-sm"
                >
                  キャンセル
                </button>
                <button
                  onClick={handleSaveCvUrl}
                  disabled={savingCvUrl}
                  className="flex-1 px-3 py-2.5 bg-gradient-to-r from-purple-500 to-cyan-500 text-white rounded-lg hover:from-purple-600 hover:to-cyan-600 transition-all font-medium disabled:opacity-50 flex items-center justify-center gap-2 text-sm"
                >
                  {savingCvUrl ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      保存中...
                    </>
                  ) : (
                    <>
                      <CheckCircle className="w-4 h-4" />
                      保存して生成
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>,
        document.body
      )}
    </section>
  );
}


