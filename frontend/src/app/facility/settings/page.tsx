"use client";

import { useState } from "react";
import { facilityApi, ApiError } from "@/lib/api";
import { validatePassword } from "@/lib/auth";
import { Lock, AlertCircle, CheckCircle } from "lucide-react";

export default function FacilitySettingsPage() {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordErrors, setPasswordErrors] = useState<string[]>([]);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  const handleNewPasswordChange = (value: string) => {
    setNewPassword(value);
    const { errors } = validatePassword(value);
    setPasswordErrors(errors);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    // バリデーション
    if (newPassword !== confirmPassword) {
      setError("新しいパスワードが一致しません");
      return;
    }

    const { isValid, errors } = validatePassword(newPassword);
    if (!isValid) {
      setPasswordErrors(errors);
      return;
    }

    setLoading(true);

    try {
      await facilityApi.changePassword(currentPassword, newPassword);
      setSuccess("パスワードを変更しました");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setPasswordErrors([]);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail);
      } else {
        setError("パスワードの変更に失敗しました");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">設定</h1>
        <p className="mt-1 text-sm text-gray-500">
          アカウント設定を管理できます
        </p>
      </div>

      {/* パスワード変更 */}
      <div className="bg-white shadow rounded-lg overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex items-center">
            <Lock className="h-5 w-5 text-gray-400 mr-2" />
            <h3 className="text-lg font-medium text-gray-900">
              パスワード変更
            </h3>
          </div>
        </div>
        <div className="p-6">
          {error && (
            <div className="mb-4 p-3 bg-red-50 rounded-lg flex items-center text-red-700">
              <AlertCircle className="h-5 w-5 mr-2" />
              <span className="text-sm">{error}</span>
            </div>
          )}

          {success && (
            <div className="mb-4 p-3 bg-green-50 rounded-lg flex items-center text-green-700">
              <CheckCircle className="h-5 w-5 mr-2" />
              <span className="text-sm">{success}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="max-w-md space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                現在のパスワード
              </label>
              <input
                type="password"
                required
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                className="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                新しいパスワード
              </label>
              <input
                type="password"
                required
                value={newPassword}
                onChange={(e) => handleNewPasswordChange(e.target.value)}
                className="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
              />
              {passwordErrors.length > 0 && (
                <ul className="mt-2 text-xs text-red-600">
                  {passwordErrors.map((err, i) => (
                    <li key={i}>• {err}</li>
                  ))}
                </ul>
              )}
              <p className="mt-1 text-xs text-gray-500">
                8文字以上、英大文字・英小文字・数字を含む
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                新しいパスワード（確認）
              </label>
              <input
                type="password"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
              />
            </div>

            <button
              type="submit"
              disabled={loading || passwordErrors.length > 0}
              className="px-4 py-2 text-sm font-medium text-white bg-teal-600 rounded-lg hover:bg-teal-700 disabled:opacity-50"
            >
              {loading ? "変更中..." : "パスワードを変更"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

