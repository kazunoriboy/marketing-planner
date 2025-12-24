'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  BrainCircuit, 
  BarChart3, 
  Users, 
  TrendingUp, 
  FileText, 
  Settings,
  MessageSquare
} from 'lucide-react';

// ナビゲーションアイテム
const navItems = [
  { id: 'dashboard', path: '/', icon: BarChart3, label: 'ダッシュボード' },
  { id: 'persona', path: '/persona', icon: Users, label: '顧客を知る' },
  { id: 'market', path: '/market', icon: TrendingUp, label: '市場を知る' },
  { id: 'planner', path: '/planner', icon: FileText, label: 'プランを立てる' },
  { id: 'content', path: '/content', icon: MessageSquare, label: '発信する' },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <div className="w-64 glass-card p-6 flex flex-col h-full">
      {/* ヘッダー */}
      <Link href="/" className="flex items-center gap-3 mb-8 hover:opacity-80 transition-opacity">
        <div className="w-10 h-10 bg-gradient-to-r from-purple-500 to-cyan-500 rounded-lg flex items-center justify-center">
          <BrainCircuit className="w-6 h-6 text-white" />
        </div>
        <h1 className="text-xl font-bold text-white">旅館AIアシスタント</h1>
      </Link>

      {/* ナビゲーション */}
      <nav className="flex-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.path;
          return (
            <Link
              key={item.id}
              href={item.path}
              className={`flex items-center gap-3 px-4 py-3 rounded-lg mb-2 cursor-pointer transition-colors w-full text-left ${
                isActive ? 'bg-white/10' : 'hover:bg-white/5'
              }`}
            >
              <Icon className="w-5 h-5" />
              <span className="text-slate-200">{item.label}</span>
            </Link>
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




