"use client";

import { useEffect, useState, useRef } from "react";
import { createPortal } from "react-dom";
import { Instagram, Loader2, Wand2, FileCode, Image, MessageSquare, CheckCircle, AlertCircle, Eye, ExternalLink, X, Link2, Upload } from "lucide-react";
import { useHotel } from "@/lib/hotel-context";
import { marketingApi, facilityApi, MarketingPlan, CreativeAsset, HotelResponse, SNSPostResponse } from "@/lib/api";
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
    generate_ota_text: true,  // OTAテキスト（じゃらん、楽天トラベル向け）
    lp_theme: "auto",
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
  
  // LP画像アップロード関連のstate
  const [uploadingImage, setUploadingImage] = useState<string | null>(null);
  const fileInputRefs = useRef<Record<string, HTMLInputElement | null>>({});
  
  // 画像アップロード確認モーダル関連のstate
  const [pendingImageUpload, setPendingImageUpload] = useState<{
    imageType: string;
    file: File;
    previewUrl: string;
  } | null>(null);
  
  // 画像モーダル関連のstate
  const [showImageModal, setShowImageModal] = useState(false);
  const [modalImageUrl, setModalImageUrl] = useState<string | null>(null);
  const [modalImageTitle, setModalImageTitle] = useState<string>("");
  
  // トースト通知のstate
  const [toast, setToast] = useState<string | null>(null);
  const toastTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const showToast = (message: string) => {
    if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    setToast(message);
    toastTimerRef.current = setTimeout(() => setToast(null), 2000);
  };

  // SNS投稿ジェネレーター関連のstate
  const [snsPlatform, setSnsPlatform] = useState<string>("");
  const [snsPostType, setSnsPostType] = useState<string>("");
  const [snsDescription, setSnsDescription] = useState<string>("");
  const [generatingSns, setGeneratingSns] = useState(false);
  const [snsPost, setSnsPost] = useState<SNSPostResponse | null>(null);
  const [snsError, setSnsError] = useState<string>("");

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

  // ESCキーで画像モーダルを閉じる
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && showImageModal) {
        setShowImageModal(false);
      }
    };
    
    if (showImageModal) {
      document.addEventListener("keydown", handleKeyDown);
      return () => document.removeEventListener("keydown", handleKeyDown);
    }
  }, [showImageModal]);

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

  // LP画像をアップロード
  const handleImageUpload = async (
    assetId: number,
    imageType: string,
    file: File
  ) => {
    setUploadingImage(imageType);
    try {
      const result = await marketingApi.uploadLpImage(hotelId, assetId, imageType, file);
      
      // アセットの画像URLを更新
      setAssets(prevAssets => 
        prevAssets.map(asset => 
          asset.id === assetId 
            ? { ...asset, lp_image_urls: result.lp_image_urls }
            : asset
        )
      );
    } catch (error) {
      console.error("Image upload failed:", error);
      alert("画像のアップロードに失敗しました");
    } finally {
      setUploadingImage(null);
    }
  };

  // 画像アップロードを確定する
  const handleConfirmImageUpload = async () => {
    if (!pendingImageUpload || !currentAsset) return;
    
    const { imageType, file, previewUrl } = pendingImageUpload;
    
    // プレビューURLを解放
    URL.revokeObjectURL(previewUrl);
    
    // モーダルを閉じる
    setPendingImageUpload(null);
    
    // アップロードを実行
    await handleImageUpload(currentAsset.id, imageType, file);
  };

  // 画像アップロードをキャンセルする
  const handleCancelImageUpload = () => {
    if (pendingImageUpload) {
      // プレビューURLを解放
      URL.revokeObjectURL(pendingImageUpload.previewUrl);
      setPendingImageUpload(null);
    }
  };

  // ファイル選択ダイアログを開く
  const triggerFileInput = (imageType: string) => {
    const input = fileInputRefs.current[imageType];
    if (input) {
      input.click();
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
                  className="w-full bg-slate-800 border border-white/10 rounded-lg p-3 text-white [&>option]:bg-slate-800 [&>option]:text-white"
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
                  <label className="flex items-center gap-2 text-slate-300">
                    <input
                      type="checkbox"
                      checked={generateOptions.generate_ota_text}
                      onChange={(e) =>
                        setGenerateOptions((prev) => ({
                          ...prev,
                          generate_ota_text: e.target.checked,
                        }))
                      }
                      className="rounded"
                    />
                    OTAテキスト
                    <span className="text-xs text-slate-500 ml-1">（じゃらん・楽天）</span>
                  </label>
                  {/* LP テーマ選択 */}
                  {generateOptions.generate_lp && (
                    <div className="mt-3">
                      <label className="text-slate-400 text-xs mb-1 block">LP デザインテーマ</label>
                      <select
                        value={generateOptions.lp_theme}
                        onChange={(e) =>
                          setGenerateOptions((prev) => ({
                            ...prev,
                            lp_theme: e.target.value,
                          }))
                        }
                        className="bg-slate-700 border border-slate-600 text-slate-200 text-sm rounded px-3 py-1.5 w-full"
                      >
                        <option value="auto">自動（AIが選択）</option>
                        <option value="luxury_japanese">高級和風</option>
                        <option value="modern_resort">モダンリゾート</option>
                        <option value="natural_retreat">ナチュラルリトリート</option>
                        <option value="urban_boutique">アーバンブティック</option>
                      </select>
                    </div>
                  )}
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
                      <p className="text-sm text-slate-400 mb-3">LP用画像（クリックで差し替え可能）</p>
                      <div className="grid grid-cols-3 gap-3">
                        {Object.entries(currentAsset.lp_image_urls).map(([key, value]) => {
                          const imageValue = value as Record<string, unknown> | string | null;
                          const isError = typeof imageValue === "object" && imageValue !== null && "error" in imageValue;
                          const isValidType = ["hero", "feature", "feature1", "feature2", "feature3", "surrounding", "ambiance"].includes(key);
                          const isUploading = uploadingImage === key;
                          
                          return (
                            <div key={key} className="relative group">
                              <p className="text-xs text-slate-500 mb-1 flex items-center gap-1">
                                {key}
                                {isValidType && (
                                  <span className="text-slate-600">（差し替え可）</span>
                                )}
                              </p>
                              
                              {/* 隠しファイル入力 */}
                              {isValidType && (
                                <input
                                  type="file"
                                  ref={(el) => { fileInputRefs.current[key] = el; }}
                                  accept="image/jpeg,image/png,image/webp"
                                  className="hidden"
                                  onChange={(e) => {
                                    const file = e.target.files?.[0];
                                    if (file) {
                                      // ファイルを選択したらプレビューを表示（即座にアップロードしない）
                                      const previewUrl = URL.createObjectURL(file);
                                      setPendingImageUpload({
                                        imageType: key,
                                        file,
                                        previewUrl,
                                      });
                                    }
                                    e.target.value = "";
                                  }}
                                />
                              )}
                              
                              {typeof imageValue === "string" && imageValue.startsWith("/static/") ? (
                                <div 
                                  className={`relative aspect-video rounded-lg overflow-hidden bg-slate-800 ${isValidType && !isUploading ? 'cursor-pointer' : ''}`}
                                  onClick={() => isValidType && !isUploading && triggerFileInput(key)}
                                >
                                  <img
                                    src={`${API_BASE_URL}${imageValue}`}
                                    alt={key}
                                    className="w-full h-full object-cover"
                                  />
                                  {/* アップロードオーバーレイ */}
                                  {isValidType && !isUploading && (
                                    <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                                      <div className="text-center">
                                        <Upload className="w-6 h-6 text-white mx-auto mb-1" />
                                        <span className="text-white text-xs">画像を差し替え</span>
                                      </div>
                                    </div>
                                  )}
                                  {/* アップロード中 */}
                                  {isUploading && (
                                    <div className="absolute inset-0 bg-black/70 flex items-center justify-center">
                                      <Loader2 className="w-6 h-6 text-white animate-spin" />
                                    </div>
                                  )}
                                </div>
                              ) : isError ? (
                                <div 
                                  className={`aspect-video rounded-lg bg-red-500/10 border border-red-500/30 flex items-center justify-center ${isValidType && !isUploading ? 'cursor-pointer hover:bg-red-500/20' : ''}`}
                                  onClick={() => isValidType && !isUploading && triggerFileInput(key)}
                                >
                                  {isUploading ? (
                                    <Loader2 className="w-6 h-6 text-red-400 animate-spin" />
                                  ) : (
                                    <div className="text-center">
                                      <Upload className="w-5 h-5 text-red-400 mx-auto mb-1" />
                                      <span className="text-red-400 text-xs">画像をアップロード</span>
                                    </div>
                                  )}
                                </div>
                              ) : (
                                <div 
                                  className={`aspect-video rounded-lg bg-slate-700 flex items-center justify-center ${isValidType && !isUploading ? 'cursor-pointer hover:bg-slate-600' : ''}`}
                                  onClick={() => isValidType && !isUploading && triggerFileInput(key)}
                                >
                                  {isUploading ? (
                                    <Loader2 className="w-6 h-6 text-slate-400 animate-spin" />
                                  ) : (
                                    <div className="text-center">
                                      <Upload className="w-5 h-5 text-slate-400 mx-auto mb-1" />
                                      <span className="text-slate-500 text-xs">画像をアップロード</span>
                                    </div>
                                  )}
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
              {currentAsset.ad_copy && (currentAsset.ad_copy.google_ads || currentAsset.ad_copy.facebook_ads || currentAsset.ad_copy.instagram_ads) && (() => {
                /** 全角換算の文字数（半角=0.5、全角=1） */
                const fullWidthLen = (s: string) =>
                  [...s].reduce((acc, c) => acc + (c.charCodeAt(0) > 0x7F ? 1 : 0.5), 0);

                const copyText = (text: string) => {
                  navigator.clipboard.writeText(text);
                  showToast("コピーしました");
                };

                const LenBadge = ({ count, limit }: { count: number; limit: number }) => (
                  <span className={`text-xs px-1.5 py-0.5 rounded font-mono flex-shrink-0 ${
                    count > limit ? "bg-red-500/20 text-red-400" : "bg-white/10 text-slate-500"
                  }`}>
                    {count}/{limit}
                  </span>
                );

                const { google_ads, facebook_ads, instagram_ads } = currentAsset.ad_copy;

                return (
                  <div className="glass-card p-6 lg:col-span-2">
                    <div className="flex items-center gap-3 mb-6">
                      <MessageSquare className="w-6 h-6 text-green-400" />
                      <h4 className="text-xl font-bold text-white">広告コピー</h4>
                    </div>
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 items-start">

                      {/* Google 検索広告（RSA） */}
                      {google_ads && (
                        <div className="bg-gradient-to-br from-blue-900/30 to-blue-800/10 border border-blue-700/30 rounded-xl p-5">
                          <div className="flex items-center justify-between mb-4">
                            <h5 className="text-base font-semibold text-blue-300">Google 検索広告（RSA）</h5>
                            <button
                              onClick={() => {
                                const all = [
                                  ...(google_ads.headlines || []),
                                  ...(google_ads.descriptions || [])
                                ].join("\t");
                                copyText(all);
                              }}
                              className="text-xs px-3 py-1 rounded bg-blue-700/30 text-blue-300 hover:bg-blue-700/50 transition-colors"
                            >
                              全コピー
                            </button>
                          </div>
                          {/* 見出し */}
                          {google_ads.headlines && google_ads.headlines.length > 0 && (
                            <div className="mb-4">
                              <p className="text-xs text-slate-400 mb-2">見出し（上限: 全角15文字）</p>
                              <div className="space-y-2">
                                {google_ads.headlines.map((h, i) => (
                                  <div key={i} className="flex items-center gap-2">
                                    <span className="text-xs text-slate-500 w-4 flex-shrink-0">#{i + 1}</span>
                                    <span className="text-slate-200 text-sm flex-1">{h}</span>
                                    <LenBadge count={fullWidthLen(h)} limit={15} />
                                    <button onClick={() => copyText(h)} className="text-slate-500 hover:text-slate-300 flex-shrink-0 text-sm">📋</button>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                          {/* 説明文 */}
                          {google_ads.descriptions && google_ads.descriptions.length > 0 && (
                            <div className="mb-4">
                              <p className="text-xs text-slate-400 mb-2">説明文（上限: 全角45文字）</p>
                              <div className="space-y-2">
                                {google_ads.descriptions.map((d, i) => (
                                  <div key={i} className="flex items-start gap-2">
                                    <span className="text-xs text-slate-500 w-4 flex-shrink-0 mt-0.5">#{i + 1}</span>
                                    <span className="text-slate-200 text-sm flex-1">{d}</span>
                                    <LenBadge count={fullWidthLen(d)} limit={45} />
                                    <button onClick={() => copyText(d)} className="text-slate-500 hover:text-slate-300 flex-shrink-0 text-sm">📋</button>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                          {/* Path */}
                          {(google_ads.path1 || google_ads.path2) && (
                            <div>
                              <p className="text-xs text-slate-400 mb-2">表示パス（各上限15文字）</p>
                              <div className="space-y-1">
                                {google_ads.path1 && (
                                  <div className="flex items-center gap-2">
                                    <span className="text-xs text-slate-500 w-10 flex-shrink-0">path1</span>
                                    <span className="text-slate-200 text-sm flex-1">{google_ads.path1}</span>
                                    <LenBadge count={fullWidthLen(google_ads.path1)} limit={15} />
                                    <button onClick={() => copyText(google_ads.path1!)} className="text-slate-500 hover:text-slate-300 flex-shrink-0 text-sm">📋</button>
                                  </div>
                                )}
                                {google_ads.path2 && (
                                  <div className="flex items-center gap-2">
                                    <span className="text-xs text-slate-500 w-10 flex-shrink-0">path2</span>
                                    <span className="text-slate-200 text-sm flex-1">{google_ads.path2}</span>
                                    <LenBadge count={fullWidthLen(google_ads.path2)} limit={15} />
                                    <button onClick={() => copyText(google_ads.path2!)} className="text-slate-500 hover:text-slate-300 flex-shrink-0 text-sm">📋</button>
                                  </div>
                                )}
                              </div>
                            </div>
                          )}
                        </div>
                      )}

                      {/* Facebook 広告 */}
                      {facebook_ads && (
                        <div className="bg-gradient-to-br from-indigo-900/30 to-indigo-800/10 border border-indigo-700/30 rounded-xl p-5">
                          <div className="flex items-center justify-between mb-4">
                            <h5 className="text-base font-semibold text-indigo-300">Facebook 広告</h5>
                            <button
                              onClick={() => {
                                const sections = (facebook_ads.primary_texts || []).map((pt, i) =>
                                  `【案${i + 1}】\nPrimary Text: ${pt}\nHeadline: ${(facebook_ads.headlines || [])[i] || ""}\nDescription: ${(facebook_ads.descriptions || [])[i] || ""}`
                                );
                                copyText(sections.join("\n\n"));
                              }}
                              className="text-xs px-3 py-1 rounded bg-indigo-700/30 text-indigo-300 hover:bg-indigo-700/50 transition-colors"
                            >
                              全コピー
                            </button>
                          </div>
                          {/* Primary Texts */}
                          {facebook_ads.primary_texts && facebook_ads.primary_texts.length > 0 && (
                            <div className="mb-4">
                              <p className="text-xs text-slate-400 mb-2">Primary Text（冒頭125文字に重要訴求を集約）</p>
                              <div className="space-y-3">
                                {facebook_ads.primary_texts.map((pt, i) => (
                                  <div key={i} className="bg-white/5 rounded-lg p-3">
                                    <div className="flex items-center justify-between mb-1">
                                      <span className="text-xs text-slate-400">案{i + 1}</span>
                                      <div className="flex items-center gap-2">
                                        <LenBadge count={pt.length} limit={125} />
                                        <button onClick={() => copyText(pt)} className="text-slate-500 hover:text-slate-300 text-sm">📋</button>
                                      </div>
                                    </div>
                                    <p className="text-slate-200 text-sm whitespace-pre-wrap">{pt}</p>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                          {/* Headlines */}
                          {facebook_ads.headlines && facebook_ads.headlines.length > 0 && (
                            <div className="mb-4">
                              <p className="text-xs text-slate-400 mb-2">Headline（目安: 40文字以内）</p>
                              <div className="space-y-2">
                                {facebook_ads.headlines.map((h, i) => (
                                  <div key={i} className="flex items-center gap-2">
                                    <span className="text-xs text-slate-500 flex-shrink-0">案{i + 1}</span>
                                    <span className="text-slate-200 text-sm flex-1">{h}</span>
                                    <LenBadge count={h.length} limit={40} />
                                    <button onClick={() => copyText(h)} className="text-slate-500 hover:text-slate-300 flex-shrink-0 text-sm">📋</button>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                          {/* Descriptions */}
                          {facebook_ads.descriptions && facebook_ads.descriptions.length > 0 && (
                            <div className="mb-4">
                              <p className="text-xs text-slate-400 mb-2">Description（目安: 20〜30文字）</p>
                              <div className="space-y-2">
                                {facebook_ads.descriptions.map((d, i) => (
                                  <div key={i} className="flex items-center gap-2">
                                    <span className="text-xs text-slate-500 flex-shrink-0">案{i + 1}</span>
                                    <span className="text-slate-200 text-sm flex-1">{d}</span>
                                    <LenBadge count={d.length} limit={30} />
                                    <button onClick={() => copyText(d)} className="text-slate-500 hover:text-slate-300 flex-shrink-0 text-sm">📋</button>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                          {/* CTA */}
                          {facebook_ads.cta && (
                            <div className="flex items-center gap-2">
                              <span className="text-xs text-slate-400">CTA:</span>
                              <span className="text-slate-200 text-sm flex-1">{facebook_ads.cta}</span>
                              <button onClick={() => copyText(facebook_ads.cta)} className="text-slate-500 hover:text-slate-300 text-sm">📋</button>
                            </div>
                          )}
                        </div>
                      )}

                      {/* Instagram 広告 */}
                      {instagram_ads && (
                        <div className="bg-gradient-to-br from-purple-900/20 to-violet-900/10 border border-purple-700/25 rounded-xl p-5">
                          <div className="flex items-center justify-between mb-4">
                            <h5 className="text-base font-semibold text-purple-300">Instagram 広告</h5>
                            <button
                              onClick={() => {
                                const sections = (instagram_ads.primary_texts || []).map((pt, i) =>
                                  `【案${i + 1}】\nPrimary Text: ${pt}\nHeadline: ${(instagram_ads.headlines || [])[i] || ""}\nDescription: ${(instagram_ads.descriptions || [])[i] || ""}`
                                );
                                const tags = (instagram_ads.hashtags || []).join(" ");
                                copyText([...sections, `Hashtags: ${tags}`].join("\n\n"));
                              }}
                              className="text-xs px-3 py-1 rounded bg-purple-700/25 text-purple-300 hover:bg-purple-700/40 transition-colors"
                            >
                              全コピー
                            </button>
                          </div>
                          {/* Primary Texts */}
                          {instagram_ads.primary_texts && instagram_ads.primary_texts.length > 0 && (
                            <div className="mb-4">
                              <p className="text-xs text-slate-400 mb-2">Primary Text（冒頭125文字に重要訴求を集約）</p>
                              <div className="space-y-3">
                                {instagram_ads.primary_texts.map((pt, i) => (
                                  <div key={i} className="bg-white/5 rounded-lg p-3">
                                    <div className="flex items-center justify-between mb-1">
                                      <span className="text-xs text-slate-400">案{i + 1}</span>
                                      <div className="flex items-center gap-2">
                                        <LenBadge count={pt.length} limit={125} />
                                        <button onClick={() => copyText(pt)} className="text-slate-500 hover:text-slate-300 text-sm">📋</button>
                                      </div>
                                    </div>
                                    <p className="text-slate-200 text-sm whitespace-pre-wrap">{pt}</p>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                          {/* Headlines */}
                          {instagram_ads.headlines && instagram_ads.headlines.length > 0 && (
                            <div className="mb-4">
                              <p className="text-xs text-slate-400 mb-2">Headline（目安: 40文字以内）</p>
                              <div className="space-y-2">
                                {instagram_ads.headlines.map((h, i) => (
                                  <div key={i} className="flex items-center gap-2">
                                    <span className="text-xs text-slate-500 flex-shrink-0">案{i + 1}</span>
                                    <span className="text-slate-200 text-sm flex-1">{h}</span>
                                    <LenBadge count={h.length} limit={40} />
                                    <button onClick={() => copyText(h)} className="text-slate-500 hover:text-slate-300 flex-shrink-0 text-sm">📋</button>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                          {/* Descriptions */}
                          {instagram_ads.descriptions && instagram_ads.descriptions.length > 0 && (
                            <div className="mb-4">
                              <p className="text-xs text-slate-400 mb-2">Description（目安: 20〜30文字）</p>
                              <div className="space-y-2">
                                {instagram_ads.descriptions.map((d, i) => (
                                  <div key={i} className="flex items-center gap-2">
                                    <span className="text-xs text-slate-500 flex-shrink-0">案{i + 1}</span>
                                    <span className="text-slate-200 text-sm flex-1">{d}</span>
                                    <LenBadge count={d.length} limit={30} />
                                    <button onClick={() => copyText(d)} className="text-slate-500 hover:text-slate-300 flex-shrink-0 text-sm">📋</button>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                          {/* Hashtags */}
                          {instagram_ads.hashtags && instagram_ads.hashtags.length > 0 && (
                            <div>
                              <div className="flex items-center justify-between mb-2">
                                <p className="text-xs text-slate-400">ハッシュタグ</p>
                                <button onClick={() => copyText(instagram_ads.hashtags.join(" "))} className="text-xs text-slate-500 hover:text-slate-300">📋 全コピー</button>
                              </div>
                              <div className="flex flex-wrap gap-2">
                                {instagram_ads.hashtags.map((tag, i) => (
                                  <button
                                    key={i}
                                    onClick={() => copyText(tag)}
                                    className="text-xs px-2 py-1 rounded-full bg-purple-900/20 text-purple-300 hover:bg-purple-900/35 transition-colors"
                                  >
                                    {tag}
                                  </button>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      )}

                    </div>
                  </div>
                );
              })()}

              {/* 広告用画像 */}
              {currentAsset.ad_image_urls && Object.keys(currentAsset.ad_image_urls).length > 0 && (
                <div className="glass-card p-6 lg:col-span-2">
                  <div className="flex items-center gap-3 mb-4">
                    <Image className="w-6 h-6 text-orange-400" />
                    <h4 className="text-xl font-bold text-white">広告用画像</h4>
                    <span className="text-xs text-slate-500">（クリックで拡大表示）</span>
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
                            // 画像URLの場合は実際の画像を表示（クリックで拡大）
                            <div 
                              className="relative aspect-video rounded-lg overflow-hidden bg-slate-800 cursor-pointer group"
                              onClick={() => {
                                setModalImageUrl(`${API_BASE_URL}${imageValue}`);
                                setModalImageTitle(key);
                                setShowImageModal(true);
                              }}
                            >
                              <img
                                src={`${API_BASE_URL}${imageValue}`}
                                alt={key}
                                className="w-full h-full object-cover transition-transform group-hover:scale-105"
                              />
                              <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-all flex items-center justify-center opacity-0 group-hover:opacity-100">
                                <div className="bg-white/20 backdrop-blur-sm rounded-full p-2">
                                  <Eye className="w-5 h-5 text-white" />
                                </div>
                              </div>
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

          {/* OTAテキスト（じゃらん・楽天トラベル） */}
          {currentAsset && currentAsset.ota_text && Object.keys(currentAsset.ota_text).length > 0 && (
            <div className="glass-card p-6 mt-8 lg:col-span-2">
              <div className="flex items-center gap-3 mb-6">
                <svg className="w-6 h-6 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                </svg>
                <h4 className="text-xl font-bold text-white">OTAテキスト</h4>
                <span className="text-xs text-slate-500">（じゃらん・楽天トラベル向け）</span>
              </div>
              
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* じゃらん用 */}
                {currentAsset.ota_text.jalan && (
                  <div className="bg-gradient-to-br from-orange-500/10 to-red-500/10 border border-orange-500/30 rounded-xl p-6">
                    <div className="flex items-center gap-2 mb-4">
                      <div className="w-8 h-8 rounded-lg bg-orange-500/20 flex items-center justify-center">
                        <span className="text-orange-400 font-bold text-sm">J</span>
                      </div>
                      <h5 className="text-lg font-bold text-orange-400">じゃらん用</h5>
                      <button
                        onClick={() => {
                          const jalan = currentAsset.ota_text.jalan;
                          if (jalan) {
                            const text = `【プランタイトル】\n${jalan.plan_title}\n\n【キャッチコピー】\n${jalan.catch_copy}\n\n【プラン説明】\n${jalan.plan_description}\n\n【特徴】\n${jalan.features?.join('\n') || ''}`;
                            navigator.clipboard.writeText(text);
                            alert("じゃらん用テキストをコピーしました");
                          }
                        }}
                        className="ml-auto text-xs text-orange-400 hover:text-orange-300 transition-colors px-2 py-1 rounded hover:bg-orange-500/20"
                      >
                        📋 全てコピー
                      </button>
                    </div>
                    
                    <div className="space-y-4">
                      <div>
                        <div className="flex items-center justify-between mb-1">
                          <p className="text-xs text-slate-500 font-medium">プランタイトル（50文字以内）</p>
                          <button
                            onClick={() => {
                              navigator.clipboard.writeText(currentAsset.ota_text.jalan?.plan_title || "");
                              alert("コピーしました");
                            }}
                            className="text-xs text-slate-500 hover:text-slate-300"
                          >
                            📋
                          </button>
                        </div>
                        <p className="text-white font-semibold bg-black/20 rounded-lg p-3">
                          {currentAsset.ota_text.jalan.plan_title}
                        </p>
                      </div>
                      
                      <div>
                        <div className="flex items-center justify-between mb-1">
                          <p className="text-xs text-slate-500 font-medium">キャッチコピー</p>
                          <button
                            onClick={() => {
                              navigator.clipboard.writeText(currentAsset.ota_text.jalan?.catch_copy || "");
                              alert("コピーしました");
                            }}
                            className="text-xs text-slate-500 hover:text-slate-300"
                          >
                            📋
                          </button>
                        </div>
                        <p className="text-orange-300 bg-black/20 rounded-lg p-3">
                          {currentAsset.ota_text.jalan.catch_copy}
                        </p>
                      </div>
                      
                      <div>
                        <div className="flex items-center justify-between mb-1">
                          <p className="text-xs text-slate-500 font-medium">プラン説明文</p>
                          <button
                            onClick={() => {
                              navigator.clipboard.writeText(currentAsset.ota_text.jalan?.plan_description || "");
                              alert("コピーしました");
                            }}
                            className="text-xs text-slate-500 hover:text-slate-300"
                          >
                            📋
                          </button>
                        </div>
                        <div className="bg-black/20 rounded-lg p-3 max-h-48 overflow-y-auto">
                          <p className="text-slate-300 text-sm whitespace-pre-wrap leading-relaxed">
                            {currentAsset.ota_text.jalan.plan_description}
                          </p>
                        </div>
                      </div>
                      
                      {currentAsset.ota_text.jalan.features && currentAsset.ota_text.jalan.features.length > 0 && (
                        <div>
                          <p className="text-xs text-slate-500 font-medium mb-2">特徴</p>
                          <div className="flex flex-wrap gap-2">
                            {currentAsset.ota_text.jalan.features.map((feature, idx) => (
                              <span key={idx} className="text-xs bg-orange-500/20 text-orange-300 px-2 py-1 rounded">
                                {feature}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}
                
                {/* 楽天トラベル用 */}
                {currentAsset.ota_text.rakuten && (
                  <div className="bg-gradient-to-br from-red-500/10 to-pink-500/10 border border-red-500/30 rounded-xl p-6">
                    <div className="flex items-center gap-2 mb-4">
                      <div className="w-8 h-8 rounded-lg bg-red-500/20 flex items-center justify-center">
                        <span className="text-red-400 font-bold text-sm">R</span>
                      </div>
                      <h5 className="text-lg font-bold text-red-400">楽天トラベル用</h5>
                      <button
                        onClick={() => {
                          const rakuten = currentAsset.ota_text.rakuten;
                          if (rakuten) {
                            const text = `【プランタイトル】\n${rakuten.plan_title}\n\n【キャッチコピー】\n${rakuten.catch_copy}\n\n【プラン説明】\n${rakuten.plan_description}\n\n【特徴】\n${rakuten.features?.join('\n') || ''}`;
                            navigator.clipboard.writeText(text);
                            alert("楽天トラベル用テキストをコピーしました");
                          }
                        }}
                        className="ml-auto text-xs text-red-400 hover:text-red-300 transition-colors px-2 py-1 rounded hover:bg-red-500/20"
                      >
                        📋 全てコピー
                      </button>
                    </div>
                    
                    <div className="space-y-4">
                      <div>
                        <div className="flex items-center justify-between mb-1">
                          <p className="text-xs text-slate-500 font-medium">プランタイトル（50文字以内）</p>
                          <button
                            onClick={() => {
                              navigator.clipboard.writeText(currentAsset.ota_text.rakuten?.plan_title || "");
                              alert("コピーしました");
                            }}
                            className="text-xs text-slate-500 hover:text-slate-300"
                          >
                            📋
                          </button>
                        </div>
                        <p className="text-white font-semibold bg-black/20 rounded-lg p-3">
                          {currentAsset.ota_text.rakuten.plan_title}
                        </p>
                      </div>
                      
                      <div>
                        <div className="flex items-center justify-between mb-1">
                          <p className="text-xs text-slate-500 font-medium">キャッチコピー</p>
                          <button
                            onClick={() => {
                              navigator.clipboard.writeText(currentAsset.ota_text.rakuten?.catch_copy || "");
                              alert("コピーしました");
                            }}
                            className="text-xs text-slate-500 hover:text-slate-300"
                          >
                            📋
                          </button>
                        </div>
                        <p className="text-red-300 bg-black/20 rounded-lg p-3">
                          {currentAsset.ota_text.rakuten.catch_copy}
                        </p>
                      </div>
                      
                      <div>
                        <div className="flex items-center justify-between mb-1">
                          <p className="text-xs text-slate-500 font-medium">プラン説明文</p>
                          <button
                            onClick={() => {
                              navigator.clipboard.writeText(currentAsset.ota_text.rakuten?.plan_description || "");
                              alert("コピーしました");
                            }}
                            className="text-xs text-slate-500 hover:text-slate-300"
                          >
                            📋
                          </button>
                        </div>
                        <div className="bg-black/20 rounded-lg p-3 max-h-48 overflow-y-auto">
                          <p className="text-slate-300 text-sm whitespace-pre-wrap leading-relaxed">
                            {currentAsset.ota_text.rakuten.plan_description}
                          </p>
                        </div>
                      </div>
                      
                      {currentAsset.ota_text.rakuten.features && currentAsset.ota_text.rakuten.features.length > 0 && (
                        <div>
                          <p className="text-xs text-slate-500 font-medium mb-2">特徴</p>
                          <div className="flex flex-wrap gap-2">
                            {currentAsset.ota_text.rakuten.features.map((feature, idx) => (
                              <span key={idx} className="text-xs bg-red-500/20 text-red-300 px-2 py-1 rounded">
                                {feature}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* SNS投稿ジェネレーター */}
          <div className="glass-card p-8 mt-8">
            <div className="flex items-center gap-3 mb-6">
              <Instagram className="w-6 h-6 text-pink-400" />
              <h3 className="text-2xl font-bold text-white">SNS投稿ジェネレーター</h3>
            </div>

            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-slate-300 text-sm mb-2">プラットフォーム</label>
                  <select 
                    value={snsPlatform}
                    onChange={(e) => setSnsPlatform(e.target.value)}
                    className="w-full bg-slate-800 border border-white/10 rounded-lg p-3 text-slate-200 focus:outline-none focus:border-purple-500 [&>option]:bg-slate-800 [&>option]:text-white"
                  >
                    <option value="">プラットフォームを選択</option>
                    <option value="instagram">Instagram</option>
                    <option value="facebook">Facebook</option>
                    <option value="twitter">Twitter</option>
                  </select>
                </div>
                <div>
                  <label className="block text-slate-300 text-sm mb-2">投稿タイプ</label>
                  <select 
                    value={snsPostType}
                    onChange={(e) => setSnsPostType(e.target.value)}
                    className="w-full bg-slate-800 border border-white/10 rounded-lg p-3 text-slate-200 focus:outline-none focus:border-purple-500 [&>option]:bg-slate-800 [&>option]:text-white"
                  >
                    <option value="">投稿タイプを選択</option>
                    <option value="温泉紹介">温泉紹介</option>
                    <option value="料理紹介">料理紹介</option>
                    <option value="イベント告知">イベント告知</option>
                    <option value="客室紹介">客室紹介</option>
                    <option value="季節の情報">季節の情報</option>
                    <option value="その他">その他</option>
                  </select>
                </div>
              </div>
              
              {/* 投稿説明欄 */}
              <div>
                <label className="block text-slate-300 text-sm mb-2">
                  どんな投稿を作りたいですか？（任意）
                </label>
                <textarea
                  value={snsDescription}
                  onChange={(e) => setSnsDescription(e.target.value)}
                  placeholder="例: 新しく始めた岩盤浴サービスを紹介したい / 秋の紅葉シーズンに合わせた投稿 / 記念日プランの告知など"
                  className="w-full h-24 bg-white/5 border border-white/10 rounded-lg p-3 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-purple-500 resize-none"
                />
                <p className="text-xs text-slate-500 mt-1">
                  具体的な内容を入力すると、より適切な投稿が生成されます
                </p>
              </div>

              {snsError && (
                <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-red-400 text-sm">
                  {snsError}
                </div>
              )}

              <button 
                onClick={async () => {
                  if (!snsPlatform || !snsPostType) {
                    setSnsError("プラットフォームと投稿タイプを選択してください");
                    return;
                  }
                  setSnsError("");
                  setGeneratingSns(true);
                  try {
                    const result = await marketingApi.generateSNSPost(hotelId, {
                      platform: snsPlatform,
                      post_type: snsPostType,
                      description: snsDescription,
                    });
                    setSnsPost(result);
                  } catch (error) {
                    console.error("SNS post generation failed:", error);
                    setSnsError("SNS投稿の生成に失敗しました。もう一度お試しください。");
                  } finally {
                    setGeneratingSns(false);
                  }
                }}
                disabled={generatingSns || !snsPlatform || !snsPostType}
                className="w-full bg-gradient-to-r from-purple-500 to-cyan-500 text-white py-4 rounded-lg hover:from-purple-600 hover:to-cyan-600 transition-all font-semibold disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {generatingSns ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    生成中...
                  </>
                ) : (
                  <>
                    <Wand2 className="w-5 h-5" />
                    SNS投稿を作成
                  </>
                )}
              </button>

              {/* 生成結果 */}
              {snsPost && (
                <div className="bg-white/5 border border-white/10 rounded-lg p-6">
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="text-lg font-semibold text-white">生成された投稿</h4>
                    <div className="flex items-center gap-2">
                      <span className="text-xs bg-purple-500/20 text-purple-400 px-2 py-1 rounded">
                        {snsPost.platform}
                      </span>
                      <span className="text-xs bg-cyan-500/20 text-cyan-400 px-2 py-1 rounded">
                        {snsPost.post_type}
                      </span>
                    </div>
                  </div>
                  <div className="bg-black/20 rounded-lg p-4 mb-4">
                    <p className="text-slate-300 leading-relaxed whitespace-pre-wrap">
                      {snsPost.content}
                    </p>
                  </div>
                  {snsPost.hashtags && snsPost.hashtags.length > 0 && (
                    <div className="flex flex-wrap gap-2">
                      {snsPost.hashtags.map((tag, index) => (
                        <span key={index} className="text-cyan-400 text-sm">
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                  <div className="mt-4 pt-4 border-t border-white/10 flex items-center justify-between">
                    <p className="text-xs text-slate-500">
                      生成日時: {new Date(snsPost.generated_at).toLocaleString('ja-JP')}
                    </p>
                    <button
                      onClick={() => {
                        const fullText = `${snsPost.content}\n\n${snsPost.hashtags.join(' ')}`;
                        navigator.clipboard.writeText(fullText);
                        alert("投稿内容をコピーしました");
                      }}
                      className="text-sm text-purple-400 hover:text-purple-300 transition-colors"
                    >
                      📋 コピー
                    </button>
                  </div>
                </div>
              )}
              
              {/* 初期表示（投稿がない場合） */}
              {!snsPost && !generatingSns && (
                <div className="bg-white/5 border border-white/10 rounded-lg p-6 text-center">
                  <MessageSquare className="w-12 h-12 text-slate-600 mx-auto mb-3" />
                  <p className="text-slate-500">
                    プラットフォームと投稿タイプを選択して、<br />
                    AIにSNS投稿を生成してもらいましょう
                  </p>
                </div>
              )}
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

      {/* 画像プレビューモーダル - Portalで画面全体に表示 */}
      {showImageModal && modalImageUrl && typeof document !== "undefined" && createPortal(
        <div 
          className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/90 backdrop-blur-sm"
          onClick={() => setShowImageModal(false)}
        >
          {/* 閉じるボタン */}
          <button
            onClick={() => setShowImageModal(false)}
            className="absolute top-4 right-4 p-3 text-white/70 hover:text-white hover:bg-white/10 rounded-full transition-all z-10"
          >
            <X className="w-8 h-8" />
          </button>
          
          {/* 画像タイトル */}
          <div className="absolute top-4 left-4 px-4 py-2 bg-black/50 rounded-lg">
            <p className="text-white font-medium">{modalImageTitle}</p>
          </div>
          
          {/* 画像コンテナ */}
          <div 
            className="relative max-w-[95vw] max-h-[95vh] p-4"
            onClick={(e) => e.stopPropagation()}
          >
            <img
              src={modalImageUrl}
              alt={modalImageTitle}
              className="max-w-full max-h-[90vh] object-contain rounded-lg shadow-2xl"
            />
          </div>
          
          {/* 操作説明 */}
          <div className="absolute bottom-4 left-1/2 -translate-x-1/2 px-4 py-2 bg-black/50 rounded-lg">
            <p className="text-white/70 text-sm">クリックまたはESCで閉じる</p>
          </div>
        </div>,
        document.body
      )}

      {/* 画像差し替え確認モーダル - Portalで画面全体に表示 */}
      {pendingImageUpload && typeof document !== "undefined" && createPortal(
        <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="relative w-full max-w-xl bg-slate-900 rounded-2xl overflow-hidden shadow-2xl border border-white/10">
            {/* ヘッダー */}
            <div className="flex items-center justify-between px-5 py-4 bg-slate-800/50 border-b border-white/10">
              <div className="flex items-center gap-2">
                <Upload className="w-5 h-5 text-cyan-400" />
                <h3 className="text-lg font-semibold text-white">画像の差し替え確認</h3>
              </div>
              <button
                onClick={handleCancelImageUpload}
                className="p-1.5 text-slate-400 hover:text-white hover:bg-white/10 rounded-lg transition-all"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            
            {/* コンテンツ */}
            <div className="p-5">
              <div className="mb-4">
                <p className="text-slate-300 text-sm mb-2">
                  <span className="font-medium text-white">{pendingImageUpload.imageType}</span> 画像を差し替えます
                </p>
                <p className="text-slate-500 text-xs">
                  確定ボタンを押すと、この画像がアップロードされ、LPの画像パスも自動的に更新されます。
                </p>
              </div>
              
              {/* 画像プレビュー */}
              <div className="mb-5">
                <p className="text-sm text-slate-400 mb-2">新しい画像のプレビュー</p>
                <div className="relative aspect-video rounded-lg overflow-hidden bg-slate-800 border border-white/10">
                  <img
                    src={pendingImageUpload.previewUrl}
                    alt="新しい画像のプレビュー"
                    className="w-full h-full object-contain"
                  />
                </div>
                <p className="text-xs text-slate-500 mt-2">
                  ファイル名: {pendingImageUpload.file.name}
                </p>
              </div>
              
              {/* ボタン */}
              <div className="flex gap-3">
                <button
                  onClick={handleCancelImageUpload}
                  className="flex-1 px-4 py-3 bg-white/5 text-slate-300 rounded-lg hover:bg-white/10 transition-all font-medium"
                >
                  キャンセル
                </button>
                <button
                  onClick={handleConfirmImageUpload}
                  disabled={uploadingImage !== null}
                  className="flex-1 px-4 py-3 bg-gradient-to-r from-cyan-500 to-blue-500 text-white rounded-lg hover:from-cyan-600 hover:to-blue-600 transition-all font-medium disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {uploadingImage ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      アップロード中...
                    </>
                  ) : (
                    <>
                      <CheckCircle className="w-4 h-4" />
                      確定して差し替え
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>,
        document.body
      )}
      {/* コピー完了トースト */}
      {toast && createPortal(
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-[9999] pointer-events-none">
          <div className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-slate-800 border border-slate-600 shadow-xl text-sm text-white animate-fadeIn">
            <CheckCircle className="w-4 h-4 text-green-400 flex-shrink-0" />
            {toast}
          </div>
        </div>,
        document.body
      )}
    </section>
  );
}


