"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { checkAdminAuth, AuthState } from "@/lib/auth";
import { adminApi, SystemAdminResponse } from "@/lib/api";
import {
  LayoutDashboard,
  Users,
  LogOut,
  Menu,
  X,
  Shield,
} from "lucide-react";

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const [authState, setAuthState] = useState<AuthState<SystemAdminResponse>>({
    isAuthenticated: false,
    user: null,
    loading: true,
    error: null,
  });
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // ログインページは認証不要
  const isLoginPage = pathname === "/admin/login";

  useEffect(() => {
    if (isLoginPage) {
      setAuthState((prev) => ({ ...prev, loading: false }));
      return;
    }

    checkAdminAuth().then((state) => {
      setAuthState(state);
      if (!state.isAuthenticated) {
        router.push("/admin/login");
      }
    });
  }, [isLoginPage, router]);

  const handleLogout = () => {
    adminApi.logout();
    router.push("/admin/login");
  };

  // ログインページの場合はレイアウトなしで表示
  if (isLoginPage) {
    return <>{children}</>;
  }

  // ローディング中
  if (authState.loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-100">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  // 未認証
  if (!authState.isAuthenticated) {
    return null;
  }

  const navigation = [
    {
      name: "ダッシュボード",
      href: "/admin/dashboard",
      icon: LayoutDashboard,
    },
    { name: "ユーザー管理", href: "/admin/users", icon: Users },
  ];

  return (
    <div className="min-h-screen bg-gray-100">
      {/* モバイルサイドバー */}
      <div
        className={`fixed inset-0 z-40 lg:hidden ${sidebarOpen ? "" : "hidden"}`}
      >
        <div
          className="fixed inset-0 bg-gray-600 bg-opacity-75"
          onClick={() => setSidebarOpen(false)}
        ></div>
        <div className="fixed inset-y-0 left-0 flex flex-col w-64 bg-indigo-700">
          <div className="flex items-center justify-between h-16 px-4">
            <div className="flex items-center">
              <Shield className="h-8 w-8 text-white" />
              <span className="ml-2 text-white font-semibold">Admin</span>
            </div>
            <button
              onClick={() => setSidebarOpen(false)}
              className="text-white"
            >
              <X className="h-6 w-6" />
            </button>
          </div>
          <nav className="flex-1 px-2 py-4 space-y-1">
            {navigation.map((item) => (
              <Link
                key={item.name}
                href={item.href}
                className={`flex items-center px-4 py-2 text-sm font-medium rounded-md ${
                  pathname === item.href
                    ? "bg-indigo-800 text-white"
                    : "text-indigo-100 hover:bg-indigo-600"
                }`}
              >
                <item.icon className="mr-3 h-5 w-5" />
                {item.name}
              </Link>
            ))}
          </nav>
        </div>
      </div>

      {/* デスクトップサイドバー */}
      <div className="hidden lg:fixed lg:inset-y-0 lg:flex lg:w-64 lg:flex-col">
        <div className="flex flex-col flex-1 bg-indigo-700">
          <div className="flex items-center h-16 px-4">
            <Shield className="h-8 w-8 text-white" />
            <span className="ml-2 text-white font-semibold text-lg">
              System Admin
            </span>
          </div>
          <nav className="flex-1 px-2 py-4 space-y-1">
            {navigation.map((item) => (
              <Link
                key={item.name}
                href={item.href}
                className={`flex items-center px-4 py-2 text-sm font-medium rounded-md ${
                  pathname === item.href
                    ? "bg-indigo-800 text-white"
                    : "text-indigo-100 hover:bg-indigo-600"
                }`}
              >
                <item.icon className="mr-3 h-5 w-5" />
                {item.name}
              </Link>
            ))}
          </nav>
          <div className="p-4 border-t border-indigo-600">
            <div className="flex items-center">
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-white truncate">
                  {authState.user?.name}
                </p>
                <p className="text-xs text-indigo-200 truncate">
                  {authState.user?.email}
                </p>
              </div>
              <button
                onClick={handleLogout}
                className="ml-2 p-2 text-indigo-200 hover:text-white rounded-md hover:bg-indigo-600"
                title="ログアウト"
              >
                <LogOut className="h-5 w-5" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* メインコンテンツ */}
      <div className="lg:pl-64">
        {/* モバイルヘッダー */}
        <div className="sticky top-0 z-10 flex h-16 bg-white shadow lg:hidden">
          <button
            onClick={() => setSidebarOpen(true)}
            className="px-4 text-gray-500 focus:outline-none"
          >
            <Menu className="h-6 w-6" />
          </button>
          <div className="flex items-center flex-1 px-4">
            <Shield className="h-6 w-6 text-indigo-600" />
            <span className="ml-2 font-semibold text-gray-900">
              System Admin
            </span>
          </div>
        </div>

        <main className="py-6">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}

