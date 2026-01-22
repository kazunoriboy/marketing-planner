"use client";

import { useEffect, useState } from "react";
import {
  adminApi,
  CompanyResponse,
  CompanyDetailResponse,
  ApiError,
} from "@/lib/api";
import {
  Building2,
  Plus,
  Pencil,
  Trash2,
  Users,
  AlertCircle,
  X,
  Check,
} from "lucide-react";

export default function AdminCompaniesPage() {
  const [companies, setCompanies] = useState<CompanyResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingCompany, setEditingCompany] = useState<CompanyResponse | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<number | null>(null);
  const [companyDetail, setCompanyDetail] = useState<CompanyDetailResponse | null>(null);
  const [showDetailModal, setShowDetailModal] = useState(false);

  useEffect(() => {
    loadCompanies();
  }, []);

  const loadCompanies = async () => {
    try {
      const data = await adminApi.listCompanies();
      setCompanies(data);
    } catch (error) {
      console.error("Failed to load companies:", error);
    } finally {
      setLoading(false);
    }
  };

  const loadCompanyDetail = async (companyId: number) => {
    try {
      const detail = await adminApi.getCompany(companyId);
      setCompanyDetail(detail);
      setShowDetailModal(true);
    } catch (error) {
      console.error("Failed to load company detail:", error);
    }
  };

  const handleDelete = async (companyId: number) => {
    try {
      await adminApi.deleteCompany(companyId);
      setCompanies(companies.filter((c) => c.id !== companyId));
      setDeleteConfirm(null);
    } catch (error) {
      console.error("Failed to delete company:", error);
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
          <h1 className="text-2xl font-bold text-gray-900">企業グループ管理</h1>
          <p className="mt-1 text-sm text-gray-500">
            企業グループの作成・編集・削除ができます
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

      {/* 企業グループテーブル */}
      <div className="bg-white shadow rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                企業グループ名
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                作成日
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                アクション
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {companies.length === 0 ? (
              <tr>
                <td
                  colSpan={3}
                  className="px-6 py-12 text-center text-sm text-gray-500"
                >
                  <Building2 className="mx-auto h-12 w-12 text-gray-400 mb-4" />
                  <p>企業グループがまだ登録されていません</p>
                  <button
                    onClick={() => setShowCreateModal(true)}
                    className="mt-4 text-indigo-600 hover:text-indigo-500"
                  >
                    最初の企業グループを作成する
                  </button>
                </td>
              </tr>
            ) : (
              companies.map((company) => (
                <tr key={company.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <div className="h-10 w-10 flex-shrink-0 bg-indigo-100 rounded-full flex items-center justify-center">
                        <Building2 className="h-5 w-5 text-indigo-600" />
                      </div>
                      <div className="ml-4">
                        <div className="text-sm font-medium text-gray-900">
                          {company.name}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {new Date(company.created_at).toLocaleDateString("ja-JP")}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <button
                      onClick={() => loadCompanyDetail(company.id)}
                      className="text-indigo-600 hover:text-indigo-900 mr-3"
                      title="詳細"
                    >
                      <Users className="h-4 w-4 inline" />
                    </button>
                    <button
                      onClick={() => setEditingCompany(company)}
                      className="text-indigo-600 hover:text-indigo-900 mr-3"
                      title="編集"
                    >
                      <Pencil className="h-4 w-4" />
                    </button>
                    {deleteConfirm === company.id ? (
                      <span className="inline-flex items-center">
                        <button
                          onClick={() => handleDelete(company.id)}
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
                        onClick={() => setDeleteConfirm(company.id)}
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
        <CreateCompanyModal
          onClose={() => setShowCreateModal(false)}
          onCreated={(company) => {
            setCompanies([...companies, company]);
            setShowCreateModal(false);
          }}
        />
      )}

      {/* 編集モーダル */}
      {editingCompany && (
        <EditCompanyModal
          company={editingCompany}
          onClose={() => setEditingCompany(null)}
          onUpdated={(updated) => {
            setCompanies(
              companies.map((c) => (c.id === updated.id ? updated : c))
            );
            setEditingCompany(null);
          }}
        />
      )}

      {/* 詳細モーダル */}
      {showDetailModal && companyDetail && (
        <CompanyDetailModal
          company={companyDetail}
          onClose={() => {
            setShowDetailModal(false);
            setCompanyDetail(null);
          }}
          onUpdated={() => {
            // 詳細を再読み込み
            loadCompanyDetail(companyDetail.id);
            // 一覧も再読み込み
            loadCompanies();
          }}
        />
      )}
    </div>
  );
}

// 作成モーダル
function CreateCompanyModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: (company: CompanyResponse) => void;
}) {
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const company = await adminApi.createCompany({ name });
      onCreated(company);
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
              企業グループを作成
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
                企業グループ名
              </label>
              <input
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="block w-full px-3 py-2 border border-gray-300 rounded-lg text-gray-900 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                placeholder="例: 株式会社サンプル"
              />
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
function EditCompanyModal({
  company,
  onClose,
  onUpdated,
}: {
  company: CompanyResponse;
  onClose: () => void;
  onUpdated: (company: CompanyResponse) => void;
}) {
  const [name, setName] = useState(company.name);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const updated = await adminApi.updateCompany(company.id, { name });
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
              企業グループを編集
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
                企業グループ名
              </label>
              <input
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="block w-full px-3 py-2 border border-gray-300 rounded-lg text-gray-900 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              />
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

// 詳細モーダル
function CompanyDetailModal({
  company,
  onClose,
  onUpdated,
}: {
  company: CompanyDetailResponse;
  onClose: () => void;
  onUpdated?: () => void;
}) {
  const [users, setUsers] = useState<Array<{ id: number; name: string; email: string; company_id?: number }>>([]);
  const [loadingUsers, setLoadingUsers] = useState(false);
  const [showAddUserModal, setShowAddUserModal] = useState(false);
  const [removingUserId, setRemovingUserId] = useState<number | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    loadAllUsers();
  }, []);

  const loadAllUsers = async () => {
    setLoadingUsers(true);
    try {
      const allUsers = await adminApi.listUsers();
      setUsers(allUsers);
    } catch (error) {
      console.error("Failed to load users:", error);
    } finally {
      setLoadingUsers(false);
    }
  };

  const handleAddUser = async (userId: number) => {
    try {
      await adminApi.updateUser(userId, { company_id: company.id });
      setShowAddUserModal(false);
      setError("");
      // 親コンポーネントに通知して再読み込み
      if (onUpdated) {
        onUpdated();
      }
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail);
      } else {
        setError("ユーザーの追加に失敗しました");
      }
    }
  };

  const handleRemoveUser = async (userId: number) => {
    setRemovingUserId(userId);
    try {
      await adminApi.updateUser(userId, { company_id: 0 }); // 0を送信するとNULLになる
      setError("");
      // 親コンポーネントに通知して再読み込み
      if (onUpdated) {
        onUpdated();
      }
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail);
      } else {
        setError("ユーザーの削除に失敗しました");
      }
    } finally {
      setRemovingUserId(null);
    }
  };

  // この企業グループに所属していないユーザー
  const availableUsers = users.filter(
    (user) => !company.admins.some((admin) => admin.id === user.id)
  );

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen px-4">
        <div
          className="fixed inset-0 bg-gray-500 bg-opacity-75"
          onClick={onClose}
        ></div>
        <div className="relative bg-white rounded-lg shadow-xl max-w-3xl w-full p-6 max-h-[90vh] overflow-y-auto">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-medium text-gray-900">
              {company.name} - 詳細
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

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                企業グループ名
              </label>
              <p className="text-sm text-gray-900">{company.name}</p>
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="block text-sm font-medium text-gray-700">
                  所属管理者 ({company.admin_count}名)
                </label>
                {availableUsers.length > 0 && (
                  <button
                    onClick={() => setShowAddUserModal(true)}
                    className="text-sm text-indigo-600 hover:text-indigo-500 flex items-center"
                  >
                    <Plus className="h-4 w-4 mr-1" />
                    ユーザーを追加
                  </button>
                )}
              </div>
              {company.admins.length > 0 ? (
                <div className="bg-gray-50 rounded-lg p-4">
                  <ul className="space-y-2">
                    {company.admins.map((admin) => (
                      <li
                        key={admin.id}
                        className="flex items-center justify-between text-sm"
                      >
                        <div>
                          <span className="font-medium text-gray-900">
                            {admin.name}
                          </span>
                          <span className="text-gray-500 ml-2">
                            ({admin.email})
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span
                            className={`px-2 py-1 text-xs font-semibold rounded-full ${
                              admin.is_active
                                ? "bg-green-100 text-green-800"
                                : "bg-red-100 text-red-800"
                            }`}
                          >
                            {admin.is_active ? "アクティブ" : "非アクティブ"}
                          </span>
                          <button
                            onClick={() => handleRemoveUser(admin.id)}
                            disabled={removingUserId === admin.id}
                            className="text-red-600 hover:text-red-900 disabled:opacity-50"
                            title="このグループから削除"
                          >
                            <X className="h-4 w-4" />
                          </button>
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : (
                <div className="bg-gray-50 rounded-lg p-4 text-sm text-gray-500 text-center">
                  所属している管理者がいません
                </div>
              )}
            </div>

            <div className="flex justify-end mt-6">
              <button
                onClick={onClose}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                閉じる
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* ユーザー追加モーダル */}
      {showAddUserModal && (
        <AddUserToCompanyModal
          company={company}
          availableUsers={availableUsers}
          onAdd={handleAddUser}
          onClose={() => {
            setShowAddUserModal(false);
            setError("");
          }}
        />
      )}
    </div>
  );
}

// ユーザー追加モーダル
function AddUserToCompanyModal({
  company,
  availableUsers,
  onAdd,
  onClose,
}: {
  company: CompanyDetailResponse;
  availableUsers: Array<{ id: number; name: string; email: string }>;
  onAdd: (userId: number) => Promise<void>;
  onClose: () => void;
}) {
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedUserId) {
      setError("ユーザーを選択してください");
      return;
    }

    setLoading(true);
    setError("");
    try {
      await onAdd(selectedUserId);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail);
      } else {
        setError("ユーザーの追加に失敗しました");
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
              {company.name} にユーザーを追加
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

          {availableUsers.length === 0 ? (
            <div className="text-sm text-gray-500 text-center py-4">
              追加できるユーザーがいません
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  ユーザーを選択
                </label>
                <select
                  value={selectedUserId || ""}
                  onChange={(e) => setSelectedUserId(parseInt(e.target.value) || null)}
                  className="block w-full px-3 py-2 border border-gray-300 rounded-lg text-gray-900 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  required
                >
                  <option value="">選択してください</option>
                  {availableUsers.map((user) => (
                    <option key={user.id} value={user.id}>
                      {user.name} ({user.email})
                    </option>
                  ))}
                </select>
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
                  disabled={loading || !selectedUserId}
                  className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 disabled:opacity-50"
                >
                  {loading ? "追加中..." : "追加"}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
