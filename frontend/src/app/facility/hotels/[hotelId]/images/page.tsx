"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  facilityApi,
  HotelResponse,
  FacilityImageItem,
  ApiError,
} from "@/lib/api";
import {
  ArrowLeft,
  Image as ImageIcon,
  Upload,
  Trash2,
  Loader2,
} from "lucide-react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const FACILITY_IMAGE_TYPE_LABELS: Record<string, string> = {
  panorama: "全景",
  room: "部屋",
  bath: "風呂",
  cuisine: "料理",
  lobby: "ロビー",
  restaurant: "レストラン",
  sightseeing: "周辺観光地",
  staff: "スタッフ",
  other: "その他",
};

const FACILITY_IMAGE_TYPES = [
  "panorama",
  "room",
  "bath",
  "cuisine",
  "lobby",
  "restaurant",
  "sightseeing",
  "staff",
  "other",
];

const MAX_IMAGES = 10;

export default function FacilityHotelImagesPage() {
  const params = useParams();
  const router = useRouter();
  const hotelId = Number(params.hotelId);

  const [hotel, setHotel] = useState<HotelResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [uploadType, setUploadType] = useState<string>("other");
  const [uploadDescription, setUploadDescription] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<{
    current: number;
    total: number;
    message: string;
  } | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const [deletingKey, setDeletingKey] = useState<string | null>(null);

  const loadHotel = useCallback(async () => {
    if (!hotelId || isNaN(hotelId)) return;
    setLoading(true);
    setError(null);
    try {
      const data = await facilityApi.getHotel(hotelId);
      setHotel(data);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail);
      } else {
        setError("施設情報の取得に失敗しました");
      }
    } finally {
      setLoading(false);
    }
  }, [hotelId]);

  useEffect(() => {
    loadHotel();
  }, [loadHotel]);

  const images = hotel?.facility_images ?? [];
  const sortedImages = [...images].sort(
    (a, b) => (a.order ?? 0) - (b.order ?? 0)
  );
  const canAddMore = images.length < MAX_IMAGES;

  const handleFiles = async (files: FileList | null) => {
    if (!files || files.length === 0 || !hotel || !canAddMore) return;
    const fileArray = Array.from(files).filter((f) =>
      /\.(jpe?g|png|webp)$/i.test(f.name)
    );
    if (fileArray.length === 0) {
      setUploadError("画像ファイル（jpg, png, webp）を選んでください");
      return;
    }
    const remaining = MAX_IMAGES - images.length;
    const toUpload = fileArray.slice(0, remaining);
    setUploading(true);
    setUploadError(null);
    setUploadProgress({ current: 0, total: toUpload.length, message: "準備中..." });

    let successCount = 0;
    for (let i = 0; i < toUpload.length; i++) {
      setUploadProgress({
        current: i + 1,
        total: toUpload.length,
        message: `${i + 1}枚目を登録中…`,
      });
      try {
        await facilityApi.uploadHotelImage(
          hotelId,
          toUpload[i],
          uploadType,
          uploadDescription || undefined
        );
        successCount++;
      } catch (err) {
        const msg =
          err instanceof ApiError ? err.detail : "登録に失敗しました";
        setUploadError(`${i + 1}枚目: ${msg}`);
        setUploadProgress(null);
        setUploading(false);
        await loadHotel();
        return;
      }
    }

    setUploadProgress({
      current: toUpload.length,
      total: toUpload.length,
      message: `${successCount}枚登録しました`,
    });
    setUploading(false);
    setTimeout(() => setUploadProgress(null), 2000);
    await loadHotel();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (!uploading && canAddMore) handleFiles(e.dataTransfer.files);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDelete = async (item: FacilityImageItem) => {
    if (!hotel) return;
    setDeletingKey(item.key);
    try {
      await facilityApi.deleteHotelImage(hotelId, item.key);
      await loadHotel();
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail);
      }
    } finally {
      setDeletingKey(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-10 w-10 animate-spin text-teal-600" />
      </div>
    );
  }

  if (error || !hotel) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <Link
          href="/facility/hotels"
          className="inline-flex items-center text-sm text-teal-600 hover:text-teal-700 mb-4"
        >
          <ArrowLeft className="h-4 w-4 mr-1" />
          施設一覧に戻る
        </Link>
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
          {error ?? "施設が見つかりません"}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <Link
        href="/facility/hotels"
        className="inline-flex items-center text-sm text-teal-600 hover:text-teal-700 mb-6"
      >
        <ArrowLeft className="h-4 w-4 mr-1" />
        施設一覧に戻る
      </Link>

      <h1 className="text-2xl font-bold text-gray-900 mb-1">
        {hotel.name} の写真
      </h1>
      <p className="text-sm text-gray-500 mb-6">
        施設の写真を追加・削除できます。最大{MAX_IMAGES}枚まで登録できます。
      </p>

      {/* 既存画像一覧 */}
      {sortedImages.length > 0 && (
        <section className="mb-8">
          <h2 className="text-lg font-medium text-gray-900 mb-3">
            登録済みの写真（{sortedImages.length}枚）
          </h2>
          <ul className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
            {sortedImages.map((item) => (
              <li
                key={item.key}
                className="bg-white border border-gray-200 rounded-lg overflow-hidden shadow-sm"
              >
                <div className="aspect-video bg-gray-100 relative">
                  <img
                    src={`${API_BASE_URL}${item.url}`}
                    alt={item.description || item.type}
                    className="w-full h-full object-cover"
                  />
                  {(hotel.role === "owner" || hotel.role === "editor") && (
                    <button
                      type="button"
                      onClick={() => handleDelete(item)}
                      disabled={deletingKey === item.key}
                      className="absolute top-2 right-2 p-1.5 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50"
                      title="削除"
                    >
                      {deletingKey === item.key ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Trash2 className="h-4 w-4" />
                      )}
                    </button>
                  )}
                </div>
                <div className="p-2 text-xs">
                  <span className="font-medium text-gray-700">
                    {FACILITY_IMAGE_TYPE_LABELS[item.type] ?? item.type}
                  </span>
                  {item.description && (
                    <p className="text-gray-500 mt-0.5 truncate">
                      {item.description}
                    </p>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* アップロード（owner/editor かつ 10枚未満のとき） */}
      {(hotel.role === "owner" || hotel.role === "editor") && (
        <section className="mb-8">
          <h2 className="text-lg font-medium text-gray-900 mb-3">
            写真を追加
          </h2>
          {canAddMore ? (
            <>
              <div className="flex flex-wrap gap-4 mb-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    種別
                  </label>
                  <select
                    value={uploadType}
                    onChange={(e) => setUploadType(e.target.value)}
                    disabled={uploading}
                    className="block w-full min-w-[160px] px-3 py-2 border border-gray-300 rounded-lg text-gray-900 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 disabled:opacity-50"
                  >
                    {FACILITY_IMAGE_TYPES.map((t) => (
                      <option key={t} value={t}>
                        {FACILITY_IMAGE_TYPE_LABELS[t]}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="flex-1 min-w-[200px]">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    説明（任意）
                  </label>
                  <input
                    type="text"
                    value={uploadDescription}
                    onChange={(e) => setUploadDescription(e.target.value)}
                    disabled={uploading}
                    placeholder="例：客室から見た庭園"
                    className="block w-full px-3 py-2 border border-gray-300 rounded-lg text-gray-900 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 disabled:opacity-50"
                  />
                </div>
              </div>

              <div
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center bg-gray-50 hover:border-teal-400 transition-colors"
              >
                <input
                  type="file"
                  id="facility-image-upload"
                  accept=".jpg,.jpeg,.png,.webp"
                  multiple
                  disabled={uploading}
                  onChange={(e) => handleFiles(e.target.files)}
                  className="hidden"
                />
                <label
                  htmlFor="facility-image-upload"
                  className="cursor-pointer flex flex-col items-center"
                >
                  <Upload className="h-12 w-12 text-gray-400 mb-2" />
                  <p className="text-sm font-medium text-gray-700 mb-1">
                    ここに写真をドラッグするか、下のボタンで選んでください
                  </p>
                  <p className="text-xs text-gray-500 mb-4">
                    jpg, png, webp（複数選択可・最大{MAX_IMAGES - images.length}枚まで）
                  </p>
                  <span className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-teal-600 hover:bg-teal-700 disabled:opacity-50">
                    ファイルを選ぶ
                  </span>
                </label>
              </div>

              {uploadProgress && (
                <div className="mt-4 flex items-center gap-2 text-sm text-gray-700">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>
                    {uploadProgress.current} / {uploadProgress.total} 枚目 —{" "}
                    {uploadProgress.message}
                  </span>
                </div>
              )}
              {uploadError && (
                <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
                  {uploadError}
                </div>
              )}
            </>
          ) : (
            <p className="text-sm text-gray-500">
              登録できる写真は最大{MAX_IMAGES}枚です。追加するには既存の写真を削除してください。
            </p>
          )}
        </section>
      )}
    </div>
  );
}
