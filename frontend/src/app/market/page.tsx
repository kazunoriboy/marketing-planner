'use client';

// 市場分析ページ
export default function MarketPage() {
  return (
    <section className="animate-fadeIn">
      <h2 className="text-3xl font-bold text-white mb-2">市場を知る</h2>
      <p className="text-slate-400 mb-8">競合分析と市場動向を把握し、戦略的なマーケティングを行います</p>

      {/* 口コミ分析サマリー */}
      <div className="glass-card p-8">
        <h3 className="text-2xl font-bold text-white mb-6">口コミ分析サマリー</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div>
            <h4 className="text-lg font-semibold text-white mb-4">あなたの旅館</h4>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-slate-300">総合評価</span>
                <span className="text-yellow-400 font-semibold">4.2/5.0</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-300">温泉の質</span>
                <span className="text-green-400 font-semibold">4.5/5.0</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-300">料理</span>
                <span className="text-blue-400 font-semibold">4.1/5.0</span>
              </div>
            </div>
          </div>
          <div>
            <h4 className="text-lg font-semibold text-white mb-4">競合A</h4>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-slate-300">総合評価</span>
                <span className="text-yellow-400 font-semibold">3.8/5.0</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-300">温泉の質</span>
                <span className="text-green-400 font-semibold">4.0/5.0</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-300">料理</span>
                <span className="text-blue-400 font-semibold">3.6/5.0</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}



