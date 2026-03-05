"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  facilityApi,
  HotelDetail,
  HotelDetailAttraction,
  ApiError,
} from "@/lib/api";
import {
  ArrowLeft,
  Plus,
  Trash2,
  Loader2,
  Save,
  CheckCircle,
  Wand2,
  TrendingUp,
} from "lucide-react";

const DEFAULT_DETAIL: HotelDetail = {
  story: "",
  highlights: [],
  surrounding: {
    description: "",
    attractions: [],
  },
  access: "",
};

export default function HotelInfoPage() {
  const params = useParams();
  const hotelId = Number(params.hotelId);

  const [detail, setDetail] = useState<HotelDetail>(DEFAULT_DETAIL);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [autoFilling, setAutoFilling] = useState(false);
  const [fillingFromMarket, setFillingFromMarket] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ハイライト入力用
  const [highlightInput, setHighlightInput] = useState("");

  const loadDetail = useCallback(async () => {
    setLoading(true);
    try {
      const data = await facilityApi.getHotelDetail(hotelId);
      setDetail({
        story: data.story || "",
        highlights: data.highlights || [],
        surrounding: {
          description: data.surrounding?.description || "",
          attractions: data.surrounding?.attractions || [],
        },
        access: data.access || "",
      });
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setDetail(DEFAULT_DETAIL);
      } else {
        setError("宿情報の取得に失敗しました");
      }
    } finally {
      setLoading(false);
    }
  }, [hotelId]);

  useEffect(() => {
    loadDetail();
  }, [loadDetail]);

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      await facilityApi.updateHotelDetail(hotelId, detail);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch {
      setError("保存に失敗しました。もう一度お試しください。");
    } finally {
      setSaving(false);
    }
  };

  const handleAutoFill = async () => {
    setAutoFilling(true);
    setError(null);
    try {
      const result = await facilityApi.autoFillHotelDetail(hotelId);
      setDetail((prev) => ({
        ...prev,
        highlights:
          result.highlights.length > 0 ? result.highlights : prev.highlights,
        surrounding: {
          description:
            result.surrounding.description || prev.surrounding.description,
          attractions:
            result.surrounding.attractions.length > 0
              ? result.surrounding.attractions
              : prev.surrounding.attractions,
        },
        access: result.access || prev.access,
      }));
    } catch (err) {
      if (err instanceof ApiError && err.status === 400) {
        setError(
          "公式サイトのURLが設定されていません。ホテル設定から追加してください。"
        );
      } else {
        setError("公式サイトからの情報取得に失敗しました。");
      }
    } finally {
      setAutoFilling(false);
    }
  };

  const handleFillFromMarket = async () => {
    setFillingFromMarket(true);
    setError(null);
    try {
      const result = await facilityApi.fillSurroundingFromMarket(hotelId);
      setDetail((prev) => ({
        ...prev,
        surrounding: {
          description:
            result.surrounding.description || prev.surrounding.description,
          attractions:
            result.surrounding.attractions.length > 0
              ? result.surrounding.attractions
              : prev.surrounding.attractions,
        },
      }));
    } catch (err) {
      if (err instanceof ApiError && err.status === 400) {
        setError(
          "市場分析データがありません。マーケティングAIの「市場を知る」で先に分析を実行してください。"
        );
      } else {
        setError("市場データからの情報取得に失敗しました。");
      }
    } finally {
      setFillingFromMarket(false);
    }
  };

  const addHighlight = () => {
    const trimmed = highlightInput.trim();
    if (!trimmed) return;
    setDetail((prev) => ({
      ...prev,
      highlights: [...prev.highlights, trimmed],
    }));
    setHighlightInput("");
  };

  const removeHighlight = (index: number) => {
    setDetail((prev) => ({
      ...prev,
      highlights: prev.highlights.filter((_, i) => i !== index),
    }));
  };

  const addAttraction = () => {
    setDetail((prev) => ({
      ...prev,
      surrounding: {
        ...prev.surrounding,
        attractions: [
          ...prev.surrounding.attractions,
          { name: "", distance: "" },
        ],
      },
    }));
  };

  const updateAttraction = (
    index: number,
    field: keyof HotelDetailAttraction,
    value: string
  ) => {
    setDetail((prev) => {
      const updated = prev.surrounding.attractions.map((a, i) =>
        i === index ? { ...a, [field]: value } : a
      );
      return {
        ...prev,
        surrounding: { ...prev.surrounding, attractions: updated },
      };
    });
  };

  const removeAttraction = (index: number) => {
    setDetail((prev) => ({
      ...prev,
      surrounding: {
        ...prev.surrounding,
        attractions: prev.surrounding.attractions.filter((_, i) => i !== index),
      },
    }));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-teal-600" />
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto">
      {/* ヘッダー */}
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link
            href="/facility/hotels"
            className="p-2 text-gray-500 hover:text-gray-700 rounded-md hover:bg-gray-100"
          >
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">宿の情報</h1>
            <p className="text-sm text-gray-500 mt-0.5">
              LP生成に使用する宿のストーリーや周辺情報を入力してください
            </p>
          </div>
        </div>
        <button
          onClick={handleAutoFill}
          disabled={autoFilling || saving}
          className="inline-flex items-center gap-1.5 px-3 py-2.5 text-sm font-medium text-purple-700 bg-purple-50 hover:bg-purple-100 border border-purple-200 rounded-md disabled:opacity-60"
        >
          {autoFilling ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Wand2 className="h-4 w-4" />
          )}
          公式サイトから自動入力
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-md text-sm">
          {error}
        </div>
      )}

      <div className="space-y-6">
        {/* 宿のストーリー */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-base font-semibold text-gray-900 mb-1">
            宿のストーリー・こだわり
          </h2>
          <p className="text-xs text-gray-500 mb-3">
            創業の歴史や宿のこだわりを自由に記述してください。LP の導入文として使用されます。
          </p>
          <textarea
            value={detail.story}
            onChange={(e) =>
              setDetail((prev) => ({ ...prev, story: e.target.value }))
            }
            rows={5}
            placeholder="例）創業昭和30年。山の麓に佇む老舗旅館として、代々地元の食材と天然温泉にこだわり続けてきました..."
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-teal-500 resize-none"
          />
        </div>

        {/* ハイライト */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-base font-semibold text-gray-900 mb-1">
            宿のハイライト
          </h2>
          <p className="text-xs text-gray-500 mb-3">
            宿の強みや特徴を短いフレーズで入力してください（例：源泉かけ流し、地産地消料理）
          </p>
          {/* 既存タグ */}
          <div className="flex flex-wrap gap-2 mb-3">
            {detail.highlights.map((h, i) => (
              <span
                key={i}
                className="inline-flex items-center gap-1 px-3 py-1 bg-teal-50 text-teal-800 text-sm rounded-full border border-teal-200"
              >
                {h}
                <button
                  onClick={() => removeHighlight(i)}
                  className="ml-1 text-teal-500 hover:text-teal-700"
                >
                  <Trash2 className="h-3 w-3" />
                </button>
              </span>
            ))}
          </div>
          {/* 入力欄 */}
          <div className="flex gap-2">
            <input
              type="text"
              value={highlightInput}
              onChange={(e) => setHighlightInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  addHighlight();
                }
              }}
              placeholder="ハイライトを入力して Enter または追加ボタン"
              className="flex-1 border border-gray-300 rounded-md px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-teal-500"
            />
            <button
              onClick={addHighlight}
              className="inline-flex items-center gap-1 px-3 py-2 text-sm font-medium text-white bg-teal-600 hover:bg-teal-700 rounded-md"
            >
              <Plus className="h-4 w-4" />
              追加
            </button>
          </div>
        </div>

        {/* 周辺情報 */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-1">
            <h2 className="text-base font-semibold text-gray-900">
              周辺観光情報
            </h2>
            <button
              onClick={handleFillFromMarket}
              disabled={fillingFromMarket || saving}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-purple-700 bg-purple-50 hover:bg-purple-100 border border-purple-200 rounded-md disabled:opacity-60"
            >
              {fillingFromMarket ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <TrendingUp className="h-3 w-3" />
              )}
              市場データから補完
            </button>
          </div>
          <p className="text-xs text-gray-500 mb-4">
            周辺エリアの説明と近隣の観光スポットを入力してください。マーケティングAIで市場分析済みの場合は「市場データから補完」が利用できます。
          </p>

          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              エリア説明
            </label>
            <textarea
              value={detail.surrounding.description}
              onChange={(e) =>
                setDetail((prev) => ({
                  ...prev,
                  surrounding: {
                    ...prev.surrounding,
                    description: e.target.value,
                  },
                }))
              }
              rows={3}
              placeholder="例）南アルプスの麓に位置し、豊かな自然に囲まれた静かなエリアです..."
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-teal-500 resize-none"
            />
          </div>

          <label className="block text-sm font-medium text-gray-700 mb-2">
            観光スポット
          </label>
          <div className="space-y-2">
            {detail.surrounding.attractions.map((attraction, i) => (
              <div key={i} className="flex gap-2 items-center">
                <input
                  type="text"
                  value={attraction.name}
                  onChange={(e) => updateAttraction(i, "name", e.target.value)}
                  placeholder="スポット名（例：○○温泉郷）"
                  className="flex-1 border border-gray-300 rounded-md px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-teal-500"
                />
                <input
                  type="text"
                  value={attraction.distance}
                  onChange={(e) =>
                    updateAttraction(i, "distance", e.target.value)
                  }
                  placeholder="距離（例：徒歩5分）"
                  className="w-36 border border-gray-300 rounded-md px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-teal-500"
                />
                <button
                  onClick={() => removeAttraction(i)}
                  className="p-2 text-gray-400 hover:text-red-500 rounded-md"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>
          <button
            onClick={addAttraction}
            className="mt-3 inline-flex items-center gap-1 px-3 py-2 text-sm font-medium text-teal-700 bg-teal-50 hover:bg-teal-100 border border-teal-200 rounded-md"
          >
            <Plus className="h-4 w-4" />
            スポットを追加
          </button>
        </div>

        {/* アクセス */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-base font-semibold text-gray-900 mb-1">
            アクセス
          </h2>
          <p className="text-xs text-gray-500 mb-3">
            最寄り駅からの経路や送迎情報などを記述してください
          </p>
          <textarea
            value={detail.access}
            onChange={(e) =>
              setDetail((prev) => ({ ...prev, access: e.target.value }))
            }
            rows={3}
            placeholder="例）新宿駅から特急あずさで2時間。無料送迎あり（要予約）。お車の場合は中央自動車道○○ICから約15分..."
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-teal-500 resize-none"
          />
        </div>

        {/* 下部保存ボタン */}
        <div className="flex justify-end pb-8">
          <button
            onClick={handleSave}
            disabled={saving}
            className="inline-flex items-center gap-2 px-6 py-2.5 text-sm font-medium text-white bg-teal-600 hover:bg-teal-700 rounded-md disabled:opacity-60"
          >
            {saving ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : saved ? (
              <CheckCircle className="h-4 w-4" />
            ) : (
              <Save className="h-4 w-4" />
            )}
            {saved ? "保存しました" : "保存する"}
          </button>
        </div>
      </div>
    </div>
  );
}
