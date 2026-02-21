"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  facilityApi,
  HotelResponse,
  FacilityImageItem,
  ApiError,
} from "@/lib/api";
import {
  ArrowLeft,
  Upload,
  Trash2,
  Loader2,
  X,
} from "lucide-react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// 種別ラベル（panorama は後方互換で施設外観として表示）
const FACILITY_IMAGE_TYPE_LABELS: Record<string, string> = {
  exterior: "施設外観",
  interior: "施設内観",
  panorama: "施設外観",
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
  "exterior",
  "interior",
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

type PendingItem = {
  id: string;
  file: File;
  type: string;
  description: string;
  previewUrl: string;
};

function generateId() {
  return `pending-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

type ImageLightboxModalProps = {
  item: FacilityImageItem;
  apiBaseUrl: string;
  typeLabels: Record<string, string>;
  types: string[];
  canEdit: boolean;
  onClose: () => void;
  onSave: (type: string, description: string) => void;
  saving: boolean;
};

function ImageLightboxModal({
  item,
  apiBaseUrl,
  typeLabels,
  types,
  canEdit,
  onClose,
  onSave,
  saving,
}: ImageLightboxModalProps) {
  const normalizedType =
    item.type === "panorama" ? "exterior" : item.type;
  const [editType, setEditType] = useState(normalizedType);
  const [editDescription, setEditDescription] = useState(
    item.description ?? ""
  );

  useEffect(() => {
    setEditType(item.type === "panorama" ? "exterior" : item.type);
    setEditDescription(item.description ?? "");
  }, [item.type, item.description]);

  const hasChange =
    editType !== item.type || editDescription !== (item.description ?? "");

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70"
      onClick={onClose}
    >
      <div
        className="relative bg-gray-900 rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-auto flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          type="button"
          onClick={onClose}
          className="absolute top-2 right-2 z-10 p-2 text-white/80 hover:text-white rounded-full bg-black/40 hover:bg-black/60"
          title="閉じる"
        >
          <X className="h-5 w-5" />
        </button>

        <div className="flex-1 flex items-center justify-center p-6 min-h-0">
          <img
            src={`${apiBaseUrl}${item.url}`}
            alt={item.description || item.type}
            className="max-w-full max-h-[70vh] w-auto h-auto object-contain"
          />
        </div>

        <div className="p-4 bg-white border-t border-gray-200 rounded-b-lg space-y-4">
          {canEdit ? (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  種別
                </label>
                <select
                  value={editType}
                  onChange={(e) => setEditType(e.target.value)}
                  disabled={saving}
                  className="block w-full max-w-xs px-3 py-2 text-sm border border-gray-300 rounded-lg text-gray-900 focus:ring-2 focus:ring-teal-500 disabled:opacity-50"
                >
                  {types.map((t) => (
                    <option key={t} value={t}>
                      {typeLabels[t] ?? t}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  説明
                </label>
                <input
                  type="text"
                  value={editDescription}
                  onChange={(e) => setEditDescription(e.target.value)}
                  disabled={saving}
                  placeholder="説明（任意）"
                  className="block w-full px-3 py-2 text-sm border border-gray-300 rounded-lg text-gray-900 focus:ring-2 focus:ring-teal-500 disabled:opacity-50"
                />
              </div>
              <div className="flex gap-3">
                {hasChange && (
                  <button
                    type="button"
                    onClick={async () => {
                      await onSave(editType, editDescription);
                    }}
                    disabled={saving}
                    className="inline-flex items-center px-4 py-2 text-sm font-medium rounded-lg text-white bg-teal-600 hover:bg-teal-700 disabled:opacity-50"
                  >
                    {saving ? (
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    ) : null}
                    保存
                  </button>
                )}
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
                >
                  閉じる
                </button>
              </div>
            </>
          ) : (
            <>
              <p className="text-sm font-medium text-gray-700">
                {typeLabels[item.type] ?? item.type}
              </p>
              {item.description && (
                <p className="text-sm text-gray-500">{item.description}</p>
              )}
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
              >
                閉じる
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default function FacilityHotelImagesPage() {
  const params = useParams();
  const hotelId = Number(params.hotelId);

  const [hotel, setHotel] = useState<HotelResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [pendingItems, setPendingItems] = useState<PendingItem[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<{
    current: number;
    total: number;
    message: string;
  } | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const [deletingKey, setDeletingKey] = useState<string | null>(null);
  const [savingKey, setSavingKey] = useState<string | null>(null);
  const [deleteConfirmItem, setDeleteConfirmItem] =
    useState<FacilityImageItem | null>(null);
  const [lightboxItem, setLightboxItem] =
    useState<FacilityImageItem | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pendingItemsRef = useRef<PendingItem[]>([]);
  pendingItemsRef.current = pendingItems;

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

  // アンマウント時に保留中の object URL を revoke
  useEffect(() => {
    return () => {
      pendingItemsRef.current.forEach((item) =>
        URL.revokeObjectURL(item.previewUrl)
      );
    };
  }, []);

  const images = hotel?.facility_images ?? [];
  const sortedImages = [...images].sort(
    (a, b) => (a.order ?? 0) - (b.order ?? 0)
  );
  const canAddMore = images.length < MAX_IMAGES;
  const remainingSlots = MAX_IMAGES - images.length - pendingItems.length;

  const addFilesToPending = (files: FileList | null) => {
    if (!files || files.length === 0) return;
    const fileArray = Array.from(files).filter((f) =>
      /\.(jpe?g|png|webp)$/i.test(f.name)
    );
    const newItems: PendingItem[] = fileArray
      .slice(0, Math.max(0, remainingSlots))
      .map((file) => ({
        id: generateId(),
        file,
        type: FACILITY_IMAGE_TYPES[0],
        description: "",
        previewUrl: URL.createObjectURL(file),
      }));
    setPendingItems((prev) => [...prev, ...newItems]);
    setUploadError(null);
  };

  const removePending = (id: string) => {
    setPendingItems((prev) => {
      const item = prev.find((p) => p.id === id);
      if (item) URL.revokeObjectURL(item.previewUrl);
      return prev.filter((p) => p.id !== id);
    });
  };

  const updatePendingItem = (
    id: string,
    updates: { type?: string; description?: string }
  ) => {
    setPendingItems((prev) =>
      prev.map((p) =>
        p.id === id ? { ...p, ...updates } : p
      )
    );
  };

  const handleUploadAll = async () => {
    if (pendingItems.length === 0 || !hotel) return;
    setUploading(true);
    setUploadError(null);
    setUploadProgress({
      current: 0,
      total: pendingItems.length,
      message: "準備中...",
    });

    let successCount = 0;
    for (let i = 0; i < pendingItems.length; i++) {
      const item = pendingItems[i];
      setUploadProgress({
        current: i + 1,
        total: pendingItems.length,
        message: `${i + 1}枚目を登録中…`,
      });
      try {
        await facilityApi.uploadHotelImage(
          hotelId,
          item.file,
          item.type,
          item.description || undefined
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

    pendingItems.forEach((p) => URL.revokeObjectURL(p.previewUrl));
    setPendingItems([]);
    setUploadProgress({
      current: pendingItems.length,
      total: pendingItems.length,
      message: `${successCount}枚登録しました`,
    });
    setUploading(false);
    setTimeout(() => setUploadProgress(null), 2000);
    await loadHotel();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (!uploading && canAddMore) addFilesToPending(e.dataTransfer.files);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDelete = async (item: FacilityImageItem) => {
    if (!hotel) return;
    setDeleteConfirmItem(null);
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

  const handleSaveImageMeta = async (
    item: FacilityImageItem,
    type: string,
    description: string
  ) => {
    setSavingKey(item.key);
    try {
      await facilityApi.updateHotelImage(hotelId, item.key, {
        type,
        description,
      });
      await loadHotel();
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail);
      }
    } finally {
      setSavingKey(null);
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

      {/* 登録済み画像一覧（インライン編集あり） */}
      {sortedImages.length > 0 && (
        <section className="mb-8">
          <h2 className="text-lg font-medium text-gray-900 mb-3">
            登録済みの写真（{sortedImages.length}枚）
          </h2>
          <ul className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
            {sortedImages.map((item) => (
              <RegisteredImageCard
                key={item.key}
                item={item}
                apiBaseUrl={API_BASE_URL}
                typeLabels={FACILITY_IMAGE_TYPE_LABELS}
                types={FACILITY_IMAGE_TYPES}
                canEdit={hotel.role === "owner" || hotel.role === "editor"}
                onRequestDelete={() => setDeleteConfirmItem(item)}
                onImageClick={() => setLightboxItem(item)}
                onSave={(type, description) =>
                  handleSaveImageMeta(item, type, description)
                }
                deleting={deletingKey === item.key}
                saving={savingKey === item.key}
              />
            ))}
          </ul>

          {/* 削除確認モーダル */}
          {deleteConfirmItem && (
            <div
              className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50"
              onClick={() => setDeleteConfirmItem(null)}
            >
              <div
                className="bg-white rounded-lg shadow-xl max-w-sm w-full p-6"
                onClick={(e) => e.stopPropagation()}
              >
                <p className="text-gray-900 font-medium mb-4">
                  この写真を削除してもよろしいですか？
                </p>
                <div className="flex gap-3 justify-end">
                  <button
                    type="button"
                    onClick={() => setDeleteConfirmItem(null)}
                    className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
                  >
                    キャンセル
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDelete(deleteConfirmItem)}
                    disabled={deletingKey === deleteConfirmItem.key}
                    className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:opacity-50 inline-flex items-center gap-2"
                  >
                    {deletingKey === deleteConfirmItem.key ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : null}
                    削除する
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* 画像拡大＋編集モーダル */}
          {lightboxItem && (
            <ImageLightboxModal
              item={lightboxItem}
              apiBaseUrl={API_BASE_URL}
              typeLabels={FACILITY_IMAGE_TYPE_LABELS}
              types={FACILITY_IMAGE_TYPES}
              canEdit={hotel.role === "owner" || hotel.role === "editor"}
              onClose={() => setLightboxItem(null)}
              onSave={async (type, description) => {
                await handleSaveImageMeta(lightboxItem, type, description);
                setLightboxItem(null);
              }}
              saving={savingKey === lightboxItem.key}
            />
          )}
        </section>
      )}

      {/* 保留中の写真 + 登録するボタン（owner/editor かつ 10枚未満のとき） */}
      {(hotel.role === "owner" || hotel.role === "editor") && (
        <section className="mb-8">
          <h2 className="text-lg font-medium text-gray-900 mb-3">
            写真を追加
          </h2>
          {canAddMore ? (
            <>
              <div
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center bg-gray-50 hover:border-teal-400 transition-colors mb-4"
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".jpg,.jpeg,.png,.webp"
                  multiple
                  disabled={uploading}
                  onChange={(e) => {
                    addFilesToPending(e.target.files);
                    e.target.value = "";
                  }}
                  className="hidden"
                />
                <Upload className="h-10 w-10 text-gray-400 mx-auto mb-2" />
                <p className="text-sm font-medium text-gray-700 mb-1">
                  ここに写真をドラッグするか、下のボタンで選んでください
                </p>
                <p className="text-xs text-gray-500 mb-4">
                  jpg, png, webp（複数選択可・あと{remainingSlots}枚まで）
                </p>
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploading}
                  className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-teal-600 hover:bg-teal-700 disabled:opacity-50"
                >
                  ファイルを選ぶ
                </button>
              </div>

              {/* 保留中の写真一覧（1枚ごとに種別・説明） */}
              {pendingItems.length > 0 && (
                <div className="mb-4">
                  <h3 className="text-sm font-medium text-gray-700 mb-2">
                    保留中の写真（{pendingItems.length}枚）
                  </h3>
                  <ul className="space-y-3">
                    {pendingItems.map((item) => (
                      <li
                        key={item.id}
                        className="flex items-start gap-4 p-3 bg-gray-50 rounded-lg border border-gray-200"
                      >
                        <div className="relative flex-shrink-0 w-24 h-24 rounded overflow-hidden bg-gray-200">
                          <img
                            src={item.previewUrl}
                            alt=""
                            className="w-full h-full object-cover"
                          />
                          <button
                            type="button"
                            onClick={() => removePending(item.id)}
                            disabled={uploading}
                            className="absolute left-1 top-1 p-1 rounded bg-black/50 text-white hover:bg-red-600 disabled:opacity-50"
                            title="削除"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                        <div className="flex-1 min-w-0 space-y-2">
                          <div>
                            <select
                              value={item.type}
                              onChange={(e) =>
                                updatePendingItem(item.id, {
                                  type: e.target.value,
                                })
                              }
                              disabled={uploading}
                              className="block w-full max-w-[140px] px-2 py-1.5 text-sm border border-gray-300 rounded-lg text-gray-900 focus:ring-2 focus:ring-teal-500 disabled:opacity-50"
                            >
                              {FACILITY_IMAGE_TYPES.map((t) => (
                                <option key={t} value={t}>
                                  {FACILITY_IMAGE_TYPE_LABELS[t]}
                                </option>
                              ))}
                            </select>
                          </div>
                          <input
                            type="text"
                            value={item.description}
                            onChange={(e) =>
                              updatePendingItem(item.id, {
                                description: e.target.value,
                              })
                            }
                            disabled={uploading}
                            placeholder="説明（任意）"
                            className="block w-full px-2 py-1.5 text-sm border border-gray-300 rounded-lg text-gray-900 focus:ring-2 focus:ring-teal-500 disabled:opacity-50"
                          />
                        </div>
                      </li>
                    ))}
                  </ul>
                  <button
                    type="button"
                    onClick={handleUploadAll}
                    disabled={uploading}
                    className="mt-3 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-teal-600 hover:bg-teal-700 disabled:opacity-50"
                  >
                    {uploading ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin mr-2" />
                        登録中...
                      </>
                    ) : (
                      "登録する"
                    )}
                  </button>
                </div>
              )}

              {uploadProgress && (
                <div className="flex items-center gap-2 text-sm text-gray-700 mb-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>
                    {uploadProgress.current} / {uploadProgress.total} 枚目 —{" "}
                    {uploadProgress.message}
                  </span>
                </div>
              )}
              {uploadError && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
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

type RegisteredImageCardProps = {
  item: FacilityImageItem;
  apiBaseUrl: string;
  typeLabels: Record<string, string>;
  types: string[];
  canEdit: boolean;
  onRequestDelete: () => void;
  onImageClick: () => void;
  onSave: (type: string, description: string) => void;
  deleting: boolean;
  saving: boolean;
};

function RegisteredImageCard({
  item,
  apiBaseUrl,
  typeLabels,
  types,
  canEdit,
  onRequestDelete,
  onImageClick,
  onSave,
  deleting,
  saving,
}: RegisteredImageCardProps) {
  // 後方互換: panorama は API で廃止のため編集時は exterior として扱う
  const normalizedType =
    item.type === "panorama" ? "exterior" : item.type;
  const [editType, setEditType] = useState(normalizedType);
  const [editDescription, setEditDescription] = useState(item.description ?? "");

  useEffect(() => {
    setEditType(item.type === "panorama" ? "exterior" : item.type);
    setEditDescription(item.description ?? "");
  }, [item.type, item.description]);

  const hasChange =
    editType !== item.type || editDescription !== (item.description ?? "");

  return (
    <li className="bg-white border border-gray-200 rounded-lg overflow-hidden shadow-sm">
      <div
        role="button"
        tabIndex={0}
        onClick={onImageClick}
        onKeyDown={(e) => e.key === "Enter" && onImageClick()}
        className="h-[200px] bg-gray-100 relative cursor-pointer focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-inset"
      >
        <img
          src={`${apiBaseUrl}${item.url}`}
          alt={item.description || item.type}
          className="w-full h-full object-cover"
        />
        {canEdit && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onRequestDelete();
            }}
            disabled={deleting}
            className="absolute top-1 right-1 p-1 bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50"
            title="削除"
          >
            {deleting ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : (
              <Trash2 className="h-3 w-3" />
            )}
          </button>
        )}
      </div>
      <div className="p-2 space-y-1.5">
        {canEdit ? (
          <>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-0.5">
                種別
              </label>
              <select
                value={editType}
                onChange={(e) => setEditType(e.target.value)}
                disabled={saving}
                className="block w-full px-1.5 py-1 text-xs border border-gray-300 rounded-md text-gray-900 focus:ring-2 focus:ring-teal-500 disabled:opacity-50"
              >
                {types.map((t) => (
                  <option key={t} value={t}>
                    {typeLabels[t] ?? t}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-0.5">
                説明
              </label>
              <input
                type="text"
                value={editDescription}
                onChange={(e) => setEditDescription(e.target.value)}
                disabled={saving}
                placeholder="説明（任意）"
                className="block w-full px-1.5 py-1 text-xs border border-gray-300 rounded-md text-gray-900 focus:ring-2 focus:ring-teal-500 disabled:opacity-50"
              />
            </div>
            {hasChange && (
              <button
                type="button"
                onClick={() => onSave(editType, editDescription)}
                disabled={saving}
                className="inline-flex items-center px-2 py-1 text-xs font-medium rounded-md text-white bg-teal-600 hover:bg-teal-700 disabled:opacity-50"
              >
                {saving ? (
              <Loader2 className="h-3 w-3 animate-spin mr-1" />
            ) : null}
                保存
              </button>
            )}
          </>
        ) : (
          <>
            <span className="font-medium text-gray-700 text-xs">
              {typeLabels[item.type] ?? item.type}
            </span>
            {item.description && (
              <p className="text-gray-500 text-xs line-clamp-2">{item.description}</p>
            )}
          </>
        )}
      </div>
    </li>
  );
}
