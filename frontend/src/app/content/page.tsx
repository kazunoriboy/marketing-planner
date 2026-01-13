'use client';

import { Instagram } from 'lucide-react';

// コンテンツ作成ページ
export default function ContentPage() {
  return (
    <section className="animate-fadeIn">
      <h2 className="text-3xl font-bold text-white mb-2">発信する</h2>
      <p className="text-slate-400 mb-8">SNSやウェブサイト向けの魅力的なコンテンツを自動生成します</p>

      {/* SNS投稿ジェネレーター */}
      <div className="glass-card p-8">
        <div className="flex items-center gap-3 mb-6">
          <Instagram className="w-6 h-6 text-pink-400" />
          <h3 className="text-2xl font-bold text-white">SNS投稿ジェネレーター</h3>
        </div>
        
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <select className="bg-slate-800 border border-white/10 rounded-lg p-3 text-slate-200 focus:outline-none focus:border-purple-500 [&>option]:bg-slate-800 [&>option]:text-white">
              <option>プラットフォームを選択</option>
              <option>Instagram</option>
              <option>Facebook</option>
              <option>Twitter</option>
            </select>
            <select className="bg-slate-800 border border-white/10 rounded-lg p-3 text-slate-200 focus:outline-none focus:border-purple-500 [&>option]:bg-slate-800 [&>option]:text-white">
              <option>投稿タイプを選択</option>
              <option>温泉紹介</option>
              <option>料理紹介</option>
              <option>イベント告知</option>
            </select>
          </div>
          
          <button className="w-full bg-gradient-to-r from-purple-500 to-cyan-500 text-white py-4 rounded-lg hover:from-purple-600 hover:to-cyan-600 transition-all font-semibold">
            Instagramの投稿を作成
          </button>
          
          <div className="bg-white/5 border border-white/10 rounded-lg p-6">
            <h4 className="text-lg font-semibold text-white mb-3">生成された投稿</h4>
            <p className="text-slate-300 leading-relaxed">
              🌸 春の訪れとともに、当館の温泉も新緑の季節を迎えました。
              <br /><br />
              #温泉 #旅館 #春 #リフレッシュ #癒し
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}





