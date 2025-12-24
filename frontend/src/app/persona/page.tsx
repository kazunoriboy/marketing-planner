'use client';

import { Plus } from 'lucide-react';

// ペルソナページ
export default function PersonaPage() {
  return (
    <section className="animate-fadeIn">
      <h2 className="text-3xl font-bold text-white mb-2">顧客を知る</h2>
      <p className="text-slate-400 mb-8">ターゲット顧客の詳細なペルソナを作成し、マーケティング戦略を最適化します</p>

      {/* 新しいペルソナ作成ボタン */}
      <button className="bg-gradient-to-r from-purple-500 to-cyan-500 text-white px-6 py-3 rounded-lg flex items-center gap-2 mb-8 hover:from-purple-600 hover:to-cyan-600 transition-all">
        <Plus className="w-5 h-5" />
        新しいペルソナを作成
      </button>

      {/* ペルソナカードグリッド */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div className="glass-card p-6">
          <div className="w-16 h-16 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full mb-4 flex items-center justify-center">
            <span className="text-white font-bold text-xl">田中</span>
          </div>
          <h4 className="text-lg font-semibold text-white mb-2">田中さん（45歳）</h4>
          <p className="text-slate-300 text-sm">
            会社員の夫婦。週末のリフレッシュを求めて温泉旅館を利用。価格よりも体験を重視する。
          </p>
        </div>

        <div className="glass-card p-6">
          <div className="w-16 h-16 bg-gradient-to-r from-green-500 to-blue-500 rounded-full mb-4 flex items-center justify-center">
            <span className="text-white font-bold text-xl">佐藤</span>
          </div>
          <h4 className="text-lg font-semibold text-white mb-2">佐藤さん（38歳）</h4>
          <p className="text-slate-300 text-sm">
            子育て中の母親。家族旅行で利用。子供が楽しめる施設やサービスを重視する。
          </p>
        </div>

        <div className="glass-card p-6">
          <div className="w-16 h-16 bg-gradient-to-r from-orange-500 to-red-500 rounded-full mb-4 flex items-center justify-center">
            <span className="text-white font-bold text-xl">山田</span>
          </div>
          <h4 className="text-lg font-semibold text-white mb-2">山田さん（52歳）</h4>
          <p className="text-slate-300 text-sm">
            定年退職後の夫婦。長期滞在を希望。静かな環境と質の高い料理を求める。
          </p>
        </div>
      </div>
    </section>
  );
}




