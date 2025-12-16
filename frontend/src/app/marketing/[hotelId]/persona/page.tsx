"use client";

import { useEffect, useState, useRef } from "react";
import { Upload, Users, Loader2, CheckCircle, AlertCircle, Calendar, TrendingUp, BarChart3, Clock, Star, DollarSign, FileText } from "lucide-react";
import { useHotel } from "@/lib/hotel-context";
import { marketingApi, AnalysisSession, CSVAnalysisResponse } from "@/lib/api";

// 統計カードのラベル定義
const STAT_LABELS: Record<string, { label: string; icon: React.ElementType }> = {
  total_records: { label: "総レコード数", icon: FileText },
  schema_mapping: { label: "データ項目マッピング", icon: FileText },
  date_range: { label: "データ期間", icon: Calendar },
  cancellation_stats: { label: "キャンセル統計", icon: TrendingUp },
  average_lead_time: { label: "平均リードタイム", icon: Clock },
  top_plans: { label: "人気プランTOP5", icon: Star },
  weekday_occupancy: { label: "曜日別予約数", icon: BarChart3 },
  price_stats: { label: "価格統計", icon: DollarSign },
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

      // price_stats
      if (statKey === "price_stats") {
        return (
          <div className="space-y-1">
            {obj.average !== undefined && (
              <p className="text-white">
                <span className="text-slate-400 text-sm">平均: </span>
                ¥{formatNumber(Math.round(obj.average as number))}
              </p>
            )}
            {obj.median !== undefined && (
              <p className="text-white">
                <span className="text-slate-400 text-sm">中央値: </span>
                ¥{formatNumber(Math.round(obj.median as number))}
              </p>
            )}
            {obj.min !== undefined && (
              <p className="text-white">
                <span className="text-slate-400 text-sm">最小: </span>
                ¥{formatNumber(obj.min as number)}
              </p>
            )}
            {obj.max !== undefined && (
              <p className="text-white">
                <span className="text-slate-400 text-sm">最大: </span>
                ¥{formatNumber(obj.max as number)}
              </p>
            )}
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

  // カードサイズを決定（top_plansとweekday_occupancyは大きめ）
  const isLargeCard = ["top_plans", "weekday_occupancy", "schema_mapping"].includes(statKey);

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

  const hasCustomerData = session?.csv_statistics && Object.keys(session.csv_statistics).length > 0;

  return (
    <section className="animate-fadeIn">
      <h2 className="text-3xl font-bold text-white mb-2">顧客を知る</h2>
      <p className="text-slate-400 mb-8">
        {hotel.name}の顧客データを分析し、ターゲット顧客を特定します
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

          {/* 分析結果セクション */}
          {hasCustomerData && (
            <div className="glass-card p-8">
              <div className="flex items-center gap-3 mb-6">
                <Users className="w-6 h-6 text-purple-400" />
                <h3 className="text-2xl font-bold text-white">顧客分析結果</h3>
              </div>

              {/* インサイト */}
              {session?.csv_insights && (
                <div className="mb-8">
                  <h4 className="text-lg font-semibold text-white mb-4">AIインサイト</h4>
                  <div className="p-6 bg-white/5 rounded-lg border border-white/10">
                    <p className="text-slate-300 whitespace-pre-wrap">
                      {session.csv_insights}
                    </p>
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
