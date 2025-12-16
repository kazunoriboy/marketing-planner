"use client";

import { useEffect, useState, useRef } from "react";
import { Upload, Users, Loader2, CheckCircle, AlertCircle } from "lucide-react";
import { useHotel } from "@/lib/hotel-context";
import { marketingApi, AnalysisSession, CSVAnalysisResponse } from "@/lib/api";

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
                    <div
                      key={key}
                      className="p-4 bg-white/5 rounded-lg border border-white/10"
                    >
                      <p className="text-sm text-slate-400 mb-1">{key}</p>
                      <p className="text-lg font-semibold text-white">
                        {typeof value === "object" ? JSON.stringify(value) : String(value)}
                      </p>
                    </div>
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
