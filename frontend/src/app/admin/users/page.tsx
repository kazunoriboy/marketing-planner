"use client";

import { useEffect, useState } from "react";
import {
  adminApi,
  FacilityAdminResponse,
  ApiError,
  CompanyResponse,
  FacilityAdminCreateRequest,
} from "@/lib/api";
import { validatePassword } from "@/lib/auth";
import {
  Users,
  Plus,
  Pencil,
  Trash2,
  Building2,
  AlertCircle,
  X,
  Check,
} from "lucide-react";

type UserWithCount = FacilityAdminResponse & { 
  hotel_count: number;
  company_id?: number;
  company_name?: string;
};

export default function AdminUsersPage() {
  const [users, setUsers] = useState<UserWithCount[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingUser, setEditingUser] = useState<UserWithCount | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<number | null>(null);

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    try {
      const data = await adminApi.listUsers();
      setUsers(data);
    } catch (error) {
      console.error("Failed to load users:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (userId: number) => {
    try {
      await adminApi.deleteUser(userId);
      setUsers(users.filter((u) => u.id !== userId));
      setDeleteConfirm(null);
    } catch (error) {
      console.error("Failed to delete user:", error);
    }
  };

  const handleToggleActive = async (user: UserWithCount) => {
    try {
      await adminApi.updateUser(user.id, { is_active: !user.is_active });
      setUsers(
        users.map((u) =>
          u.id === user.id ? { ...u, is_active: !u.is_active } : u
        )
      );
    } catch (error) {
      console.error("Failed to update user:", error);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-8 flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">ユーザー管理</h1>
          <p className="mt-1 text-sm text-gray-500">
            施設管理者の作成・編集・削除ができます
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
        >
          <Plus className="h-4 w-4 mr-2" />
          新規作成
        </button>
      </div>

      {/* ユーザーテーブル */}
      <div className="bg-white shadow rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                ユーザー
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                企業グループ
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                施設数
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                ステータス
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                アクション
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {users.length === 0 ? (
              <tr>
                <td
                  colSpan={5}
                  className="px-6 py-12 text-center text-sm text-gray-500"
                >
                  <Users className="mx-auto h-12 w-12 text-gray-400 mb-4" />
                  <p>施設管理者がまだ登録されていません</p>
                  <button
                    onClick={() => setShowCreateModal(true)}
                    className="mt-4 text-indigo-600 hover:text-indigo-500"
                  >
                    最初のユーザーを作成する
                  </button>
                </td>
              </tr>
            ) : (
              users.map((user) => (
                <tr key={user.id}>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <div className="h-10 w-10 flex-shrink-0 bg-indigo-100 rounded-full flex items-center justify-center">
                        <span className="text-indigo-600 font-medium">
                          {user.name.charAt(0).toUpperCase()}
                        </span>
                      </div>
                      <div className="ml-4">
                        <div className="text-sm font-medium text-gray-900">
                          {user.name}
                        </div>
                        <div className="text-sm text-gray-500">{user.email}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900">
                      {user.company_name || (
                        <span className="text-gray-400">未所属</span>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center text-sm text-gray-500">
                      <Building2 className="h-4 w-4 mr-1" />
                      {user.hotel_count}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <button
                      onClick={() => handleToggleActive(user)}
                      className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                        user.is_active
                          ? "bg-green-100 text-green-800 hover:bg-green-200"
                          : "bg-red-100 text-red-800 hover:bg-red-200"
                      }`}
                    >
                      {user.is_active ? "アクティブ" : "非アクティブ"}
                    </button>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <button
                      onClick={() => setEditingUser(user)}
                      className="text-indigo-600 hover:text-indigo-900 mr-3"
                      title="編集"
                    >
                      <Pencil className="h-4 w-4" />
                    </button>
                    {deleteConfirm === user.id ? (
                      <span className="inline-flex items-center">
                        <button
                          onClick={() => handleDelete(user.id)}
                          className="text-red-600 hover:text-red-900 mr-2"
                          title="削除を確定"
                        >
                          <Check className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => setDeleteConfirm(null)}
                          className="text-gray-400 hover:text-gray-600"
                          title="キャンセル"
                        >
                          <X className="h-4 w-4" />
                        </button>
                      </span>
                    ) : (
                      <button
                        onClick={() => setDeleteConfirm(user.id)}
                        className="text-red-600 hover:text-red-900"
                        title="削除"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* 作成モーダル */}
      {showCreateModal && (
        <CreateUserModal
          onClose={() => setShowCreateModal(false)}
          onCreated={(user) => {
            setUsers([...users, { ...user, hotel_count: 0 }]);
            setShowCreateModal(false);
          }}
        />
      )}

      {/* 編集モーダル */}
      {editingUser && (
        <EditUserModal
          user={editingUser}
          onClose={() => setEditingUser(null)}
          onUpdated={(updated) => {
            setUsers(
              users.map((u) =>
                u.id === updated.id ? { ...u, ...updated } : u
              )
            );
            setEditingUser(null);
          }}
        />
      )}
    </div>
  );
}

// 作成モーダル
function CreateUserModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: (user: FacilityAdminResponse) => void;
}) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [companyId, setCompanyId] = useState<number | undefined>(undefined);
  const [companies, setCompanies] = useState<CompanyResponse[]>([]);
  const [loadingCompanies, setLoadingCompanies] = useState(false);
  const [showNewCompanyInput, setShowNewCompanyInput] = useState(false);
  const [newCompanyName, setNewCompanyName] = useState("");
  const [error, setError] = useState("");
  const [passwordErrors, setPasswordErrors] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadCompanies();
  }, []);

  const loadCompanies = async () => {
    setLoadingCompanies(true);
    try {
      const data = await adminApi.listCompanies();
      setCompanies(data);
    } catch (error) {
      console.error("Failed to load companies:", error);
    } finally {
      setLoadingCompanies(false);
    }
  };

  const handlePasswordChange = (value: string) => {
    setPassword(value);
    const { errors } = validatePassword(value);
    setPasswordErrors(errors);
  };

  const handleCreateCompany = async () => {
    if (!newCompanyName.trim()) {
      setError("企業グループ名を入力してください");
      return;
    }

    try {
      const company = await adminApi.createCompany({ name: newCompanyName });
      setCompanies([...companies, company]);
      setCompanyId(company.id);
      setShowNewCompanyInput(false);
      setNewCompanyName("");
      setError("");
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail);
      } else {
        setError("企業グループの作成に失敗しました");
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    const { isValid, errors } = validatePassword(password);
    if (!isValid) {
      setPasswordErrors(errors);
      return;
    }

    setLoading(true);

    try {
      const request: FacilityAdminCreateRequest = {
        name,
        email,
        password,
        company_id: companyId,
      };
      const user = await adminApi.createUser(request);
      onCreated(user);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail);
      } else {
        setError("作成に失敗しました");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen px-4">
        <div
          className="fixed inset-0 bg-gray-500 bg-opacity-75"
          onClick={onClose}
        ></div>
        <div className="relative bg-white rounded-lg shadow-xl max-w-md w-full p-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-medium text-gray-900">
              施設管理者を作成
            </h3>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-500">
              <X className="h-5 w-5" />
            </button>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-50 rounded-lg flex items-center text-red-700">
              <AlertCircle className="h-5 w-5 mr-2" />
              <span className="text-sm">{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                名前
              </label>
              <input
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="block w-full px-3 py-2 border border-gray-300 rounded-lg text-gray-900 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                メールアドレス
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="block w-full px-3 py-2 border border-gray-300 rounded-lg text-gray-900 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                パスワード
              </label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => handlePasswordChange(e.target.value)}
                className="block w-full px-3 py-2 border border-gray-300 rounded-lg text-gray-900 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
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
                企業グループ（オプション）
              </label>
              {loadingCompanies ? (
                <div className="text-sm text-gray-500">読み込み中...</div>
              ) : (
                <>
                  <select
                    value={companyId || ""}
                    onChange={(e) => {
                      const value = e.target.value;
                      setCompanyId(value ? parseInt(value) : undefined);
                      setShowNewCompanyInput(false);
                    }}
                    className="block w-full px-3 py-2 border border-gray-300 rounded-lg text-gray-900 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  >
                    <option value="">企業グループを選択しない</option>
                    {companies.map((company) => (
                      <option key={company.id} value={company.id}>
                        {company.name}
                      </option>
                    ))}
                  </select>
                  <div className="mt-2 flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => {
                        setShowNewCompanyInput(!showNewCompanyInput);
                        if (!showNewCompanyInput) {
                          setCompanyId(undefined);
                        }
                      }}
                      className="text-sm text-indigo-600 hover:text-indigo-500"
                    >
                      {showNewCompanyInput ? "キャンセル" : "+ 新規企業グループを作成"}
                    </button>
                  </div>
                  {showNewCompanyInput && (
                    <div className="mt-2 flex gap-2">
                      <input
                        type="text"
                        placeholder="企業グループ名"
                        value={newCompanyName}
                        onChange={(e) => setNewCompanyName(e.target.value)}
                        className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-gray-900 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                      />
                      <button
                        type="button"
                        onClick={handleCreateCompany}
                        className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700"
                      >
                        作成
                      </button>
                    </div>
                  )}
                  <p className="mt-1 text-xs text-gray-500">
                    同じ企業グループに所属する管理者は、互いに作成した施設に自動的にアクセスできます
                  </p>
                </>
              )}
            </div>

            <div className="flex justify-end space-x-3 mt-6">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                キャンセル
              </button>
              <button
                type="submit"
                disabled={loading || passwordErrors.length > 0}
                className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 disabled:opacity-50"
              >
                {loading ? "作成中..." : "作成"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

// 編集モーダル
function EditUserModal({
  user,
  onClose,
  onUpdated,
}: {
  user: UserWithCount;
  onClose: () => void;
  onUpdated: (user: FacilityAdminResponse) => void;
}) {
  const [name, setName] = useState(user.name);
  const [companyId, setCompanyId] = useState<number | undefined | null>(undefined);
  const [companies, setCompanies] = useState<CompanyResponse[]>([]);
  const [loadingCompanies, setLoadingCompanies] = useState(false);
  const [showNewCompanyInput, setShowNewCompanyInput] = useState(false);
  const [newCompanyName, setNewCompanyName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadCompanies();
    loadUserDetail();
  }, []);

  const loadCompanies = async () => {
    setLoadingCompanies(true);
    try {
      const data = await adminApi.listCompanies();
      setCompanies(data);
    } catch (error) {
      console.error("Failed to load companies:", error);
    } finally {
      setLoadingCompanies(false);
    }
  };

  const loadUserDetail = async () => {
    try {
      const userDetail = await adminApi.getUser(user.id);
      setCompanyId(userDetail.company_id ?? null);
    } catch (error) {
      console.error("Failed to load user detail:", error);
    }
  };

  const handleCreateCompany = async () => {
    if (!newCompanyName.trim()) {
      setError("企業グループ名を入力してください");
      return;
    }

    try {
      const company = await adminApi.createCompany({ name: newCompanyName });
      setCompanies([...companies, company]);
      setCompanyId(company.id);
      setShowNewCompanyInput(false);
      setNewCompanyName("");
      setError("");
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail);
      } else {
        setError("企業グループの作成に失敗しました");
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const updateData: { name: string; company_id?: number | null } = { name };
      if (companyId !== undefined) {
        updateData.company_id = companyId === null ? 0 : companyId; // 0を送信するとNULLに設定される
      }
      const updated = await adminApi.updateUser(user.id, updateData);
      onUpdated(updated);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail);
      } else {
        setError("更新に失敗しました");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen px-4">
        <div
          className="fixed inset-0 bg-gray-500 bg-opacity-75"
          onClick={onClose}
        ></div>
        <div className="relative bg-white rounded-lg shadow-xl max-w-md w-full p-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-medium text-gray-900">
              施設管理者を編集
            </h3>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-500">
              <X className="h-5 w-5" />
            </button>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-50 rounded-lg flex items-center text-red-700">
              <AlertCircle className="h-5 w-5 mr-2" />
              <span className="text-sm">{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                名前
              </label>
              <input
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="block w-full px-3 py-2 border border-gray-300 rounded-lg text-gray-900 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                メールアドレス
              </label>
              <input
                type="email"
                disabled
                value={user.email}
                className="block w-full px-3 py-2 border border-gray-200 rounded-lg bg-gray-50 text-gray-700"
              />
              <p className="mt-1 text-xs text-gray-500">
                メールアドレスは変更できません
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                企業グループ
              </label>
              {loadingCompanies ? (
                <div className="text-sm text-gray-500">読み込み中...</div>
              ) : (
                <>
                  <select
                    value={companyId ?? ""}
                    onChange={(e) => {
                      const value = e.target.value;
                      setCompanyId(value ? parseInt(value) : null);
                      setShowNewCompanyInput(false);
                    }}
                    className="block w-full px-3 py-2 border border-gray-300 rounded-lg text-gray-900 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  >
                    <option value="">企業グループを選択しない</option>
                    {companies.map((company) => (
                      <option key={company.id} value={company.id}>
                        {company.name}
                      </option>
                    ))}
                  </select>
                  <div className="mt-2 flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => {
                        setShowNewCompanyInput(!showNewCompanyInput);
                        if (!showNewCompanyInput) {
                          setCompanyId(null);
                        }
                      }}
                      className="text-sm text-indigo-600 hover:text-indigo-500"
                    >
                      {showNewCompanyInput ? "キャンセル" : "+ 新規企業グループを作成"}
                    </button>
                  </div>
                  {showNewCompanyInput && (
                    <div className="mt-2 flex gap-2">
                      <input
                        type="text"
                        placeholder="企業グループ名"
                        value={newCompanyName}
                        onChange={(e) => setNewCompanyName(e.target.value)}
                        className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-gray-900 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                      />
                      <button
                        type="button"
                        onClick={handleCreateCompany}
                        className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700"
                      >
                        作成
                      </button>
                    </div>
                  )}
                  <p className="mt-1 text-xs text-gray-500">
                    同じ企業グループに所属する管理者は、互いに作成した施設に自動的にアクセスできます
                  </p>
                </>
              )}
            </div>

            <div className="flex justify-end space-x-3 mt-6">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                キャンセル
              </button>
              <button
                type="submit"
                disabled={loading}
                className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 disabled:opacity-50"
              >
                {loading ? "更新中..." : "更新"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}


