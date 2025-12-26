"use client";

import { useEffect, useState, useRef } from "react";
import { Upload, Users, Loader2, CheckCircle, AlertCircle, Calendar, TrendingUp, BarChart3, Clock, Star, DollarSign, FileText, Link2, ExternalLink, RefreshCw, MessageSquare } from "lucide-react";
import { useHotel } from "@/lib/hotel-context";
import { marketingApi, AnalysisSession, ReviewUrlsUpdate } from "@/lib/api";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

// 統計カードのラベル定義
const STAT_LABELS: Record<string, { label: string; icon: React.ElementType }> = {
  total_records: { label: "総レコード数", icon: FileText },
  schema_mapping: { label: "データ項目マッピング", icon: FileText },
  date_range: { label: "データ期間", icon: Calendar },
  cancellation_stats: { label: "キャンセル統計", icon: TrendingUp },
  average_lead_time: { label: "平均リードタイム", icon: Clock },
  top_plans: { label: "人気プランTOP5", icon: Star },
  weekday_occupancy: { label: "曜日別予約数", icon: BarChart3 },
  guest_stats: { label: "宿泊人数統計", icon: Users },
  price_stats: { label: "価格統計（人数あたり単価）", icon: DollarSign },
};

// 曜日の日本語変換と順序
const WEEKDAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const WEEKDAY_JP: Record<string, string> = {
  Monday: "月曜日",
  Tuesday: "火曜日",
  Wednesday: "水曜日",
  Thursday: "木曜日",
  Friday: "金曜日",
  Saturday: "土曜日",
  Sunday: "日曜日",
};

// 日付をフォーマット
function formatDate(dateStr: string): string {
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString("ja-JP", { year: "numeric", month: "long", day: "numeric" });
  } catch {
    return dateStr;
  }
}

// 数値をフォーマット
function formatNumber(num: number): string {
  return num.toLocaleString("ja-JP");
}

// パーセントをフォーマット
function formatPercent(num: number): string {
  return `${(num * 100).toFixed(1)}%`;
}

