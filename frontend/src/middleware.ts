import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * 認証ミドルウェア
 * 
 * 保護されたパスへのアクセスを制御します。
 * 注意: localStorageはサーバーサイドで使用できないため、
 * このミドルウェアはクライアントサイドの認証チェックを補完するものです。
 * 実際の認証チェックは各ページのlayout.tsxで行われます。
 */
export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // 公開パス（認証不要）
  const publicPaths = [
    "/",
    "/admin/login",
    "/facility/login",
  ];

  // 公開パスの場合はそのまま通す
  if (publicPaths.includes(pathname)) {
    return NextResponse.next();
  }

  // 静的ファイルとAPIルートはスキップ
  if (
    pathname.startsWith("/_next") ||
    pathname.startsWith("/api") ||
    pathname.includes(".")
  ) {
    return NextResponse.next();
  }

  // /admin/* へのアクセス（ログインページ以外）
  if (pathname.startsWith("/admin") && pathname !== "/admin/login") {
    // クライアントサイドでの認証チェックに委ねる
    // layout.tsxで認証状態を確認し、未認証の場合はリダイレクト
    return NextResponse.next();
  }

  // /facility/* へのアクセス（ログインページ以外）
  if (pathname.startsWith("/facility") && pathname !== "/facility/login") {
    // クライアントサイドでの認証チェックに委ねる
    // layout.tsxで認証状態を確認し、未認証の場合はリダイレクト
    return NextResponse.next();
  }

  // /marketing/* へのアクセス
  if (pathname.startsWith("/marketing")) {
    // クライアントサイドでの認証チェックに委ねる
    // layout.tsxで認証状態と施設へのアクセス権限を確認
    return NextResponse.next();
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    "/((?!api|_next/static|_next/image|favicon.ico).*)",
  ],
};

