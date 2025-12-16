"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { BrainCircuit, Building2, Shield } from "lucide-react";
import Link from "next/link";
import { hasToken } from "@/lib/auth";

// ランディングページ
export default function HomePage() {
  const router = useRouter();

  useEffect(() => {
    // 施設管理者としてログイン済みの場合は施設一覧へリダイレクト
    if (hasToken("facility")) {
      router.push("/facility/hotels");
    }
  }, [router]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center p-4">
      <div className="max-w-4xl w-full">
        {/* ヘッダー */}
        <div className="text-center mb-12">
          <div className="w-20 h-20 bg-gradient-to-r from-purple-500 to-cyan-500 rounded-2xl flex items-center justify-center mx-auto mb-6">
            <BrainCircuit className="w-10 h-10 text-white" />
          </div>
          <h1 className="text-4xl md:text-5xl font-bold text-white mb-4">
            旅館AIマーケティング
          </h1>
          <p className="text-xl text-slate-300 max-w-2xl mx-auto">
            AIの力で旅館・ホテルのマーケティングを最適化。
            顧客分析から広告制作まで、すべてをサポートします。
          </p>
        </div>

        {/* ログインカード */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* 施設管理者ログイン */}
          <Link
            href="/facility/login"
            className="glass-card p-8 hover:bg-white/10 transition-colors cursor-pointer group"
          >
            <div className="flex items-center gap-4 mb-4">
              <div className="w-12 h-12 bg-teal-500/20 rounded-lg flex items-center justify-center group-hover:bg-teal-500/30 transition-colors">
                <Building2 className="w-6 h-6 text-teal-400" />
              </div>
              <h2 className="text-2xl font-bold text-white">施設管理者</h2>
            </div>
            <p className="text-slate-300 mb-4">
              施設のマーケティング機能を利用する方はこちらからログインしてください。
            </p>
            <span className="inline-flex items-center text-teal-400 font-medium group-hover:text-teal-300">
              ログイン →
            </span>
          </Link>

          {/* システム管理者ログイン */}
          <Link
            href="/admin/login"
            className="glass-card p-8 hover:bg-white/10 transition-colors cursor-pointer group"
          >
            <div className="flex items-center gap-4 mb-4">
              <div className="w-12 h-12 bg-blue-500/20 rounded-lg flex items-center justify-center group-hover:bg-blue-500/30 transition-colors">
                <Shield className="w-6 h-6 text-blue-400" />
              </div>
              <h2 className="text-2xl font-bold text-white">システム管理者</h2>
            </div>
            <p className="text-slate-300 mb-4">
              施設管理者アカウントの管理を行う方はこちらからログインしてください。
            </p>
            <span className="inline-flex items-center text-blue-400 font-medium group-hover:text-blue-300">
              ログイン →
            </span>
          </Link>
        </div>

        {/* フッター */}
        <div className="text-center mt-12 text-slate-500 text-sm">
          <p>© 2024 旅館AIマーケティング. All rights reserved.</p>
        </div>
      </div>
    </div>
  );
}
