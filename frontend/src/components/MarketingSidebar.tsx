"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BrainCircuit,
  BarChart3,
  Users,
  TrendingUp,
  FileText,
  MessageSquare,
  ArrowLeft,
  Building2,
} from "lucide-react";
import { HotelResponse } from "@/lib/api";

interface MarketingSidebarProps {
  hotel: HotelResponse;
}

export default function MarketingSidebar({ hotel }: MarketingSidebarProps) {
  const pathname = usePathname();
  const basePath = `/marketing/${hotel.id}`;

  const navItems = [
    { id: "dashboard", path: `${basePath}/dashboard`, icon: BarChart3, label: "ダッシュボード" },
    { id: "persona", path: `${basePath}/persona`, icon: Users, label: "顧客を知る" },
    { id: "market", path: `${basePath}/market`, icon: TrendingUp, label: "市場を知る" },
    { id: "planner", path: `${basePath}/planner`, icon: FileText, label: "プランを立てる" },
    { id: "content", path: `${basePath}/content`, icon: MessageSquare, label: "発信する" },
  ];

  return (
    <div className="w-64 glass-card p-6 flex flex-col h-full">
      {/* ヘッダー */}
      <Link
        href={`${basePath}/dashboard`}
        className="flex items-center gap-3 mb-4 hover:opacity-80 transition-opacity"
      >
        <div className="w-10 h-10 bg-gradient-to-r from-purple-500 to-cyan-500 rounded-lg flex items-center justify-center">
          <BrainCircuit className="w-6 h-6 text-white" />
        </div>
        <h1 className="text-xl font-bold text-white">マーケティングAI</h1>
      </Link>

      {/* 施設情報 */}
      <div className="mb-6 p-3 bg-white/5 rounded-lg border border-white/10">
        <div className="flex items-center gap-2 text-slate-300">
          <Building2 className="w-4 h-4" />
          <span className="text-sm font-medium truncate">{hotel.name}</span>
        </div>
        <p className="text-xs text-slate-400 mt-1 truncate">{hotel.address}</p>
      </div>

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
                isActive ? "bg-white/10" : "hover:bg-white/5"
              }`}
            >
              <Icon className="w-5 h-5" />
              <span className="text-slate-200">{item.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* フッター - 施設一覧に戻る */}
      <div className="border-t border-white/10 pt-4">
        <Link
          href="/facility/hotels"
          className="flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-white/5 cursor-pointer transition-colors w-full text-left"
        >
          <ArrowLeft className="w-5 h-5" />
          <span className="text-slate-200">施設一覧に戻る</span>
        </Link>
      </div>
    </div>
  );
}