// 統計値を表示するコンポーネント
function StatCard({ statKey, value }: { statKey: string; value: unknown }) {
  const config = STAT_LABELS[statKey] || { label: statKey, icon: FileText };
  const Icon = config.icon;

  // データ種類に応じた表示内容を生成
  const renderContent = () => {
    // 単純な数値
    if (typeof value === "number") {
      return <p className="text-2xl font-bold text-white">{formatNumber(value)}</p>;
    }

    // 単純な文字列
    if (typeof value === "string") {
      return <p className="text-lg font-semibold text-white">{value}</p>;
    }

    // オブジェクトの場合、キーに応じて表示を変える
    if (typeof value === "object" && value !== null) {
      const obj = value as Record<string, unknown>;

      // date_range
      if (statKey === "date_range" && "start" in obj && "end" in obj) {
        return (
          <div className="space-y-1">
            <p className="text-white">
              <span className="text-slate-400 text-sm">開始: </span>
              {formatDate(obj.start as string)}
            </p>
            <p className="text-white">
              <span className="text-slate-400 text-sm">終了: </span>
              {formatDate(obj.end as string)}
            </p>
          </div>
        );
      }

      // cancellation_stats
      if (statKey === "cancellation_stats") {
        return (
          <div className="space-y-1">
            {obj.total_bookings !== undefined && (
              <p className="text-white">
                <span className="text-slate-400 text-sm">総予約数: </span>
                {formatNumber(obj.total_bookings as number)}
              </p>
            )}
            {obj.cancelled_bookings !== undefined && (
              <p className="text-white">
                <span className="text-slate-400 text-sm">キャンセル数: </span>
                {formatNumber(obj.cancelled_bookings as number)}
              </p>
            )}
            {obj.cancellation_rate !== undefined && (
              <p className="text-white">
                <span className="text-slate-400 text-sm">キャンセル率: </span>
                <span className="text-red-400 font-semibold">
                  {formatPercent(obj.cancellation_rate as number)}
                </span>
              </p>
            )}
          </div>
        );
      }

      // guest_stats - 宿泊人数統計
      if (statKey === "guest_stats") {
        const distribution = (obj.distribution as Record<string, number>) || {};
        return (
          <div className="space-y-2">
            <div className="grid grid-cols-2 gap-2">
              {obj.average !== undefined && (
                <p className="text-white">
                  <span className="text-slate-400 text-sm">平均: </span>
                  {obj.average as number}人
                </p>
              )}
              {obj.total_guests !== undefined && (
                <p className="text-white">
                  <span className="text-slate-400 text-sm">総人数: </span>
                  {formatNumber(obj.total_guests as number)}人
                </p>
              )}
            </div>
            {Object.keys(distribution).length > 0 && (
              <div className="mt-2 pt-2 border-t border-white/10">
                <p className="text-slate-400 text-xs mb-2">人数分布</p>
                <div className="space-y-1">
                  {["1人", "2人", "3人", "4人", "5人以上"].map((key) => {
                    const count = distribution[key];
                    if (count === undefined) return null;
                    return (
                      <div key={key} className="flex justify-between items-center">
                        <span className="text-slate-400 text-sm">{key}</span>
                        <span className="text-white font-medium">{formatNumber(count)}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        );
      }

      // price_stats - 価格統計（人数あたり単価）
      if (statKey === "price_stats") {
        const hasPerGuest = obj.per_guest_average !== undefined;
        return (
          <div className="space-y-2">
            {/* 人数あたり単価（メイン表示） */}
            {hasPerGuest && (
              <div className="mb-3 pb-3 border-b border-white/10">
                <p className="text-cyan-400 text-xs mb-2">▼ 1人あたり単価</p>
                <div className="grid grid-cols-2 gap-2">
                  {obj.per_guest_average !== undefined && (
                    <p className="text-white">
                      <span className="text-slate-400 text-sm">平均: </span>
                      ¥{formatNumber(Math.round(obj.per_guest_average as number))}
                    </p>
                  )}
                  {obj.per_guest_median !== undefined && (
                    <p className="text-white">
                      <span className="text-slate-400 text-sm">中央値: </span>
                      ¥{formatNumber(Math.round(obj.per_guest_median as number))}
                    </p>
                  )}
                  {obj.per_guest_min !== undefined && (
                    <p className="text-white">
                      <span className="text-slate-400 text-sm">最小: </span>
                      ¥{formatNumber(Math.round(obj.per_guest_min as number))}
                    </p>
                  )}
                  {obj.per_guest_max !== undefined && (
                    <p className="text-white">
                      <span className="text-slate-400 text-sm">最大: </span>
                      ¥{formatNumber(Math.round(obj.per_guest_max as number))}
                    </p>
                  )}
                </div>
              </div>
            )}
            
            {/* 合計金額（参考表示） */}
            <div>
              <p className="text-slate-500 text-xs mb-2">▼ 予約合計金額</p>
              <div className="grid grid-cols-2 gap-2">
                {(obj.total_average ?? obj.average) !== undefined && (
                  <p className="text-slate-300 text-sm">
                    <span className="text-slate-500 text-xs">平均: </span>
                    ¥{formatNumber(Math.round((obj.total_average ?? obj.average) as number))}
                  </p>
                )}
                {(obj.total_median ?? obj.median) !== undefined && (
                  <p className="text-slate-300 text-sm">
                    <span className="text-slate-500 text-xs">中央値: </span>
                    ¥{formatNumber(Math.round((obj.total_median ?? obj.median) as number))}
                  </p>
                )}
              </div>
            </div>
            
            {obj.excluded_count !== undefined && (obj.excluded_count as number) > 0 && (
              <p className="text-slate-500 text-xs mt-2">
                ※ 金額0円のデータ {formatNumber(obj.excluded_count as number)}件を除外
              </p>
            )}
          </div>
        );
      }

      // weekday_occupancy - 曜日順にソート
      if (statKey === "weekday_occupancy") {
        const sortedEntries = WEEKDAY_ORDER
          .filter((day) => day in obj)
          .map((day) => [day, obj[day]] as [string, number]);

        return (
          <div className="space-y-1">
            {sortedEntries.map(([day, count]) => (
              <div key={day} className="flex justify-between items-center">
                <span className="text-slate-400 text-sm">{WEEKDAY_JP[day] || day}</span>
                <span className="text-white font-medium">{formatNumber(count)}</span>
              </div>
            ))}
          </div>
        );
      }

      // top_plans - プラン名と件数
      if (statKey === "top_plans") {
        const entries = Object.entries(obj).slice(0, 5);
        return (
          <div className="space-y-2">
            {entries.map(([plan, count], index) => (
              <div key={plan} className="flex items-start gap-2">
                <span className="text-purple-400 font-bold text-sm min-w-[20px]">
                  {index + 1}.
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-white text-sm truncate" title={plan}>
                    {plan}
                  </p>
                  <p className="text-slate-400 text-xs">{formatNumber(count as number)}件</p>
                </div>
              </div>
            ))}
          </div>
        );
      }

      // schema_mapping - キーと値のマッピング
      if (statKey === "schema_mapping") {
        const entries = Object.entries(obj);
        return (
          <div className="space-y-1">
            {entries.map(([key, val]) => (
              <div key={key} className="flex items-center gap-2">
                <span className="text-cyan-400 text-sm">{String(val)}</span>
                <span className="text-slate-500">→</span>
                <span className="text-slate-400 text-xs">{key}</span>
              </div>
            ))}
          </div>
        );
      }

      // その他のオブジェクト - キー: 値形式
      const entries = Object.entries(obj);
      return (
        <div className="space-y-1">
          {entries.map(([k, v]) => (
            <div key={k} className="flex justify-between items-center">
              <span className="text-slate-400 text-sm truncate max-w-[60%]">{k}</span>
              <span className="text-white font-medium text-sm">
                {typeof v === "number" ? formatNumber(v) : String(v)}
              </span>
            </div>
          ))}
        </div>
      );
    }

    return <p className="text-white">{String(value)}</p>;
  };

  // カードサイズを決定（top_plans, weekday_occupancy, guest_stats, price_statsは大きめ）
  const isLargeCard = ["top_plans", "weekday_occupancy", "schema_mapping", "guest_stats", "price_stats"].includes(statKey);

  return (
    <div
      className={`p-4 bg-white/5 rounded-lg border border-white/10 overflow-hidden ${
        isLargeCard ? "md:col-span-2 lg:col-span-1" : ""
      }`}
    >
      <div className="flex items-center gap-2 mb-3">
        <Icon className="w-4 h-4 text-purple-400" />
        <p className="text-sm text-slate-400 font-medium">{config.label}</p>
      </div>
      <div className="overflow-hidden">{renderContent()}</div>
    </div>
  );
}

export default function PersonaPage() {
  const { hotel, hotelId } = useHotel();
  const [session, setSession] = useState<AnalysisSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // 口コミURL関連のstate
  const [reviewUrls, setReviewUrls] = useState<Record<string, string>>({});
  const [jalanUrl, setJalanUrl] = useState("");
  const [googleUrl, setGoogleUrl] = useState("");
  const [savingUrls, setSavingUrls] = useState(false);
  const [analyzingReviews, setAnalyzingReviews] = useState(false);
  const [urlSaveMessage, setUrlSaveMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        const [sessionData, urlsData] = await Promise.all([
          marketingApi.getAnalysisSession(hotelId),
          marketingApi.getReviewUrls(hotelId).catch(() => null),
        ]);
        setSession(sessionData);
        if (urlsData?.review_urls) {
          setReviewUrls(urlsData.review_urls);
          setJalanUrl(urlsData.review_urls.jalan || "");
          setGoogleUrl(urlsData.review_urls.google || "");
        }
      } catch (error) {
        console.error("Failed to load session:", error);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [hotelId]);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setUploadError(null);
    setUploadSuccess(false);

    try {
      const result = await marketingApi.analyzeCustomerCSV(hotelId, file);
      setSession((prev) => prev ? {
        ...prev,
        session_id: result.session_id,
        csv_statistics: result.statistics,
        csv_insights: result.insights,
      } : null);
      setUploadSuccess(true);
      
      // Reload full session data
      const sessionData = await marketingApi.getAnalysisSession(hotelId);
      setSession(sessionData);
    } catch (error) {
      console.error("Upload failed:", error);
      setUploadError(error instanceof Error ? error.message : "アップロードに失敗しました");
    } finally {
      setUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const handleSaveReviewUrls = async () => {
    setSavingUrls(true);
    setUrlSaveMessage(null);
    try {
      const urls: ReviewUrlsUpdate = {};
      if (jalanUrl.trim()) urls.jalan = jalanUrl.trim();
      if (googleUrl.trim()) urls.google = googleUrl.trim();

      const result = await marketingApi.updateReviewUrls(hotelId, urls);
      setReviewUrls(result.review_urls);
      setUrlSaveMessage({ type: "success", text: "口コミURLを保存しました" });
    } catch (error) {
      console.error("Failed to save review URLs:", error);
      setUrlSaveMessage({ type: "error", text: "URLの保存に失敗しました。URLの形式を確認してください。" });
    } finally {
      setSavingUrls(false);
    }
  };

  const handleAnalyzeReviews = async () => {
    setAnalyzingReviews(true);
    try {
      await marketingApi.analyzeReviews(hotelId);
      // Reload session data
      const sessionData = await marketingApi.getAnalysisSession(hotelId);
      setSession(sessionData);
    } catch (error) {
      console.error("Review analysis failed:", error);
      alert("口コミ分析に失敗しました。Difyの設定を確認してください。");
    } finally {
      setAnalyzingReviews(false);
    }
  };

  const hasCustomerData = session?.csv_statistics && Object.keys(session.csv_statistics).length > 0;
  const hasReviewUrls = Object.keys(reviewUrls).length > 0;
  const hasReviewData = session?.reviews_summary && Object.keys(session.reviews_summary).length > 0;

  return (
    <section className="animate-fadeIn">
      <h2 className="text-3xl font-bold text-white mb-2">顧客を知る</h2>
      <p className="text-slate-400 mb-8">
        {hotel.name}の顧客データと口コミを分析し、ターゲット顧客を特定します
      </p>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-purple-500"></div>
        </div>
      ) : (
        <>
          {/* CSVアップロードセクション */}
          <div className="glass-card p-8 mb-8">
            <div className="flex items-center gap-3 mb-6">
              <Upload className="w-6 h-6 text-cyan-400" />
              <h3 className="text-2xl font-bold text-white">顧客データをアップロード</h3>
            </div>
            
            <p className="text-slate-300 mb-6">
              顧客データ（CSV形式）をアップロードすると、AIが自動的に分析し、
              マーケティングインサイトを生成します。
            </p>

            <div className="flex flex-col items-center p-8 border-2 border-dashed border-white/20 rounded-lg bg-white/5">
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv"
                onChange={handleFileUpload}
                className="hidden"
                id="csv-upload"
                disabled={uploading}
              />
              <label
                htmlFor="csv-upload"
                className={`flex flex-col items-center cursor-pointer ${uploading ? "opacity-50 cursor-not-allowed" : ""}`}
              >
                {uploading ? (
                  <Loader2 className="w-12 h-12 text-purple-400 mb-4 animate-spin" />
                ) : (
                  <Upload className="w-12 h-12 text-slate-400 mb-4" />
                )}
                <span className="text-lg font-medium text-white mb-2">
                  {uploading ? "分析中..." : "CSVファイルを選択"}
                </span>
                <span className="text-sm text-slate-400">
                  またはドラッグ＆ドロップ
                </span>
              </label>
            </div>

            {uploadError && (
              <div className="mt-4 p-4 bg-red-500/20 rounded-lg flex items-center gap-3">
                <AlertCircle className="w-5 h-5 text-red-400" />
                <span className="text-red-300">{uploadError}</span>
              </div>
            )}

            {uploadSuccess && (
              <div className="mt-4 p-4 bg-green-500/20 rounded-lg flex items-center gap-3">
                <CheckCircle className="w-5 h-5 text-green-400" />
                <span className="text-green-300">分析が完了しました</span>
              </div>
            )}
          </div>

          {/* 口コミURL登録セクション */}
          <div className="glass-card p-8 mb-8">
            <div className="flex items-center gap-3 mb-6">
              <Link2 className="w-6 h-6 text-blue-400" />
              <h3 className="text-2xl font-bold text-white">口コミを収集・分析</h3>
            </div>

            <p className="text-slate-400 text-sm mb-6">
              じゃらんやGoogleマップの口コミページURLを登録すると、実際の口コミを収集・分析できます。
            </p>

            <div className="space-y-4 mb-6">
              <div>
                <label className="block text-sm text-slate-300 mb-2">
                  じゃらん 口コミページURL
                </label>
                <input
                  type="url"
                  value={jalanUrl}
                  onChange={(e) => setJalanUrl(e.target.value)}
                  placeholder="https://www.jalan.net/yad??????/kuchikomi/"
                  className="w-full bg-white/5 border border-white/10 rounded-lg p-3 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm text-slate-300 mb-2">
                  Googleマップ 口コミURL
                </label>
                <input
                  type="url"
                  value={googleUrl}
                  onChange={(e) => setGoogleUrl(e.target.value)}
                  placeholder="https://www.google.com/maps/place/..."
                  className="w-full bg-white/5 border border-white/10 rounded-lg p-3 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
                />
              </div>
            </div>

            {urlSaveMessage && (
              <div className={`mb-4 p-3 rounded-lg text-sm ${
                urlSaveMessage.type === "success"
                  ? "bg-green-500/20 text-green-300 border border-green-500/30"
                  : "bg-red-500/20 text-red-300 border border-red-500/30"
              }`}>
                {urlSaveMessage.text}
              </div>
            )}

            <div className="flex gap-4">
              <button
                onClick={handleSaveReviewUrls}
                disabled={savingUrls || (!jalanUrl.trim() && !googleUrl.trim())}
                className="flex-1 bg-blue-600 text-white py-3 rounded-lg hover:bg-blue-700 transition-all font-semibold disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {savingUrls ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    保存中...
                  </>
                ) : (
                  <>
                    <Link2 className="w-5 h-5" />
                    URLを保存
                  </>
                )}
              </button>

              {hasReviewUrls && (
                <button
                  onClick={handleAnalyzeReviews}
                  disabled={analyzingReviews}
                  className="flex-1 bg-gradient-to-r from-blue-500 to-purple-500 text-white py-3 rounded-lg hover:from-blue-600 hover:to-purple-600 transition-all font-semibold disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {analyzingReviews ? (
                    <>
                      <Loader2 className="w-5 h-5 animate-spin" />
                      口コミ収集中...
                    </>
                  ) : (
                    <>
                      <RefreshCw className="w-5 h-5" />
                      口コミを収集・分析
                    </>
                  )}
                </button>
              )}
            </div>

            {/* 登録済みURL表示 */}
            {hasReviewUrls && (
              <div className="mt-6 pt-6 border-t border-white/10">
                <p className="text-sm text-slate-400 mb-3">登録済みURL</p>
                <div className="space-y-2">
                  {reviewUrls.jalan && (
                    <a
                      href={reviewUrls.jalan}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-2 text-sm text-blue-400 hover:text-blue-300"
                    >
                      <ExternalLink className="w-4 h-4" />
                      じゃらん: {reviewUrls.jalan.substring(0, 50)}...
                    </a>
                  )}
                  {reviewUrls.google && (
                    <a
                      href={reviewUrls.google}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-2 text-sm text-blue-400 hover:text-blue-300"
                    >
                      <ExternalLink className="w-4 h-4" />
                      Google: {reviewUrls.google.substring(0, 50)}...
                    </a>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* 口コミ分析結果 */}
          {hasReviewData && (
            <div className="glass-card p-8 mb-8">
              <div className="flex items-center gap-3 mb-6">
                <MessageSquare className="w-6 h-6 text-blue-400" />
                <h3 className="text-2xl font-bold text-white">口コミ分析結果</h3>
                {Boolean((session.reviews_summary as Record<string, unknown>).analyzed_at) && (
                  <span className="text-xs text-slate-500 ml-auto">
                    分析日時: {new Date((session.reviews_summary as Record<string, unknown>).analyzed_at as string).toLocaleString("ja-JP")}
                  </span>
                )}
              </div>

              {/* 収集件数表示 */}
              {Boolean((session.reviews_summary as Record<string, unknown>).total_reviews !== undefined) && (
                <div className="mb-6 p-4 bg-blue-500/10 rounded-lg border border-blue-500/20">
                  <p className="text-sm text-blue-300">
                    収集した口コミ数: <span className="font-bold">{(session.reviews_summary as Record<string, unknown>).total_reviews as number}件</span>
                  </p>
                </div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {Boolean((session.reviews_summary as Record<string, unknown>).positive_themes) && (
                  <div>
                    <p className="text-sm text-green-400 mb-2">好評ポイント</p>
                    <ul className="space-y-1">
                      {((session.reviews_summary as Record<string, unknown>).positive_themes as string[]).map((theme, idx) => (
                        <li key={idx} className="text-slate-300 text-sm">• {theme}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {Boolean((session.reviews_summary as Record<string, unknown>).negative_themes) && (
                  <div>
                    <p className="text-sm text-red-400 mb-2">不評ポイント</p>
                    <ul className="space-y-1">
                      {((session.reviews_summary as Record<string, unknown>).negative_themes as string[]).map((theme, idx) => (
                        <li key={idx} className="text-slate-300 text-sm">• {theme}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {Boolean((session.reviews_summary as Record<string, unknown>).guest_expectations) && (
                  <div>
                    <p className="text-sm text-yellow-400 mb-2">お客様の期待</p>
                    <ul className="space-y-1">
                      {((session.reviews_summary as Record<string, unknown>).guest_expectations as string[]).map((exp, idx) => (
                        <li key={idx} className="text-slate-300 text-sm">• {exp}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* 顧客データ分析結果セクション */}
          {hasCustomerData && (
            <div className="glass-card p-8">
              <div className="flex items-center gap-3 mb-6">
                <Users className="w-6 h-6 text-purple-400" />
                <h3 className="text-2xl font-bold text-white">顧客データ分析結果</h3>
              </div>

              {/* インサイト */}
              {session?.csv_insights && (
                <div className="mb-8">
                  <h4 className="text-lg font-semibold text-white mb-4">AIインサイト</h4>
                  <div className="p-6 bg-white/5 rounded-lg border border-white/10 prose prose-invert prose-sm max-w-none
                    prose-headings:text-white prose-headings:font-semibold prose-headings:mt-4 prose-headings:mb-2
                    prose-p:text-slate-300 prose-p:my-2
                    prose-ul:text-slate-300 prose-ul:my-2 prose-ul:list-disc prose-ul:pl-4
                    prose-ol:text-slate-300 prose-ol:my-2 prose-ol:list-decimal prose-ol:pl-4
                    prose-li:text-slate-300 prose-li:my-1
                    prose-strong:text-white prose-strong:font-semibold
                    prose-code:text-cyan-400 prose-code:bg-white/10 prose-code:px-1 prose-code:py-0.5 prose-code:rounded
                    prose-table:border-collapse prose-th:text-slate-300 prose-th:border prose-th:border-white/20 prose-th:p-2
                    prose-td:text-slate-300 prose-td:border prose-td:border-white/20 prose-td:p-2
                    prose-blockquote:border-l-purple-500 prose-blockquote:text-slate-400
                    prose-hr:border-white/20
                  ">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {session.csv_insights}
                    </ReactMarkdown>
                  </div>
                </div>
              )}

              {/* 統計情報 */}
              <div>
                <h4 className="text-lg font-semibold text-white mb-4">統計データ</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {Object.entries(session?.csv_statistics || {}).map(([key, value]) => (
                    <StatCard key={key} statKey={key} value={value} />
                  ))}
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </section>
  );
}


