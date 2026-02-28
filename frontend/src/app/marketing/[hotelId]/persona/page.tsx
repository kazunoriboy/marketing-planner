"use client";

import { useEffect, useState, useRef } from "react";
import { createPortal } from "react-dom";
import { Upload, Users, Loader2, CheckCircle, AlertCircle, Calendar, TrendingUp, BarChart3, Clock, Star, DollarSign, FileText, Link2, ExternalLink, RefreshCw, MessageSquare, Sparkles, User, Briefcase, Target, Heart, Wallet, Search, AlertTriangle, MapPin, Edit3, X, Send, Trash2, History, ChevronDown, ChevronUp } from "lucide-react";
import { useHotel } from "@/lib/hotel-context";
import { marketingApi, AnalysisSession, ReviewUrlsUpdate, Persona, CSVUploadHistory } from "@/lib/api";
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
  guest_area_stats: { label: "予約者エリア統計", icon: MapPin },
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
  const [areaViewMode, setAreaViewMode] = useState<"region" | "prefecture">("region");
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

      // cancellation_stats - 複数の形式に対応
      if (statKey === "cancellation_stats") {
        // 新形式 (total_bookings) または旧形式 (confirmed_count + cancelled_count) に対応
        const totalBookings = (obj.total_bookings as number) ?? 
          ((obj.confirmed_count as number ?? 0) + (obj.cancelled_count as number ?? 0));
        const cancelledBookings = (obj.cancelled_bookings as number) ?? (obj.cancelled_count as number);
        // cancellation_rate は 0.0-1.0 または cancellation_rate_percent (0-100) に対応
        let cancellationRate = obj.cancellation_rate as number | undefined;
        if (cancellationRate === undefined && obj.cancellation_rate_percent !== undefined) {
          cancellationRate = (obj.cancellation_rate_percent as number) / 100;
        }
        
        return (
          <div className="space-y-1">
            {totalBookings > 0 && (
              <p className="text-white">
                <span className="text-slate-400 text-sm">総予約数: </span>
                {formatNumber(totalBookings)}
              </p>
            )}
            {cancelledBookings !== undefined && (
              <p className="text-white">
                <span className="text-slate-400 text-sm">キャンセル数: </span>
                {formatNumber(cancelledBookings)}
              </p>
            )}
            {cancellationRate !== undefined && (
              <p className="text-white">
                <span className="text-slate-400 text-sm">キャンセル率: </span>
                <span className="text-red-400 font-semibold">
                  {formatPercent(cancellationRate)}
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
            {obj.note != null && (
              <p className="text-slate-600 text-xs pt-2 border-t border-white/10">※{String(obj.note)}</p>
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
            {obj.note != null && (
              <p className="text-slate-600 text-xs">※{String(obj.note)}</p>
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

      // top_plans - プラン名と件数（リスト形式・辞書形式の両方に対応）
      if (statKey === "top_plans") {
        // データを正規化: [{name: string, count: number}] の形式に変換
        let planEntries: { name: string; count: number }[] = [];
        
        if (Array.isArray(value)) {
          // リスト形式: [{"plan_name": "...", "count": ...}]
          planEntries = (value as Array<{ plan_name?: string; name?: string; count?: number }>)
            .map((item) => ({
              name: item.plan_name || item.name || "",
              count: item.count || 0,
            }))
            .filter((item) => item.name)
            .slice(0, 5);
        } else {
          // 辞書形式: {"プラン名": 件数}
          planEntries = Object.entries(obj)
            .map(([name, count]) => ({
              name,
              count: typeof count === "number" ? count : 0,
            }))
            .filter((item) => item.name && typeof item.count === "number")
            .slice(0, 5);
        }
        
        return (
          <div className="space-y-2">
            {planEntries.map((plan, index) => (
              <div key={plan.name} className="flex items-start gap-2">
                <span className="text-purple-400 font-bold text-sm min-w-[20px]">
                  {index + 1}.
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-white text-sm truncate" title={plan.name}>
                    {plan.name}
                  </p>
                  <p className="text-slate-400 text-xs">{formatNumber(plan.count)}件</p>
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

      // guest_area_stats - 予約者エリア統計
      if (statKey === "guest_area_stats") {
        const regionDist = (obj.region_distribution as Record<string, number>) || {};
        const prefectureDist = (obj.prefecture_distribution as Record<string, number>) || {};
        const overseasDist = (obj.overseas_distribution as Record<string, number>) || {};
        const domesticCount = (obj.domestic_count as number) || 0;
        const overseasCount = (obj.overseas_count as number) || 0;
        
        // 表示する国内データを選択
        const domesticData = areaViewMode === "region" ? regionDist : prefectureDist;
        const domesticLabel = areaViewMode === "region" ? "地方別" : "都道府県別";
        
        return (
          <div className="space-y-3">
            {/* 国内/海外の割合 */}
            {(domesticCount > 0 || overseasCount > 0) && (
              <div className="flex gap-4 mb-2">
                <div className="flex-1 p-2 bg-blue-500/10 rounded-lg border border-blue-500/20">
                  <p className="text-blue-400 text-xs mb-1">国内</p>
                  <p className="text-white font-bold text-lg">{formatNumber(domesticCount)}件</p>
                </div>
                <div className="flex-1 p-2 bg-amber-500/10 rounded-lg border border-amber-500/20">
                  <p className="text-amber-400 text-xs mb-1">海外</p>
                  <p className="text-white font-bold text-lg">{formatNumber(overseasCount)}件</p>
                </div>
              </div>
            )}
            
            {/* 地方別/都道府県別 切り替えボタン */}
            {(Object.keys(regionDist).length > 0 || Object.keys(prefectureDist).length > 0) && (
              <div className="flex gap-1 p-1 bg-white/5 rounded-lg">
                <button
                  onClick={() => setAreaViewMode("region")}
                  className={`flex-1 px-2 py-1 text-xs rounded transition-colors ${
                    areaViewMode === "region"
                      ? "bg-cyan-500/20 text-cyan-400 font-medium"
                      : "text-slate-400 hover:text-slate-300"
                  }`}
                >
                  地方別
                </button>
                <button
                  onClick={() => setAreaViewMode("prefecture")}
                  className={`flex-1 px-2 py-1 text-xs rounded transition-colors ${
                    areaViewMode === "prefecture"
                      ? "bg-cyan-500/20 text-cyan-400 font-medium"
                      : "text-slate-400 hover:text-slate-300"
                  }`}
                >
                  都道府県別
                </button>
              </div>
            )}
            
            {/* 国内分布（地方別 or 都道府県別） */}
            {Object.keys(domesticData).length > 0 && (
              <div>
                <p className="text-cyan-400 text-xs mb-2">▼ 国内 {domesticLabel}予約数</p>
                <div className="space-y-1 max-h-48 overflow-y-auto">
                  {Object.entries(domesticData)
                    .sort((a, b) => b[1] - a[1])
                    .map(([area, count]) => (
                      <div key={area} className="flex justify-between items-center">
                        <span className="text-slate-400 text-sm">{area}</span>
                        <span className="text-white font-medium">{formatNumber(count)}</span>
                      </div>
                    ))}
                </div>
              </div>
            )}
            
            {/* 海外の国別分布 */}
            {Object.keys(overseasDist).length > 0 && (
              <div className="pt-2 border-t border-white/10">
                <p className="text-amber-400 text-xs mb-2">▼ 海外 国別予約数</p>
                <div className="space-y-1">
                  {Object.entries(overseasDist)
                    .sort((a, b) => b[1] - a[1])
                    .map(([country, count]) => (
                      <div key={country} className="flex justify-between items-center">
                        <span className="text-slate-400 text-sm">{country}</span>
                        <span className="text-white font-medium">{formatNumber(count)}</span>
                      </div>
                    ))}
                </div>
              </div>
            )}
            
            {/* 統計サマリー */}
            {obj.total_unique_areas !== undefined && (
              <p className="text-slate-500 text-xs pt-2 border-t border-white/10">
                {formatNumber(obj.total_records_with_area as number)}件中 {formatNumber(obj.total_unique_areas as number)}エリアから予約
                {obj.note != null && <span className="block text-slate-600 text-xs mt-1">※{String(obj.note)}</span>}
              </p>
            )}
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

  // カードサイズを決定（top_plans, weekday_occupancy, guest_stats, price_stats, guest_area_statsは大きめ）
  const isLargeCard = ["top_plans", "weekday_occupancy", "schema_mapping", "guest_stats", "price_stats", "guest_area_stats"].includes(statKey);

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

// ペルソナカードコンポーネント
interface PersonaCardProps {
  persona: Persona;
  index: number;
  onEdit: (index: number, instruction: string) => Promise<void>;
  isEditing: boolean;
}

function PersonaCard({ persona, index, onEdit, isEditing }: PersonaCardProps) {
  const [showEditModal, setShowEditModal] = useState(false);
  const [editInstruction, setEditInstruction] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // 性別に応じた背景色のグラデーション
  const gradients = [
    "from-purple-500/20 to-pink-500/20",
    "from-blue-500/20 to-cyan-500/20",
    "from-amber-500/20 to-orange-500/20",
  ];
  const borderColors = [
    "border-purple-500/30",
    "border-blue-500/30",
    "border-amber-500/30",
  ];
  const textColors = [
    "text-purple-400",
    "text-blue-400",
    "text-amber-400",
  ];
  const buttonColors = [
    "bg-purple-500 hover:bg-purple-600",
    "bg-blue-500 hover:bg-blue-600",
    "bg-amber-500 hover:bg-amber-600",
  ];

  const handleSubmitEdit = async () => {
    if (!editInstruction.trim()) return;
    setSubmitting(true);
    try {
      await onEdit(index, editInstruction);
      setShowEditModal(false);
      setEditInstruction("");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <div className={`bg-gradient-to-br ${gradients[index % 3]} rounded-xl p-6 border ${borderColors[index % 3]} transition-all hover:shadow-lg relative ${isEditing ? "opacity-50 pointer-events-none" : ""}`}>
        {/* 修正ボタン */}
        <button
          onClick={() => setShowEditModal(true)}
          disabled={isEditing}
          className={`absolute top-4 right-4 p-2 rounded-lg ${buttonColors[index % 3]} text-white transition-all hover:scale-105 disabled:opacity-50`}
          title="このペルソナを修正"
        >
          <Edit3 className="w-4 h-4" />
        </button>

        {/* ヘッダー */}
        <div className="flex items-start gap-4 mb-5 pr-10">
          <div className={`w-16 h-16 rounded-full bg-gradient-to-br ${gradients[index % 3]} flex items-center justify-center border-2 ${borderColors[index % 3]}`}>
            <User className={`w-8 h-8 ${textColors[index % 3]}`} />
          </div>
          <div className="flex-1">
            <h4 className="text-xl font-bold text-white mb-1">{persona.name}</h4>
            <div className="flex flex-wrap gap-2 text-sm">
              <span className="px-2 py-0.5 bg-white/10 rounded-full text-slate-300">{persona.age_range}</span>
              <span className="px-2 py-0.5 bg-white/10 rounded-full text-slate-300">{persona.gender}</span>
            </div>
          </div>
        </div>

        {/* 住んでいるところ */}
        {persona.location && (
          <div className="mb-4">
            <div className="flex items-center gap-2 mb-2">
              <MapPin className="w-4 h-4 text-slate-400" />
              <span className="text-sm text-slate-400">住んでいるところ</span>
            </div>
            <p className="text-white">{persona.location}</p>
          </div>
        )}

        {/* 職業 */}
        <div className="mb-4">
          <div className="flex items-center gap-2 mb-2">
            <Briefcase className="w-4 h-4 text-slate-400" />
            <span className="text-sm text-slate-400">職業</span>
          </div>
          <p className="text-white font-medium">{persona.occupation}</p>
        </div>

        {/* 旅行目的 */}
        <div className="mb-4">
          <div className="flex items-center gap-2 mb-2">
            <Target className="w-4 h-4 text-slate-400" />
            <span className="text-sm text-slate-400">旅行目的</span>
          </div>
          <p className="text-white">{persona.travel_purpose}</p>
        </div>

        {/* 価値観 */}
        <div className="mb-4">
          <div className="flex items-center gap-2 mb-2">
            <Heart className="w-4 h-4 text-slate-400" />
            <span className="text-sm text-slate-400">重視すること</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {persona.values.map((value, i) => (
              <span key={i} className={`px-2 py-1 bg-white/10 rounded text-sm ${textColors[index % 3]}`}>
                {value}
              </span>
            ))}
          </div>
        </div>

        {/* 予算 */}
        <div className="mb-4">
          <div className="flex items-center gap-2 mb-2">
            <Wallet className="w-4 h-4 text-slate-400" />
            <span className="text-sm text-slate-400">予算帯</span>
          </div>
          <p className="text-white font-semibold">{persona.budget_range}</p>
        </div>

        {/* 情報収集方法 */}
        <div className="mb-4">
          <div className="flex items-center gap-2 mb-2">
            <Search className="w-4 h-4 text-slate-400" />
            <span className="text-sm text-slate-400">情報収集方法</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {persona.information_source.map((source, i) => (
              <span key={i} className="px-2 py-1 bg-white/5 rounded text-sm text-slate-300">
                {source}
              </span>
            ))}
          </div>
        </div>

        {/* 宿泊施設に求めること */}
        <div className="mb-4">
          <div className="flex items-center gap-2 mb-2">
            <Star className="w-4 h-4 text-slate-400" />
            <span className="text-sm text-slate-400">宿泊施設に求めること</span>
          </div>
          <ul className="space-y-1">
            {persona.needs.map((need, i) => (
              <li key={i} className="text-slate-300 text-sm flex items-start gap-2">
                <span className={textColors[index % 3]}>•</span>
                {need}
              </li>
            ))}
          </ul>
        </div>

        {/* 悩み・課題 */}
        <div className="mb-4">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle className="w-4 h-4 text-slate-400" />
            <span className="text-sm text-slate-400">悩み・課題</span>
          </div>
          <ul className="space-y-1">
            {persona.pain_points.map((point, i) => (
              <li key={i} className="text-slate-400 text-sm flex items-start gap-2">
                <span className="text-red-400">•</span>
                {point}
              </li>
            ))}
          </ul>
        </div>

        {/* 詳細説明 */}
        <div className="pt-4 border-t border-white/10">
          <p className="text-slate-300 text-sm leading-relaxed">{persona.description}</p>
        </div>

        {/* 根拠 */}
        {persona.rationale && (
          <div className="mt-4 pt-4 border-t border-white/10">
            <div className="flex items-center gap-2 mb-2">
              <FileText className="w-4 h-4 text-slate-400" />
              <span className="text-sm text-slate-400">このペルソナを作成した根拠</span>
            </div>
            <p className="text-slate-400 text-sm leading-relaxed bg-white/5 rounded-lg p-3 italic">
              {persona.rationale}
            </p>
          </div>
        )}

        {/* ローディングオーバーレイ */}
        {isEditing && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/50 rounded-xl">
            <div className="flex items-center gap-3 text-white">
              <Loader2 className="w-6 h-6 animate-spin" />
              <span>修正中...</span>
            </div>
          </div>
        )}
      </div>

      {/* 修正モーダル - Portalを使用してbody直下にレンダリング */}
      {showEditModal && typeof document !== "undefined" && createPortal(
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70">
          <div className={`bg-slate-900 rounded-xl p-6 max-w-lg w-full border ${borderColors[index % 3]}`}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Edit3 className={`w-5 h-5 ${textColors[index % 3]}`} />
                ペルソナを修正: {persona.name}
              </h3>
              <button
                onClick={() => setShowEditModal(false)}
                className="p-1 text-slate-400 hover:text-white transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-slate-400 text-sm mb-4">
              このペルソナに対する修正指示を入力してください。AIが指示に従ってペルソナを修正します。
            </p>

            <textarea
              value={editInstruction}
              onChange={(e) => setEditInstruction(e.target.value)}
              placeholder="例: もっと若い世代にしてほしい、予算を高めに設定してほしい、旅行目的をビジネス出張に変えてほしい..."
              className="w-full h-32 bg-white/5 border border-white/10 rounded-lg p-3 text-white placeholder-slate-500 focus:outline-none focus:border-purple-500 resize-none"
              disabled={submitting}
            />

            <div className="flex gap-3 mt-4">
              <button
                onClick={() => setShowEditModal(false)}
                disabled={submitting}
                className="flex-1 py-2 px-4 rounded-lg border border-white/20 text-white hover:bg-white/10 transition-colors disabled:opacity-50"
              >
                キャンセル
              </button>
              <button
                onClick={handleSubmitEdit}
                disabled={submitting || !editInstruction.trim()}
                className={`flex-1 py-2 px-4 rounded-lg ${buttonColors[index % 3]} text-white transition-colors disabled:opacity-50 flex items-center justify-center gap-2`}
              >
                {submitting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    修正中...
                  </>
                ) : (
                  <>
                    <Send className="w-4 h-4" />
                    修正を実行
                  </>
                )}
              </button>
            </div>
          </div>
        </div>,
        document.body
      )}
    </>
  );
}

export default function PersonaPage() {
  const { hotel, hotelId } = useHotel();
  const [session, setSession] = useState<AnalysisSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [periodOverlapWarning, setPeriodOverlapWarning] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // CSV履歴関連のstate
  const [csvHistories, setCsvHistories] = useState<CSVUploadHistory[]>([]);
  const [showCsvHistory, setShowCsvHistory] = useState(false);
  const [deletingHistoryId, setDeletingHistoryId] = useState<number | null>(null);

  // 口コミURL関連のstate
  const [reviewUrls, setReviewUrls] = useState<Record<string, string>>({});
  const [jalanUrl, setJalanUrl] = useState("");
  const [savingUrls, setSavingUrls] = useState(false);
  const [analyzingReviews, setAnalyzingReviews] = useState(false);
  const [urlSaveMessage, setUrlSaveMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // ペルソナ関連のstate
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [generatingPersonas, setGeneratingPersonas] = useState(false);
  const [personaError, setPersonaError] = useState<string | null>(null);
  const [editingPersonaIndex, setEditingPersonaIndex] = useState<number | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        const [sessionData, urlsData, personasData, historyData] = await Promise.all([
          marketingApi.getAnalysisSession(hotelId),
          marketingApi.getReviewUrls(hotelId).catch(() => null),
          marketingApi.getPersonas(hotelId).catch(() => null),
          marketingApi.getCSVUploadHistory(hotelId).catch(() => null),
        ]);
        setSession(sessionData);
        if (urlsData?.review_urls) {
          setReviewUrls(urlsData.review_urls);
          setJalanUrl(urlsData.review_urls.jalan || "");
        }
        if (personasData?.personas) {
          setPersonas(personasData.personas);
        }
        if (historyData?.histories) {
          setCsvHistories(historyData.histories);
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
    setPeriodOverlapWarning(null);

    try {
      const result = await marketingApi.analyzeCustomerCSV(hotelId, file);
      setSession((prev) => prev ? {
        ...prev,
        session_id: result.session_id,
        csv_statistics: result.statistics,
        csv_insights: result.insights,
      } : null);
      setUploadSuccess(true);
      
      // 期間重複警告があれば表示
      if (result.period_overlap_warning) {
        setPeriodOverlapWarning(result.period_overlap_warning);
      }
      
      // Reload full session data and CSV history
      const [sessionData, historyData] = await Promise.all([
        marketingApi.getAnalysisSession(hotelId),
        marketingApi.getCSVUploadHistory(hotelId),
      ]);
      setSession(sessionData);
      if (historyData?.histories) {
        setCsvHistories(historyData.histories);
      }
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

  // CSV履歴を削除
  const handleDeleteCsvHistory = async (historyId: number) => {
    if (!confirm("このCSVデータを削除しますか？統計情報が再計算されます。")) return;
    
    setDeletingHistoryId(historyId);
    try {
      const result = await marketingApi.deleteCSVUploadHistory(hotelId, historyId);
      
      // 履歴リストから削除
      setCsvHistories(prev => prev.filter(h => h.id !== historyId));
      
      // セッションの統計を更新
      setSession(prev => prev ? {
        ...prev,
        csv_statistics: result.statistics,
      } : null);
      
      // セッションデータを再読み込み
      const sessionData = await marketingApi.getAnalysisSession(hotelId);
      setSession(sessionData);
    } catch (error) {
      console.error("Delete failed:", error);
      alert("削除に失敗しました");
    } finally {
      setDeletingHistoryId(null);
    }
  };

  const handleSaveReviewUrls = async () => {
    setSavingUrls(true);
    setUrlSaveMessage(null);
    try {
      const urls: ReviewUrlsUpdate = {};
      if (jalanUrl.trim()) urls.jalan = jalanUrl.trim();

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

  const handleGeneratePersonas = async () => {
    setGeneratingPersonas(true);
    setPersonaError(null);
    try {
      const result = await marketingApi.generatePersonas(hotelId, 3);
      setPersonas(result.personas);
    } catch (error) {
      console.error("Persona generation failed:", error);
      setPersonaError(
        error instanceof Error ? error.message : "ペルソナの生成に失敗しました"
      );
    } finally {
      setGeneratingPersonas(false);
    }
  };

  const handleEditPersona = async (personaIndex: number, instruction: string) => {
    setEditingPersonaIndex(personaIndex);
    setPersonaError(null);
    try {
      const result = await marketingApi.editPersona(hotelId, personaIndex, instruction);
      // ペルソナを更新
      setPersonas((prev) => {
        const updated = [...prev];
        updated[personaIndex] = result.persona;
        return updated;
      });
    } catch (error) {
      console.error("Persona edit failed:", error);
      setPersonaError(
        error instanceof Error ? error.message : "ペルソナの修正に失敗しました"
      );
    } finally {
      setEditingPersonaIndex(null);
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

            {periodOverlapWarning && (
              <div className="mt-4 p-4 bg-yellow-500/20 rounded-lg flex items-start gap-3">
                <AlertTriangle className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" />
                <div>
                  <span className="text-yellow-300 font-medium">データ期間の重複</span>
                  <p className="text-yellow-200/80 text-sm mt-1">{periodOverlapWarning}</p>
                  <p className="text-yellow-200/60 text-xs mt-1">重複データがある場合、統計が正確でない可能性があります。不要なデータは下の履歴から削除できます。</p>
                </div>
              </div>
            )}

            {/* CSVアップロード履歴 */}
            {csvHistories.length > 0 && (
              <div className="mt-6 pt-6 border-t border-white/10">
                <button
                  onClick={() => setShowCsvHistory(!showCsvHistory)}
                  className="flex items-center gap-2 text-slate-300 hover:text-white transition-colors"
                >
                  <History className="w-4 h-4" />
                  <span className="text-sm font-medium">
                    アップロード履歴（{csvHistories.length}件）
                  </span>
                  {showCsvHistory ? (
                    <ChevronUp className="w-4 h-4" />
                  ) : (
                    <ChevronDown className="w-4 h-4" />
                  )}
                </button>

                {showCsvHistory && (
                  <div className="mt-4 space-y-2">
                    {csvHistories.map((history) => (
                      <div
                        key={history.id}
                        className="flex items-center justify-between p-3 bg-white/5 rounded-lg border border-white/10"
                      >
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <FileText className="w-4 h-4 text-slate-400 flex-shrink-0" />
                            <span className="text-white text-sm truncate">
                              {history.filename}
                            </span>
                            {history.is_migrated && (
                              <span className="px-2 py-0.5 bg-purple-500/20 text-purple-300 text-xs rounded">
                                移行データ
                              </span>
                            )}
                          </div>
                          <div className="flex items-center gap-4 mt-1 text-xs text-slate-400">
                            <span>{new Date(history.upload_date).toLocaleDateString("ja-JP")}</span>
                            <span>{history.record_count.toLocaleString()}件</span>
                            {history.data_period_start && history.data_period_end && (
                              <span>
                                {new Date(history.data_period_start).toLocaleDateString("ja-JP")}
                                〜
                                {new Date(history.data_period_end).toLocaleDateString("ja-JP")}
                              </span>
                            )}
                          </div>
                        </div>
                        <button
                          onClick={() => handleDeleteCsvHistory(history.id)}
                          disabled={deletingHistoryId === history.id}
                          className="p-2 text-slate-400 hover:text-red-400 transition-colors disabled:opacity-50"
                          title="削除"
                        >
                          {deletingHistoryId === history.id ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <Trash2 className="w-4 h-4" />
                          )}
                        </button>
                      </div>
                    ))}
                    <p className="text-xs text-slate-500 mt-2">
                      ※ 複数のCSVデータは自動的に合算されて統計が計算されます
                    </p>
                  </div>
                )}
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
              じゃらんの口コミページURLを登録すると、実際の口コミを収集・分析できます。
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
                disabled={savingUrls || !jalanUrl.trim()}
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
            <div className="glass-card p-8 mb-8">
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

          {/* ペルソナ生成セクション */}
          <div className="glass-card p-8 mb-8">
            <div className="flex items-center gap-3 mb-6">
              <Sparkles className="w-6 h-6 text-yellow-400" />
              <h3 className="text-2xl font-bold text-white">ペルソナを作成</h3>
            </div>

            <p className="text-slate-300 mb-6">
              顧客データと口コミ分析の結果をもとに、AIがターゲット顧客のペルソナ（架空の顧客像）を3つ生成します。
              ペルソナを活用することで、より効果的なマーケティング戦略を立てることができます。
            </p>

            {/* 生成に必要なデータがあるか確認 */}
            {!hasCustomerData && !hasReviewData ? (
              <div className="p-4 bg-yellow-500/10 rounded-lg border border-yellow-500/20 mb-6">
                <div className="flex items-center gap-3">
                  <AlertCircle className="w-5 h-5 text-yellow-400" />
                  <p className="text-yellow-300 text-sm">
                    ペルソナを生成するには、先に顧客データ（CSV）または口コミの分析を行ってください。
                  </p>
                </div>
              </div>
            ) : (
              <div className="p-4 bg-green-500/10 rounded-lg border border-green-500/20 mb-6">
                <div className="flex items-center gap-3">
                  <CheckCircle className="w-5 h-5 text-green-400" />
                  <div className="text-green-300 text-sm">
                    <p className="font-medium">分析データが利用可能です</p>
                    <p className="text-green-400/80 mt-1">
                      {hasCustomerData && "顧客データ "}
                      {hasCustomerData && hasReviewData && "・ "}
                      {hasReviewData && "口コミ分析"}
                      のデータをもとにペルソナを生成します。
                    </p>
                  </div>
                </div>
              </div>
            )}

            {personaError && (
              <div className="mb-6 p-4 bg-red-500/20 rounded-lg flex items-center gap-3">
                <AlertCircle className="w-5 h-5 text-red-400" />
                <span className="text-red-300">{personaError}</span>
              </div>
            )}

            <button
              onClick={handleGeneratePersonas}
              disabled={generatingPersonas || (!hasCustomerData && !hasReviewData)}
              className="w-full bg-gradient-to-r from-yellow-500 to-orange-500 text-white py-4 rounded-lg hover:from-yellow-600 hover:to-orange-600 transition-all font-semibold disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-3 text-lg"
            >
              {generatingPersonas ? (
                <>
                  <Loader2 className="w-6 h-6 animate-spin" />
                  ペルソナを生成中...（30秒ほどかかります）
                </>
              ) : personas.length > 0 ? (
                <>
                  <RefreshCw className="w-6 h-6" />
                  ペルソナを再生成
                </>
              ) : (
                <>
                  <Sparkles className="w-6 h-6" />
                  ペルソナを生成する
                </>
              )}
            </button>
          </div>

          {/* 生成されたペルソナ表示セクション */}
          {personas.length > 0 && (
            <div className="glass-card p-8">
              <div className="flex items-center gap-3 mb-6">
                <Users className="w-6 h-6 text-cyan-400" />
                <h3 className="text-2xl font-bold text-white">生成されたペルソナ</h3>
                <span className="ml-auto text-sm text-slate-400">
                  {personas.length}人のペルソナ
                </span>
              </div>

              <p className="text-slate-400 mb-8">
                分析データに基づいて生成された、ターゲット顧客の代表的なペルソナです。
                各ペルソナの右上にある<Edit3 className="w-4 h-4 inline mx-1 text-slate-400" />ボタンで修正できます。
              </p>

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {personas.map((persona, index) => (
                  <PersonaCard
                    key={index}
                    persona={persona}
                    index={index}
                    onEdit={handleEditPersona}
                    isEditing={editingPersonaIndex === index}
                  />
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </section>
  );
}


