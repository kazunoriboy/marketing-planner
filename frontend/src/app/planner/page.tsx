'use client';

import { Lightbulb } from 'lucide-react';

// プランナーページ
export default function PlannerPage() {
  return (
    <section className="animate-fadeIn">
      <h2 className="text-3xl font-bold text-white mb-2">プランを立てる</h2>
      <p className="text-slate-400 mb-8">AIを活用して効果的なマーケティングプランを作成します</p>

      {/* アイデア生成ワークスペース */}
      <div className="glass-card p-8">
        <div className="flex items-center gap-3 mb-6">
          <Lightbulb className="w-6 h-6 text-yellow-400" />
          <h3 className="text-2xl font-bold text-white">アイデア生成ワークスペース</h3>
        </div>
        <div className="space-y-4">
          <textarea
            placeholder="マーケティングの目標や課題を入力してください..."
            className="w-full h-32 bg-white/5 border border-white/10 rounded-lg p-4 text-slate-200 placeholder-slate-400 focus:outline-none focus:border-purple-500"
          />
          <button className="bg-gradient-to-r from-purple-500 to-cyan-500 text-white px-6 py-3 rounded-lg hover:from-purple-600 hover:to-cyan-600 transition-all">
            アイデアを生成
          </button>
        </div>
      </div>
    </section>
  );
}





