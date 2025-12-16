'use client';

import { 
  Sparkles,
  UserCheck,
  Swords,
  Building
} from 'lucide-react';

// ダッシュボードページ
export default function Dashboard() {
  return (
    <section className="animate-fadeIn">
      <h2 className="text-3xl font-bold text-white mb-2">ダッシュボード</h2>
      <p className="text-slate-400 mb-8">旅館のマーケティング状況を一覧で確認できます</p>

      {/* AIからの提案 */}
      <div className="glass-card p-8 mb-8">
        <div className="flex items-center gap-4 mb-6">
          <div className="w-12 h-12 bg-gradient-to-r from-purple-500 to-cyan-500 rounded-lg flex items-center justify-center">
            <Sparkles className="w-6 h-6 text-white" />
          </div>
          <h3 className="text-2xl font-bold text-white">AIからの提案</h3>
        </div>
        <p className="text-slate-300 text-lg">
          今月の顧客満足度が向上しています。温泉の魅力をより効果的に伝えるコンテンツ作成をお勧めします。
        </p>
      </div>

      {/* 3列グリッド */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="glass-card p-6">
          <div className="flex items-center gap-3 mb-4">
            <UserCheck className="w-6 h-6 text-blue-400" />
            <h4 className="text-lg font-semibold text-white">ターゲット顧客</h4>
          </div>
          <p className="text-slate-300">30-50代の夫婦、リピート率85%</p>
        </div>

        <div className="glass-card p-6">
          <div className="flex items-center gap-3 mb-4">
            <Swords className="w-6 h-6 text-green-400" />
            <h4 className="text-lg font-semibold text-white">旅館の強み・弱み</h4>
          </div>
          <p className="text-slate-300">温泉の質は高評価、アクセス改善が必要</p>
        </div>

        <div className="glass-card p-6">
          <div className="flex items-center gap-3 mb-4">
            <Building className="w-6 h-6 text-orange-400" />
            <h4 className="text-lg font-semibold text-white">競合の動向</h4>
          </div>
          <p className="text-slate-300">新規オープンが増加、差別化が重要</p>
        </div>
      </div>
    </section>
  );
}
