'use client';

import { useState, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { 
  BrainCircuit, 
  BarChart3, 
  Users, 
  TrendingUp, 
  FileText, 
  Settings,
  Sparkles,
  UserCheck,
  Swords,
  Building,
  Plus,
  MessageSquare,
  Lightbulb,
  Instagram
} from 'lucide-react';

// ナビゲーションアイテム
const navItems = [
  { id: 'dashboard', icon: BarChart3, label: 'ダッシュボード' },
  { id: 'persona', icon: Users, label: '顧客を知る' },
  { id: 'market', icon: TrendingUp, label: '市場を知る' },
  { id: 'planner', icon: FileText, label: 'プランを立てる' },
  { id: 'content', icon: MessageSquare, label: '発信する' },
];

// サイドバーコンポーネント
function Sidebar({ activeView, setActiveView }: { activeView: string; setActiveView: (view: string) => void }) {
  return (
    <div className="w-64 glass-card p-6 flex flex-col h-full">
      {/* ヘッダー */}
      <div className="flex items-center gap-3 mb-8">
        <div className="w-10 h-10 bg-gradient-to-r from-purple-500 to-cyan-500 rounded-lg flex items-center justify-center">
          <BrainCircuit className="w-6 h-6 text-white" />
        </div>
        <h1 className="text-xl font-bold text-white">旅館AIアシスタント</h1>
      </div>

      {/* ナビゲーション */}
      <nav className="flex-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              onClick={() => setActiveView(item.id)}
              className={`flex items-center gap-3 px-4 py-3 rounded-lg mb-2 cursor-pointer transition-colors w-full text-left ${
                activeView === item.id ? 'bg-white/10' : 'hover:bg-white/5'
              }`}
            >
              <Icon className="w-5 h-5" />
              <span className="text-slate-200">{item.label}</span>
            </button>
          );
        })}
      </nav>

      {/* フッター */}
      <div className="border-t border-white/10 pt-4">
        <button className="flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-white/5 cursor-pointer transition-colors w-full text-left">
          <Settings className="w-5 h-5" />
          <span className="text-slate-200">設定</span>
        </button>
      </div>
    </div>
  );
}

// ダッシュボードコンポーネント
function Dashboard() {
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

// ペルソナコンポーネント
function Persona() {
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

// 市場分析コンポーネント
function Market() {
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

// プランナーコンポーネント
function Planner() {
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

// コンテンツ作成コンポーネント
function Content() {
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
            <select className="bg-white/5 border border-white/10 rounded-lg p-3 text-slate-200 focus:outline-none focus:border-purple-500">
              <option>プラットフォームを選択</option>
              <option>Instagram</option>
              <option>Facebook</option>
              <option>Twitter</option>
            </select>
            <select className="bg-white/5 border border-white/10 rounded-lg p-3 text-slate-200 focus:outline-none focus:border-purple-500">
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

// メインコンポーネント
function Home() {
  const [activeView, setActiveView] = useState('dashboard');

  const renderContent = () => {
    switch (activeView) {
      case 'dashboard':
        return <Dashboard />;
      case 'persona':
        return <Persona />;
      case 'market':
        return <Market />;
      case 'planner':
        return <Planner />;
      case 'content':
        return <Content />;
      default:
        return <Dashboard />;
    }
  };

  return (
    <main className="flex h-screen overflow-hidden">
      <Sidebar activeView={activeView} setActiveView={setActiveView} />
      <div className="flex-1 p-8 overflow-y-auto">
        {renderContent()}
      </div>
    </main>
  );
}

// 動的インポートでSSRを無効化
export default dynamic(() => Promise.resolve(Home), {
  ssr: false,
  loading: () => (
    <main className="flex h-screen overflow-hidden">
      <div className="w-64 glass-card p-6 flex flex-col h-full">
        <div className="flex items-center gap-3 mb-8">
          <div className="w-10 h-10 bg-gradient-to-r from-purple-500 to-cyan-500 rounded-lg flex items-center justify-center">
            <BrainCircuit className="w-6 h-6 text-white" />
          </div>
          <h1 className="text-xl font-bold text-white">旅館AIアシスタント</h1>
        </div>
      </div>
      <div className="flex-1 p-8 overflow-y-auto">
        <div className="animate-fadeIn">
          <h2 className="text-3xl font-bold text-white mb-2">ダッシュボード</h2>
          <p className="text-slate-400 mb-8">旅館のマーケティング状況を一覧で確認できます</p>
        </div>
      </div>
    </main>
  )
});