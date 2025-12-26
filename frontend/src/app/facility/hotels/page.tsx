"use client";

import { useEffect, useState } from "react";
import { facilityApi, HotelResponse, ApiError, HotelCreateRequest } from "@/lib/api";
import {
  Building2,
  Plus,
  Pencil,
  Trash2,
  MapPin,
  AlertCircle,
  X,
  Check,
  Phone,
  Globe,
  BrainCircuit,
} from "lucide-react";
import Link from "next/link";

export default function FacilityHotelsPage() {
  const [hotels, setHotels] = useState<HotelResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingHotel, setEditingHotel] = useState<HotelResponse | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<number | null>(null);

  useEffect(() => {
    loadHotels();
  }, []);

  const loadHotels = async () => {
    try {
      const data = await facilityApi.listHotels();
      setHotels(data);
    } catch (error) {
      console.error("Failed to load hotels:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (hotelId: number) => {
    try {
      await facilityApi.deleteHotel(hotelId);
      setHotels(hotels.filter((h) => h.id !== hotelId));
      setDeleteConfirm(null);
    } catch (error) {
      console.error("Failed to delete hotel:", error);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-teal-600"></div>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-8 flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">施設管理</h1>
          <p className="mt-1 text-sm text-gray-500">
            施設の登録・編集・削除ができます
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-teal-600 hover:bg-teal-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-teal-500"
        >
          <Plus className="h-4 w-4 mr-2" />
          新規登録
        </button>
      </div>

      {/* 施設リスト */}
      <div className="bg-white shadow rounded-lg overflow-hidden">
        {hotels.length === 0 ? (
          <div className="p-12 text-center">
            <Building2 className="mx-auto h-12 w-12 text-gray-400 mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              施設がまだ登録されていません
            </h3>
            <p className="text-sm text-gray-500 mb-4">
              新しい施設を登録して管理を始めましょう
            </p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-teal-600 hover:bg-teal-700"
            >
              <Plus className="h-4 w-4 mr-2" />
              最初の施設を登録
            </button>
          </div>
        ) : (
          <ul className="divide-y divide-gray-200">
            {hotels.map((hotel) => (
              <li key={hotel.id} className="p-6">
                <div className="flex items-start justify-between">
                  <div className="flex items-start">
                    <div className="flex-shrink-0 bg-teal-100 rounded-lg p-3">
                      <Building2 className="h-8 w-8 text-teal-600" />
                    </div>
                    <div className="ml-4">
                      <h3 className="text-lg font-medium text-gray-900">
                        {hotel.name}
                      </h3>
                      <div className="mt-1 space-y-1">
                        <div className="flex items-center text-sm text-gray-500">
                          <MapPin className="h-4 w-4 mr-1" />
                          {hotel.address}
                          {hotel.postal_code && ` (〒${hotel.postal_code})`}
                        </div>
                        {hotel.phone && (
                          <div className="flex items-center text-sm text-gray-500">
                            <Phone className="h-4 w-4 mr-1" />
                            {hotel.phone}
                          </div>
                        )}
                        {hotel.website && (
                          <div className="flex items-center text-sm text-gray-500">
                            <Globe className="h-4 w-4 mr-1" />
                            <a
                              href={hotel.website}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-teal-600 hover:text-teal-500"
                            >
                              {hotel.website}
                            </a>
                          </div>
                        )}
                      </div>
                      <div className="mt-2">
                        <span
                          className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                            hotel.role === "owner"
                              ? "bg-teal-100 text-teal-800"
                              : hotel.role === "editor"
                                ? "bg-blue-100 text-blue-800"
                                : "bg-gray-100 text-gray-800"
                          }`}
                        >
                          {hotel.role === "owner"
                            ? "オーナー"
                            : hotel.role === "editor"
                              ? "編集者"
                              : "閲覧者"}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    {/* マーケティングAIへのリンク */}
                    <Link
                      href={`/marketing/${hotel.id}/dashboard`}
                      className="inline-flex items-center px-3 py-2 text-sm font-medium text-white bg-gradient-to-r from-purple-500 to-cyan-500 rounded-md hover:from-purple-600 hover:to-cyan-600 transition-all"
                      title="マーケティングAI"
                    >
                      <BrainCircuit className="h-4 w-4 mr-1" />
                      マーケティングAI
                    </Link>
                    {(hotel.role === "owner" || hotel.role === "editor") && (
                      <button
                        onClick={() => setEditingHotel(hotel)}
                        className="p-2 text-gray-400 hover:text-teal-600 rounded-md hover:bg-gray-100"
                        title="編集"
                      >
                        <Pencil className="h-5 w-5" />
                      </button>
                    )}
                    {hotel.role === "owner" && (
                      <>
                        {deleteConfirm === hotel.id ? (
                          <span className="inline-flex items-center">
                            <button
                              onClick={() => handleDelete(hotel.id)}
                              className="p-2 text-red-600 hover:text-red-700 rounded-md hover:bg-red-50"
                              title="削除を確定"
                            >
                              <Check className="h-5 w-5" />
                            </button>
                            <button
                              onClick={() => setDeleteConfirm(null)}
                              className="p-2 text-gray-400 hover:text-gray-600 rounded-md hover:bg-gray-100"
                              title="キャンセル"
                            >
                              <X className="h-5 w-5" />
                            </button>
                          </span>
                        ) : (
                          <button
                            onClick={() => setDeleteConfirm(hotel.id)}
                            className="p-2 text-gray-400 hover:text-red-600 rounded-md hover:bg-gray-100"
                            title="削除"
                          >
                            <Trash2 className="h-5 w-5" />
                          </button>
                        )}
                      </>
                    )}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* 作成モーダル */}
      {showCreateModal && (
        <HotelModal
          onClose={() => setShowCreateModal(false)}
          onSaved={(hotel) => {
            setHotels([...hotels, hotel]);
            setShowCreateModal(false);
          }}
        />
      )}

      {/* 編集モーダル */}
      {editingHotel && (
        <HotelModal
          hotel={editingHotel}
          onClose={() => setEditingHotel(null)}
          onSaved={(updated) => {
            setHotels(hotels.map((h) => (h.id === updated.id ? updated : h)));
            setEditingHotel(null);
          }}
        />
      )}
    </div>
  );
}

// 施設作成・編集モーダル
function HotelModal({
  hotel,
  onClose,
  onSaved,
}: {
  hotel?: HotelResponse;
  onClose: () => void;
  onSaved: (hotel: HotelResponse) => void;
}) {
  const isEdit = !!hotel;
  const [formData, setFormData] = useState<HotelCreateRequest>({
    name: hotel?.name || "",
    address: hotel?.address || "",
    postal_code: hotel?.postal_code || "",
    phone: hotel?.phone || "",
    email: hotel?.email || "",
    website: hotel?.website || "",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleChange = (field: keyof HotelCreateRequest, value: string) => {
    setFormData({ ...formData, [field]: value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      let saved: HotelResponse;
      if (isEdit) {
        saved = await facilityApi.updateHotel(hotel.id, formData);
      } else {
        saved = await facilityApi.createHotel(formData);
      }
      onSaved(saved);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail);
      } else {
        setError(isEdit ? "更新に失敗しました" : "登録に失敗しました");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen px-4">
        <div
          className="fixed inset-0 bg-gray-500 bg-opacity-75"
          onClick={onClose}
        ></div>
        <div className="relative bg-white rounded-lg shadow-xl max-w-lg w-full p-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-medium text-gray-900">
              {isEdit ? "施設を編集" : "施設を登録"}
            </h3>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-500">
              <X className="h-5 w-5" />
            </button>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-50 rounded-lg flex items-center text-red-700">
              <AlertCircle className="h-5 w-5 mr-2" />
              <span className="text-sm">{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                施設名 <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                required
                value={formData.name}
                onChange={(e) => handleChange("name", e.target.value)}
                className="block w-full px-3 py-2 border border-gray-300 rounded-lg text-gray-900 focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
                placeholder="〇〇ホテル"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                郵便番号
              </label>
              <input
                type="text"
                value={formData.postal_code}
                onChange={(e) => handleChange("postal_code", e.target.value)}
                className="block w-full px-3 py-2 border border-gray-300 rounded-lg text-gray-900 focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
                placeholder="123-4567"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                住所 <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                required
                value={formData.address}
                onChange={(e) => handleChange("address", e.target.value)}
                className="block w-full px-3 py-2 border border-gray-300 rounded-lg text-gray-900 focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
                placeholder="東京都〇〇区〇〇1-2-3"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                電話番号
              </label>
              <input
                type="tel"
                value={formData.phone}
                onChange={(e) => handleChange("phone", e.target.value)}
                className="block w-full px-3 py-2 border border-gray-300 rounded-lg text-gray-900 focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
                placeholder="03-1234-5678"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                ウェブサイト
              </label>
              <input
                type="url"
                value={formData.website}
                onChange={(e) => handleChange("website", e.target.value)}
                className="block w-full px-3 py-2 border border-gray-300 rounded-lg text-gray-900 focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
                placeholder="https://example.com"
              />
            </div>

            <div className="flex justify-end space-x-3 mt-6">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                キャンセル
              </button>
              <button
                type="submit"
                disabled={loading}
                className="px-4 py-2 text-sm font-medium text-white bg-teal-600 rounded-lg hover:bg-teal-700 disabled:opacity-50"
              >
                {loading
                  ? isEdit
                    ? "更新中..."
                    : "登録中..."
                  : isEdit
                    ? "更新"
                    : "登録"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}


