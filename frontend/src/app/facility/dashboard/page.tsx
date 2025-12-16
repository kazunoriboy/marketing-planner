"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { facilityApi, HotelResponse } from "@/lib/api";
import { Building2, MapPin, Plus, ArrowRight } from "lucide-react";

export default function FacilityDashboardPage() {
  const [hotels, setHotels] = useState<HotelResponse[]>([]);
  const [loading, setLoading] = useState(true);

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

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-teal-600"></div>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">ダッシュボード</h1>
        <p className="mt-1 text-sm text-gray-500">
          管理している施設の概要を確認できます
        </p>
      </div>

      {/* 施設カード */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {hotels.length === 0 ? (
          <div className="col-span-full bg-white rounded-lg shadow p-8 text-center">
            <Building2 className="mx-auto h-12 w-12 text-gray-400 mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              施設がまだ登録されていません
            </h3>
            <p className="text-sm text-gray-500 mb-4">
              最初の施設を登録して、マーケティング分析を始めましょう
            </p>
            <Link
              href="/facility/hotels"
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-teal-600 hover:bg-teal-700"
            >
              <Plus className="h-4 w-4 mr-2" />
              施設を登録
            </Link>
          </div>
        ) : (
          hotels.map((hotel) => (
            <div
              key={hotel.id}
              className="bg-white overflow-hidden shadow rounded-lg"
            >
              <div className="p-5">
                <div className="flex items-center">
                  <div className="flex-shrink-0 bg-teal-100 rounded-md p-3">
                    <Building2 className="h-6 w-6 text-teal-600" />
                  </div>
                  <div className="ml-4 flex-1">
                    <h3 className="text-lg font-medium text-gray-900 truncate">
                      {hotel.name}
                    </h3>
                    <div className="flex items-center text-sm text-gray-500 mt-1">
                      <MapPin className="h-4 w-4 mr-1 flex-shrink-0" />
                      <span className="truncate">{hotel.address}</span>
                    </div>
                  </div>
                </div>
                <div className="mt-4 flex justify-between items-center">
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
                  <Link
                    href={`/facility/hotels/${hotel.id}`}
                    className="inline-flex items-center text-sm text-teal-600 hover:text-teal-500"
                  >
                    詳細
                    <ArrowRight className="ml-1 h-4 w-4" />
                  </Link>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* クイックアクション */}
      {hotels.length > 0 && (
        <div className="mt-8 bg-white shadow rounded-lg p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">
            クイックアクション
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <Link
              href="/facility/hotels"
              className="flex items-center p-4 border border-gray-200 rounded-lg hover:border-teal-500 hover:bg-teal-50 transition-colors"
            >
              <Building2 className="h-8 w-8 text-teal-600" />
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-900">施設管理</p>
                <p className="text-xs text-gray-500">施設の追加・編集</p>
              </div>
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
