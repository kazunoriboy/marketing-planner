'use client';

import { useEffect, useState } from 'react';

interface BackendResponse {
  message: string;
}

export default function Home() {
  const [backendMessage, setBackendMessage] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    const fetchBackendData = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const response = await fetch(`${apiUrl}/`);
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data: BackendResponse = await response.json();
        setBackendMessage(data.message);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error occurred');
      } finally {
        setLoading(false);
      }
    };

    fetchBackendData();
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
      <div className="max-w-2xl w-full">
        <div className="bg-white rounded-lg shadow-xl p-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-8 text-center">
            宿泊業界向けマーケティングAIエージェント
          </h1>
          
          <div className="space-y-6">
            <div className="bg-gray-50 rounded-lg p-6">
              <h2 className="text-xl font-semibold text-gray-800 mb-4">
                バックエンド接続状況
              </h2>
              
              {loading && (
                <div className="flex items-center space-x-2">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                  <span className="text-gray-600">接続中...</span>
                </div>
              )}
              
              {error && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <p className="text-red-800">
                    <strong>エラー:</strong> {error}
                  </p>
                  <p className="text-red-600 text-sm mt-2">
                    バックエンドサーバーが起動していない可能性があります。
                  </p>
                </div>
              )}
              
              {backendMessage && !loading && !error && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                  <p className="text-green-800">
                    <strong>接続成功:</strong> {backendMessage}
                  </p>
                </div>
              )}
            </div>
            
            <div className="bg-blue-50 rounded-lg p-6">
              <h3 className="text-lg font-semibold text-blue-900 mb-3">
                開発環境情報
              </h3>
              <ul className="space-y-2 text-blue-800">
                <li>• フロントエンド: Next.js (TypeScript + Tailwind CSS)</li>
                <li>• バックエンド: FastAPI (Python 3.13)</li>
                <li>• データベース: PostgreSQL with pgvector</li>
                <li>• AI: LangChain + OpenAI + Google Gemini</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
