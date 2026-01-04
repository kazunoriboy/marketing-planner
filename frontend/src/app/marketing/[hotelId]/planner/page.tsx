"use client";

import { useEffect, useState, useRef } from "react";
import { Lightbulb, FileText, Loader2, Trash2, CheckCircle, Clock, Plus, Users, DollarSign, Gift, Target, Globe, Pencil, X, Send, MessageSquare, BookOpen, ChevronUp, Sparkles, ListChecks, User, AlertCircle, Info } from "lucide-react";
import { useHotel } from "@/lib/hotel-context";
import { marketingApi, MarketingPlan, AnalysisSession, OperationManual, OperationChatMessage, ManualContent, Persona } from "@/lib/api";

// セクションの型
type EditableSection = "concept" | "target_audience" | "price_range" | "benefits";

// 型定義
interface TargetAudience {
  age_range?: string;
  demographics?: string;
  psychographics?: string;
  needs?: string[];
}

interface PriceRange {
  min?: number;
  max?: number;
  recommended?: number;
  rationale?: string;
}

interface Benefits {
  main_benefits?: string[];
  unique_value?: string;
  amenities?: string[];
}

interface Strategy3C {
  customer?: string;
  competitor?: string;
  company?: string;
}

interface StrategyPEST {
  political?: string;
  economic?: string;
  social?: string;
  technological?: string;
}

// 価格をフォーマット
function formatPrice(price: number): string {
  return `¥${price.toLocaleString("ja-JP")}`;
}

export default function PlannerPage() {
  const { hotel, hotelId } = useHotel();
  const [session, setSession] = useState<AnalysisSession | null>(null);
  const [plans, setPlans] = useState<MarketingPlan[]>([]);
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [numPlans, setNumPlans] = useState(3);
  const [selectedPlan, setSelectedPlan] = useState<MarketingPlan | null>(null);
  const [selectedPersonaIndex, setSelectedPersonaIndex] = useState<number | null>(null);
  
  // セクション編集用のstate
  const [editingSection, setEditingSection] = useState<EditableSection | null>(null);
  const [editInstruction, setEditInstruction] = useState("");
  const [editingLoading, setEditingLoading] = useState(false);
  
  // オペレーション関連のstate
  const [operationManual, setOperationManual] = useState<OperationManual | null>(null);
  const [chatMessages, setChatMessages] = useState<OperationChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [showOperationChat, setShowOperationChat] = useState(false);
  const [generatingManual, setGeneratingManual] = useState(false);
  const [showManual, setShowManual] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    async function loadData() {
      try {
        const [sessionData, plansData, personasData] = await Promise.all([
          marketingApi.getAnalysisSession(hotelId),
          marketingApi.listPlans(hotelId),
          marketingApi.getPersonas(hotelId).catch(() => null),
        ]);
        setSession(sessionData);
        setPlans(plansData);
        if (personasData?.personas) {
          setPersonas(personasData.personas);
        }
      } catch (error) {
        console.error("Failed to load data:", error);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [hotelId]);

  const handleGeneratePlans = async () => {
    setGenerating(true);
    try {
      // ペルソナが選択されている場合は、そのペルソナに対してプランを生成
      const newPlans = await marketingApi.generatePlans(
        hotelId, 
        numPlans, 
        selectedPersonaIndex ?? undefined
      );
      setPlans((prev) => [...newPlans, ...prev]);
    } catch (error) {
      console.error("Plan generation failed:", error);
    } finally {
      setGenerating(false);
    }
  };

  const handleUpdateStatus = async (planId: number, status: "draft" | "approved") => {
    try {
      const updated = await marketingApi.updatePlanStatus(hotelId, planId, status);
      setPlans((prev) => prev.map((p) => (p.id === planId ? updated : p)));
      if (selectedPlan?.id === planId) {
        setSelectedPlan(updated);
      }
    } catch (error) {
      console.error("Status update failed:", error);
    }
  };

  const handleDeletePlan = async (planId: number) => {
    if (!confirm("このプランを削除しますか？")) return;
    try {
      await marketingApi.deletePlan(hotelId, planId);
      setPlans((prev) => prev.filter((p) => p.id !== planId));
      if (selectedPlan?.id === planId) {
        setSelectedPlan(null);
      }
    } catch (error) {
      console.error("Delete failed:", error);
    }
  };

  const handleStartEdit = (section: EditableSection) => {
    setEditingSection(section);
    setEditInstruction("");
  };

  const handleCancelEdit = () => {
    setEditingSection(null);
    setEditInstruction("");
  };

  const handleSubmitEdit = async () => {
    if (!selectedPlan || !editingSection || !editInstruction.trim()) return;
    
    setEditingLoading(true);
    try {
      const updated = await marketingApi.editPlanSection(
        hotelId,
        selectedPlan.id,
        editingSection,
        editInstruction
      );
      setPlans((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
      setSelectedPlan(updated);
      setEditingSection(null);
      setEditInstruction("");
    } catch (error) {
      console.error("Section edit failed:", error);
      alert("修正に失敗しました。もう一度お試しください。");
    } finally {
      setEditingLoading(false);
    }
  };

  // オペレーションチャットを開始
  const handleStartOperationChat = async () => {
    if (!selectedPlan) return;
    
    setChatLoading(true);
    try {
      const manual = await marketingApi.startOperationChat(hotelId, selectedPlan.id);
      setOperationManual(manual);
      setChatMessages(manual.chat_messages || []);
      setShowOperationChat(true);
      setShowManual(manual.status === "completed");
    } catch (error) {
      console.error("Failed to start operation chat:", error);
      alert("オペレーションチャットの開始に失敗しました。");
    } finally {
      setChatLoading(false);
    }
  };

  // チャットメッセージを送信
  const handleSendMessage = async () => {
    if (!operationManual || !chatInput.trim() || chatLoading) return;
    
    const userMessage = chatInput.trim();
    setChatInput("");
    setChatLoading(true);
    
    // ユーザーメッセージを即時表示
    const tempUserMsg: OperationChatMessage = {
      id: Date.now(),
      operation_manual_id: operationManual.id,
      role: "user",
      content: userMessage,
      msg_metadata: {},
      created_at: new Date().toISOString(),
    };
    setChatMessages((prev) => [...prev, tempUserMsg]);
    
    try {
      const aiResponse = await marketingApi.sendOperationMessage(
        hotelId,
        operationManual.id,
        userMessage
      );
      setChatMessages((prev) => [...prev.slice(0, -1), { ...tempUserMsg }, aiResponse]);
      
      // スクロール
      setTimeout(() => {
        chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
      }, 100);
    } catch (error) {
      console.error("Failed to send message:", error);
      setChatMessages((prev) => prev.slice(0, -1));
      setChatInput(userMessage);
      alert("メッセージの送信に失敗しました。");
    } finally {
      setChatLoading(false);
    }
  };

  // マニュアルを生成
  const handleGenerateManual = async () => {
    if (!operationManual) return;
    
    setGeneratingManual(true);
    try {
      const updated = await marketingApi.generateOperationManual(hotelId, operationManual.id);
      setOperationManual(updated);
      setShowManual(true);
    } catch (error) {
      console.error("Failed to generate manual:", error);
      alert("マニュアルの生成に失敗しました。");
    } finally {
      setGeneratingManual(false);
    }
  };

  // オペレーションチャットを閉じる
  const handleCloseOperationChat = () => {
    setShowOperationChat(false);
  };

  // 最後のAIメッセージがマニュアル生成準備完了かチェック
  const isReadyForManual = chatMessages.length > 0 && 
    chatMessages[chatMessages.length - 1].role === "assistant" &&
    chatMessages[chatMessages.length - 1].msg_metadata?.is_ready_for_manual === true;

  const hasAnalysisData = session?.session_id !== null && (
    (session?.csv_statistics && Object.keys(session.csv_statistics).length > 0) ||
    (session?.competitors_list && Object.keys(session.competitors_list).length > 0)
  );
  
  const hasPersonas = personas.length > 0;

  return (
    <section className="animate-fadeIn">
      <h2 className="text-3xl font-bold text-white mb-2">プランを立てる</h2>
      <p className="text-slate-400 mb-8">
        {hotel.name}のマーケティングプランをAIで生成します
      </p>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-purple-500"></div>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* 左側：プラン生成＆一覧 */}
          <div className="lg:col-span-1 space-y-6">
            {/* プラン生成セクション */}
            <div className="glass-card p-6">
              <div className="flex items-center gap-3 mb-4">
                <Lightbulb className="w-6 h-6 text-yellow-400" />
                <h3 className="text-xl font-bold text-white">プラン生成</h3>
              </div>

              {!hasAnalysisData ? (
                <p className="text-slate-400 text-sm">
                  プランを生成するには、先に「顧客を知る」または「市場を知る」で分析を実行してください。
                </p>
              ) : (
                <>
                  {/* ペルソナ選択UI */}
                  {hasPersonas ? (
                    <div className="mb-4">
                      <div className="flex items-center gap-2 mb-3">
                        <Users className="w-5 h-5 text-purple-400" />
                        <span className="text-purple-300 font-semibold text-sm">ペルソナを選択</span>
                      </div>
                      <p className="text-slate-400 text-xs mb-3">
                        ターゲットとなるペルソナを選んでください。選択したペルソナに刺さる複数のプランを生成します。
                      </p>
                      <div className="space-y-2">
                        {personas.map((persona, idx) => (
                          <button 
                            key={idx}
                            onClick={() => setSelectedPersonaIndex(selectedPersonaIndex === idx ? null : idx)}
                            className={`w-full text-left p-3 rounded-lg border transition-all ${
                              selectedPersonaIndex === idx
                                ? "bg-gradient-to-r from-purple-500/20 to-cyan-500/20 border-purple-500/50"
                                : "bg-white/5 border-white/10 hover:bg-white/10"
                            }`}
                          >
                            <div className="flex items-center gap-3">
                              <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                                selectedPersonaIndex === idx
                                  ? "bg-purple-500/30"
                                  : "bg-white/10"
                              }`}>
                                <User className={`w-4 h-4 ${
                                  selectedPersonaIndex === idx
                                    ? "text-purple-300"
                                    : "text-slate-400"
                                }`} />
                              </div>
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2">
                                  <span className={`font-medium ${
                                    selectedPersonaIndex === idx
                                      ? "text-white"
                                      : "text-slate-200"
                                  }`}>{persona.name}</span>
                                  <span className="text-xs text-slate-500">{persona.age_range}</span>
                                </div>
                                <p className="text-xs text-slate-400 truncate mt-0.5">
                                  {persona.travel_purpose}
                                </p>
                              </div>
                              {selectedPersonaIndex === idx && (
                                <CheckCircle className="w-5 h-5 text-purple-400 flex-shrink-0" />
                              )}
                            </div>
                          </button>
                        ))}
                      </div>
                      
                      {selectedPersonaIndex !== null && (
                        <div className="mt-3 p-3 bg-purple-500/10 rounded-lg border border-purple-500/20">
                          <p className="text-xs text-purple-300 flex items-center gap-1">
                            <Info className="w-3 h-3" />
                            「{personas[selectedPersonaIndex].name}」に刺さる{numPlans}つの異なる切り口のプランを生成します
                          </p>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="mb-4 p-3 bg-yellow-500/10 rounded-lg border border-yellow-500/20">
                      <div className="flex items-start gap-2">
                        <AlertCircle className="w-4 h-4 text-yellow-400 mt-0.5 flex-shrink-0" />
                        <div>
                          <p className="text-yellow-300 text-sm font-medium">ペルソナが未設定です</p>
                          <p className="text-slate-400 text-xs mt-1">
                            「顧客を知る」でペルソナを生成すると、各ペルソナに最適化されたプランを提案できます
                          </p>
                        </div>
                      </div>
                    </div>
                  )}
                  
                  {/* 生成数選択 */}
                  <div className="flex items-center gap-4 mb-4">
                    <label className="text-slate-300 text-sm">生成数：</label>
                    <select
                      value={numPlans}
                      onChange={(e) => setNumPlans(Number(e.target.value))}
                      className="bg-white/5 border border-white/10 rounded-lg p-2 text-white text-sm"
                    >
                      <option value={1}>1件</option>
                      <option value={3}>3件</option>
                      <option value={5}>5件</option>
                    </select>
                  </div>

                  <button
                    onClick={handleGeneratePlans}
                    disabled={generating || (hasPersonas && selectedPersonaIndex === null)}
                    className="w-full bg-gradient-to-r from-purple-500 to-cyan-500 text-white py-3 rounded-lg hover:from-purple-600 hover:to-cyan-600 transition-all font-semibold disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                  >
                    {generating ? (
                      <>
                        <Loader2 className="w-5 h-5 animate-spin" />
                        生成中...
                      </>
                    ) : hasPersonas ? (
                      selectedPersonaIndex !== null ? (
                        <>
                          <Sparkles className="w-5 h-5" />
                          {numPlans}件のプランを生成
                        </>
                      ) : (
                        <>
                          <User className="w-5 h-5" />
                          ペルソナを選択してください
                        </>
                      )
                    ) : (
                      <>
                        <Plus className="w-5 h-5" />
                        プランを生成
                      </>
                    )}
                  </button>
                </>
              )}
            </div>

            {/* プラン一覧 */}
            <div className="glass-card p-6">
              <div className="flex items-center gap-3 mb-4">
                <FileText className="w-6 h-6 text-blue-400" />
                <h3 className="text-xl font-bold text-white">プラン一覧</h3>
              </div>

              {plans.length === 0 ? (
                <p className="text-slate-400 text-sm">プランがありません</p>
              ) : (
                <div className="space-y-2 max-h-96 overflow-y-auto">
                  {plans.map((plan) => (
                    <div
                      key={plan.id}
                      onClick={() => setSelectedPlan(plan)}
                      className={`p-3 rounded-lg cursor-pointer transition-colors ${
                        selectedPlan?.id === plan.id
                          ? "bg-white/20 border border-white/30"
                          : "bg-white/5 border border-white/10 hover:bg-white/10"
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-medium text-white text-sm truncate">
                          {plan.plan_name}
                        </span>
                        {plan.status === "approved" ? (
                          <CheckCircle className="w-4 h-4 text-green-400 flex-shrink-0" />
                        ) : (
                          <Clock className="w-4 h-4 text-yellow-400 flex-shrink-0" />
                        )}
                      </div>
                      <p className="text-xs text-slate-400 line-clamp-1">
                        {plan.concept}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* 右側：プラン詳細 */}
          <div className="lg:col-span-2">
            {selectedPlan ? (
              <div className="glass-card p-8">
                <div className="flex items-start justify-between mb-6">
                  <div>
                    <h3 className="text-2xl font-bold text-white mb-2">
                      {selectedPlan.plan_name}
                    </h3>
                    <span
                      className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm ${
                        selectedPlan.status === "approved"
                          ? "bg-green-500/20 text-green-400"
                          : "bg-yellow-500/20 text-yellow-400"
                      }`}
                    >
                      {selectedPlan.status === "approved" ? (
                        <>
                          <CheckCircle className="w-4 h-4" />
                          承認済み
                        </>
                      ) : (
                        <>
                          <Clock className="w-4 h-4" />
                          ドラフト
                        </>
                      )}
                    </span>
                  </div>
                  <div className="flex gap-2">
                    {selectedPlan.status === "draft" ? (
                      <button
                        onClick={() => handleUpdateStatus(selectedPlan.id, "approved")}
                        className="px-4 py-2 bg-green-500/20 text-green-400 rounded-lg hover:bg-green-500/30 transition-colors text-sm"
                      >
                        承認
                      </button>
                    ) : (
                      <button
                        onClick={() => handleUpdateStatus(selectedPlan.id, "draft")}
                        className="px-4 py-2 bg-yellow-500/20 text-yellow-400 rounded-lg hover:bg-yellow-500/30 transition-colors text-sm"
                      >
                        ドラフトに戻す
                      </button>
                    )}
                    <button
                      onClick={() => handleDeletePlan(selectedPlan.id)}
                      className="px-4 py-2 bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30 transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {/* コンセプト */}
                <div className="mb-6">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="text-lg font-semibold text-white">コンセプト</h4>
                    {editingSection !== "concept" && (
                      <button
                        onClick={() => handleStartEdit("concept")}
                        className="flex items-center gap-1 px-3 py-1 text-sm text-slate-400 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
                      >
                        <Pencil className="w-4 h-4" />
                        修正
                      </button>
                    )}
                  </div>
                  <p className="text-slate-300 p-4 bg-white/5 rounded-lg">
                    {selectedPlan.concept}
                  </p>
                  {editingSection === "concept" && (
                    <div className="mt-3 p-4 bg-white/5 rounded-lg border border-purple-500/30">
                      <p className="text-sm text-slate-400 mb-2">修正指示を入力してください：</p>
                      <textarea
                        value={editInstruction}
                        onChange={(e) => setEditInstruction(e.target.value)}
                        placeholder="例: 地元の名士との交流を削除して、地元の食材を使った料理体験に焦点を当てて"
                        className="w-full bg-white/5 border border-white/10 rounded-lg p-3 text-white placeholder-slate-500 focus:outline-none focus:border-purple-500 resize-none"
                        rows={3}
                        disabled={editingLoading}
                      />
                      <div className="flex justify-end gap-2 mt-3">
                        <button
                          onClick={handleCancelEdit}
                          disabled={editingLoading}
                          className="flex items-center gap-1 px-4 py-2 text-sm text-slate-400 hover:text-white hover:bg-white/10 rounded-lg transition-colors disabled:opacity-50"
                        >
                          <X className="w-4 h-4" />
                          キャンセル
                        </button>
                        <button
                          onClick={handleSubmitEdit}
                          disabled={editingLoading || !editInstruction.trim()}
                          className="flex items-center gap-1 px-4 py-2 text-sm text-white bg-gradient-to-r from-purple-500 to-cyan-500 rounded-lg hover:from-purple-600 hover:to-cyan-600 transition-colors disabled:opacity-50"
                        >
                          {editingLoading ? (
                            <>
                              <Loader2 className="w-4 h-4 animate-spin" />
                              修正中...
                            </>
                          ) : (
                            <>
                              <Send className="w-4 h-4" />
                              修正を実行
                            </>
                          )}
                        </button>
                      </div>
                    </div>
                  )}
                </div>

                {/* ターゲット顧客 */}
                {selectedPlan.target_audience && Object.keys(selectedPlan.target_audience).length > 0 && (
                  <div className="mb-6">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <Users className="w-5 h-5 text-blue-400" />
                        <h4 className="text-lg font-semibold text-white">ターゲット顧客</h4>
                      </div>
                      {editingSection !== "target_audience" && (
                        <button
                          onClick={() => handleStartEdit("target_audience")}
                          className="flex items-center gap-1 px-3 py-1 text-sm text-slate-400 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
                        >
                          <Pencil className="w-4 h-4" />
                          修正
                        </button>
                      )}
                    </div>
                    <div className="p-4 bg-white/5 rounded-lg space-y-3">
                      {(() => {
                        const target = selectedPlan.target_audience as TargetAudience;
                        return (
                          <>
                            {target.age_range && (
                              <div className="flex items-start gap-3">
                                <span className="text-slate-400 text-sm min-w-[100px]">年齢層</span>
                                <span className="text-white">{target.age_range}</span>
                              </div>
                            )}
                            {target.demographics && (
                              <div className="flex items-start gap-3">
                                <span className="text-slate-400 text-sm min-w-[100px]">属性</span>
                                <span className="text-white">{target.demographics}</span>
                              </div>
                            )}
                            {target.psychographics && (
                              <div className="flex items-start gap-3">
                                <span className="text-slate-400 text-sm min-w-[100px]">志向</span>
                                <span className="text-white">{target.psychographics}</span>
                              </div>
                            )}
                            {target.needs && target.needs.length > 0 && (
                              <div className="flex items-start gap-3">
                                <span className="text-slate-400 text-sm min-w-[100px]">ニーズ</span>
                                <div className="flex flex-wrap gap-2">
                                  {target.needs.map((need, idx) => (
                                    <span key={idx} className="px-2 py-1 bg-blue-500/20 text-blue-300 rounded-full text-sm">
                                      {need}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}
                          </>
                        );
                      })()}
                    </div>
                    {editingSection === "target_audience" && (
                      <div className="mt-3 p-4 bg-white/5 rounded-lg border border-blue-500/30">
                        <p className="text-sm text-slate-400 mb-2">修正指示を入力してください：</p>
                        <textarea
                          value={editInstruction}
                          onChange={(e) => setEditInstruction(e.target.value)}
                          placeholder="例: ターゲット年齢層を40-60代に変更して、富裕層向けにして"
                          className="w-full bg-white/5 border border-white/10 rounded-lg p-3 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 resize-none"
                          rows={3}
                          disabled={editingLoading}
                        />
                        <div className="flex justify-end gap-2 mt-3">
                          <button
                            onClick={handleCancelEdit}
                            disabled={editingLoading}
                            className="flex items-center gap-1 px-4 py-2 text-sm text-slate-400 hover:text-white hover:bg-white/10 rounded-lg transition-colors disabled:opacity-50"
                          >
                            <X className="w-4 h-4" />
                            キャンセル
                          </button>
                          <button
                            onClick={handleSubmitEdit}
                            disabled={editingLoading || !editInstruction.trim()}
                            className="flex items-center gap-1 px-4 py-2 text-sm text-white bg-gradient-to-r from-purple-500 to-cyan-500 rounded-lg hover:from-purple-600 hover:to-cyan-600 transition-colors disabled:opacity-50"
                          >
                            {editingLoading ? (
                              <>
                                <Loader2 className="w-4 h-4 animate-spin" />
                                修正中...
                              </>
                            ) : (
                              <>
                                <Send className="w-4 h-4" />
                                修正を実行
                              </>
                            )}
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* 価格帯 */}
                {selectedPlan.price_range && Object.keys(selectedPlan.price_range).length > 0 && (
                  <div className="mb-6">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <DollarSign className="w-5 h-5 text-green-400" />
                        <h4 className="text-lg font-semibold text-white">価格帯</h4>
                      </div>
                      {editingSection !== "price_range" && (
                        <button
                          onClick={() => handleStartEdit("price_range")}
                          className="flex items-center gap-1 px-3 py-1 text-sm text-slate-400 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
                        >
                          <Pencil className="w-4 h-4" />
                          修正
                        </button>
                      )}
                    </div>
                    <div className="p-4 bg-white/5 rounded-lg">
                      {(() => {
                        const price = selectedPlan.price_range as PriceRange;
                        return (
                          <>
                            <div className="grid grid-cols-3 gap-4 mb-4">
                              {price.min !== undefined && (
                                <div className="text-center p-3 bg-white/5 rounded-lg">
                                  <p className="text-slate-400 text-xs mb-1">最低価格</p>
                                  <p className="text-white font-semibold">{formatPrice(price.min)}</p>
                                </div>
                              )}
                              {price.recommended !== undefined && (
                                <div className="text-center p-3 bg-green-500/20 rounded-lg border border-green-500/30">
                                  <p className="text-green-400 text-xs mb-1">推奨価格</p>
                                  <p className="text-green-300 font-bold text-lg">{formatPrice(price.recommended)}</p>
                                </div>
                              )}
                              {price.max !== undefined && (
                                <div className="text-center p-3 bg-white/5 rounded-lg">
                                  <p className="text-slate-400 text-xs mb-1">最高価格</p>
                                  <p className="text-white font-semibold">{formatPrice(price.max)}</p>
                                </div>
                              )}
                            </div>
                            {price.rationale && (
                              <div className="p-3 bg-white/5 rounded-lg">
                                <p className="text-slate-400 text-xs mb-1">価格設定の根拠</p>
                                <p className="text-slate-300 text-sm">{price.rationale}</p>
                              </div>
                            )}
                          </>
                        );
                      })()}
                    </div>
                    {editingSection === "price_range" && (
                      <div className="mt-3 p-4 bg-white/5 rounded-lg border border-green-500/30">
                        <p className="text-sm text-slate-400 mb-2">修正指示を入力してください：</p>
                        <textarea
                          value={editInstruction}
                          onChange={(e) => setEditInstruction(e.target.value)}
                          placeholder="例: 推奨価格を15000円に下げて、繁忙期と閑散期で価格差をつけて"
                          className="w-full bg-white/5 border border-white/10 rounded-lg p-3 text-white placeholder-slate-500 focus:outline-none focus:border-green-500 resize-none"
                          rows={3}
                          disabled={editingLoading}
                        />
                        <div className="flex justify-end gap-2 mt-3">
                          <button
                            onClick={handleCancelEdit}
                            disabled={editingLoading}
                            className="flex items-center gap-1 px-4 py-2 text-sm text-slate-400 hover:text-white hover:bg-white/10 rounded-lg transition-colors disabled:opacity-50"
                          >
                            <X className="w-4 h-4" />
                            キャンセル
                          </button>
                          <button
                            onClick={handleSubmitEdit}
                            disabled={editingLoading || !editInstruction.trim()}
                            className="flex items-center gap-1 px-4 py-2 text-sm text-white bg-gradient-to-r from-purple-500 to-cyan-500 rounded-lg hover:from-purple-600 hover:to-cyan-600 transition-colors disabled:opacity-50"
                          >
                            {editingLoading ? (
                              <>
                                <Loader2 className="w-4 h-4 animate-spin" />
                                修正中...
                              </>
                            ) : (
                              <>
                                <Send className="w-4 h-4" />
                                修正を実行
                              </>
                            )}
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* 特典 */}
                {selectedPlan.benefits && Object.keys(selectedPlan.benefits).length > 0 && (
                  <div className="mb-6">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <Gift className="w-5 h-5 text-pink-400" />
                        <h4 className="text-lg font-semibold text-white">特典・特徴</h4>
                      </div>
                      {editingSection !== "benefits" && (
                        <button
                          onClick={() => handleStartEdit("benefits")}
                          className="flex items-center gap-1 px-3 py-1 text-sm text-slate-400 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
                        >
                          <Pencil className="w-4 h-4" />
                          修正
                        </button>
                      )}
                    </div>
                    <div className="p-4 bg-white/5 rounded-lg space-y-4">
                      {(() => {
                        const benefits = selectedPlan.benefits as Benefits;
                        return (
                          <>
                            {benefits.unique_value && (
                              <div className="p-3 bg-gradient-to-r from-purple-500/20 to-pink-500/20 rounded-lg border border-purple-500/30">
                                <p className="text-purple-300 text-xs mb-1">独自の価値提案</p>
                                <p className="text-white font-medium">{benefits.unique_value}</p>
                              </div>
                            )}
                            {benefits.main_benefits && benefits.main_benefits.length > 0 && (
                              <div>
                                <p className="text-slate-400 text-xs mb-2">主な特典</p>
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                                  {benefits.main_benefits.map((benefit, idx) => (
                                    <div key={idx} className="flex items-center gap-2 p-2 bg-white/5 rounded-lg">
                                      <CheckCircle className="w-4 h-4 text-green-400 flex-shrink-0" />
                                      <span className="text-slate-300 text-sm">{benefit}</span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                            {benefits.amenities && benefits.amenities.length > 0 && (
                              <div>
                                <p className="text-slate-400 text-xs mb-2">アメニティ</p>
                                <div className="flex flex-wrap gap-2">
                                  {benefits.amenities.map((amenity, idx) => (
                                    <span key={idx} className="px-2 py-1 bg-pink-500/20 text-pink-300 rounded-full text-sm">
                                      {amenity}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}
                          </>
                        );
                      })()}
                    </div>
                    {editingSection === "benefits" && (
                      <div className="mt-3 p-4 bg-white/5 rounded-lg border border-pink-500/30">
                        <p className="text-sm text-slate-400 mb-2">修正指示を入力してください：</p>
                        <textarea
                          value={editInstruction}
                          onChange={(e) => setEditInstruction(e.target.value)}
                          placeholder="例: 朝食の特典を削除して、代わりに温泉入り放題と個室での夕食を追加して"
                          className="w-full bg-white/5 border border-white/10 rounded-lg p-3 text-white placeholder-slate-500 focus:outline-none focus:border-pink-500 resize-none"
                          rows={3}
                          disabled={editingLoading}
                        />
                        <div className="flex justify-end gap-2 mt-3">
                          <button
                            onClick={handleCancelEdit}
                            disabled={editingLoading}
                            className="flex items-center gap-1 px-4 py-2 text-sm text-slate-400 hover:text-white hover:bg-white/10 rounded-lg transition-colors disabled:opacity-50"
                          >
                            <X className="w-4 h-4" />
                            キャンセル
                          </button>
                          <button
                            onClick={handleSubmitEdit}
                            disabled={editingLoading || !editInstruction.trim()}
                            className="flex items-center gap-1 px-4 py-2 text-sm text-white bg-gradient-to-r from-purple-500 to-cyan-500 rounded-lg hover:from-purple-600 hover:to-cyan-600 transition-colors disabled:opacity-50"
                          >
                            {editingLoading ? (
                              <>
                                <Loader2 className="w-4 h-4 animate-spin" />
                                修正中...
                              </>
                            ) : (
                              <>
                                <Send className="w-4 h-4" />
                                修正を実行
                              </>
                            )}
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* 3C分析 */}
                {selectedPlan.strategy_3c && Object.keys(selectedPlan.strategy_3c).length > 0 && (
                  <div className="mb-6">
                    <div className="flex items-center gap-2 mb-3">
                      <Target className="w-5 h-5 text-orange-400" />
                      <h4 className="text-lg font-semibold text-white">3C分析</h4>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      {(() => {
                        const strategy = selectedPlan.strategy_3c as Strategy3C;
                        return (
                          <>
                            {strategy.customer && (
                              <div className="p-4 bg-white/5 rounded-lg border-l-4 border-blue-500">
                                <p className="text-blue-400 text-xs font-semibold mb-2">Customer（顧客）</p>
                                <p className="text-slate-300 text-sm">{strategy.customer}</p>
                              </div>
                            )}
                            {strategy.competitor && (
                              <div className="p-4 bg-white/5 rounded-lg border-l-4 border-red-500">
                                <p className="text-red-400 text-xs font-semibold mb-2">Competitor（競合）</p>
                                <p className="text-slate-300 text-sm">{strategy.competitor}</p>
                              </div>
                            )}
                            {strategy.company && (
                              <div className="p-4 bg-white/5 rounded-lg border-l-4 border-green-500">
                                <p className="text-green-400 text-xs font-semibold mb-2">Company（自社）</p>
                                <p className="text-slate-300 text-sm">{strategy.company}</p>
                              </div>
                            )}
                          </>
                        );
                      })()}
                    </div>
                  </div>
                )}

                {/* PEST分析 */}
                {selectedPlan.strategy_pest && Object.keys(selectedPlan.strategy_pest).length > 0 && (
                  <div className="mb-6">
                    <div className="flex items-center gap-2 mb-3">
                      <Globe className="w-5 h-5 text-cyan-400" />
                      <h4 className="text-lg font-semibold text-white">PEST分析</h4>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {(() => {
                        const pest = selectedPlan.strategy_pest as StrategyPEST;
                        return (
                          <>
                            {pest.political && (
                              <div className="p-4 bg-white/5 rounded-lg">
                                <p className="text-purple-400 text-xs font-semibold mb-2">Political（政治的要因）</p>
                                <p className="text-slate-300 text-sm">{pest.political}</p>
                              </div>
                            )}
                            {pest.economic && (
                              <div className="p-4 bg-white/5 rounded-lg">
                                <p className="text-green-400 text-xs font-semibold mb-2">Economic（経済的要因）</p>
                                <p className="text-slate-300 text-sm">{pest.economic}</p>
                              </div>
                            )}
                            {pest.social && (
                              <div className="p-4 bg-white/5 rounded-lg">
                                <p className="text-blue-400 text-xs font-semibold mb-2">Social（社会的要因）</p>
                                <p className="text-slate-300 text-sm">{pest.social}</p>
                              </div>
                            )}
                            {pest.technological && (
                              <div className="p-4 bg-white/5 rounded-lg">
                                <p className="text-cyan-400 text-xs font-semibold mb-2">Technological（技術的要因）</p>
                                <p className="text-slate-300 text-sm">{pest.technological}</p>
                              </div>
                            )}
                          </>
                        );
                      })()}
                    </div>
                  </div>
                )}

                {/* オペレーションセクション（承認済みプランのみ） */}
                {selectedPlan.status === "approved" && (
                  <div className="mt-8 pt-6 border-t border-white/10">
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-2">
                        <ListChecks className="w-5 h-5 text-emerald-400" />
                        <h4 className="text-lg font-semibold text-white">オペレーションマニュアル</h4>
                      </div>
                      {!showOperationChat && (
                        <button
                          onClick={handleStartOperationChat}
                          disabled={chatLoading}
                          className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-emerald-500 to-teal-500 text-white rounded-lg hover:from-emerald-600 hover:to-teal-600 transition-all font-medium disabled:opacity-50"
                        >
                          {chatLoading ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <MessageSquare className="w-4 h-4" />
                          )}
                          {operationManual ? "チャットを再開" : "オペレーションを作成"}
                        </button>
                      )}
                    </div>

                    <p className="text-slate-400 text-sm mb-4">
                      このプランを実行するための具体的なマニュアルを、AIとの対話を通じて作成できます。
                      施設の状況に合わせた実践的な手順書を生成します。
                    </p>

                    {/* チャットUI */}
                    {showOperationChat && (
                      <div className="bg-white/5 rounded-xl border border-white/10 overflow-hidden">
                        {/* チャットヘッダー */}
                        <div className="flex items-center justify-between p-4 bg-white/5 border-b border-white/10">
                          <div className="flex items-center gap-2">
                            <MessageSquare className="w-5 h-5 text-emerald-400" />
                            <span className="font-medium text-white">オペレーション作成チャット</span>
                            {operationManual?.status === "completed" && (
                              <span className="px-2 py-0.5 bg-emerald-500/20 text-emerald-400 text-xs rounded-full">
                                完了
                              </span>
                            )}
                          </div>
                          <div className="flex items-center gap-2">
                            {operationManual?.status === "completed" && (
                              <button
                                onClick={() => setShowManual(!showManual)}
                                className="flex items-center gap-1 px-3 py-1.5 text-sm text-emerald-400 hover:bg-white/10 rounded-lg transition-colors"
                              >
                                <BookOpen className="w-4 h-4" />
                                {showManual ? "チャットを表示" : "マニュアルを表示"}
                              </button>
                            )}
                            <button
                              onClick={handleCloseOperationChat}
                              className="p-1.5 text-slate-400 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
                            >
                              <ChevronUp className="w-5 h-5" />
                            </button>
                          </div>
                        </div>

                        {/* マニュアル表示 */}
                        {showManual && operationManual?.manual_content && Object.keys(operationManual.manual_content).length > 0 ? (
                          <div className="p-6 max-h-[600px] overflow-y-auto">
                            {(() => {
                              const manual = operationManual.manual_content as ManualContent;
                              return (
                                <div className="space-y-6">
                                  {/* タイトルと概要 */}
                                  <div>
                                    <h3 className="text-xl font-bold text-white mb-2">{manual.title}</h3>
                                    <p className="text-slate-300">{manual.overview}</p>
                                  </div>

                                  {/* タイムラインと予算 */}
                                  {(manual.timeline || manual.budget_estimate) && (
                                    <div className="grid grid-cols-2 gap-4">
                                      {manual.timeline && (
                                        <div className="p-3 bg-white/5 rounded-lg">
                                          <p className="text-slate-400 text-xs mb-1">タイムライン</p>
                                          <p className="text-white text-sm">{manual.timeline}</p>
                                        </div>
                                      )}
                                      {manual.budget_estimate && (
                                        <div className="p-3 bg-white/5 rounded-lg">
                                          <p className="text-slate-400 text-xs mb-1">概算予算</p>
                                          <p className="text-white text-sm">{manual.budget_estimate}</p>
                                        </div>
                                      )}
                                    </div>
                                  )}

                                  {/* フェーズ */}
                                  {manual.phases?.map((phase, phaseIdx) => (
                                    <div key={phaseIdx} className="border border-white/10 rounded-lg overflow-hidden">
                                      <div className="p-4 bg-gradient-to-r from-emerald-500/20 to-teal-500/20 border-b border-white/10">
                                        <div className="flex items-center justify-between">
                                          <h4 className="font-semibold text-white">{phase.name}</h4>
                                          {phase.duration && (
                                            <span className="text-xs text-slate-400">
                                              期間: {phase.duration}
                                            </span>
                                          )}
                                        </div>
                                        {phase.description && (
                                          <p className="text-slate-300 text-sm mt-1">{phase.description}</p>
                                        )}
                                      </div>
                                      <div className="p-4 space-y-3">
                                        {phase.tasks?.map((task, taskIdx) => (
                                          <div key={taskIdx} className="p-3 bg-white/5 rounded-lg">
                                            <div className="flex items-start gap-3">
                                              <div className="flex items-center justify-center w-6 h-6 bg-emerald-500/20 text-emerald-400 rounded-full text-xs font-bold flex-shrink-0">
                                                {taskIdx + 1}
                                              </div>
                                              <div className="flex-1">
                                                <h5 className="font-medium text-white mb-1">{task.title}</h5>
                                                <p className="text-slate-300 text-sm whitespace-pre-wrap">{task.description}</p>
                                                <div className="flex flex-wrap gap-2 mt-2">
                                                  {task.estimated_time && (
                                                    <span className="px-2 py-0.5 bg-blue-500/20 text-blue-300 text-xs rounded-full">
                                                      ⏱ {task.estimated_time}
                                                    </span>
                                                  )}
                                                  {task.responsible && (
                                                    <span className="px-2 py-0.5 bg-purple-500/20 text-purple-300 text-xs rounded-full">
                                                      👤 {task.responsible}
                                                    </span>
                                                  )}
                                                  {task.tools?.map((tool, toolIdx) => (
                                                    <span key={toolIdx} className="px-2 py-0.5 bg-slate-500/20 text-slate-300 text-xs rounded-full">
                                                      🔧 {tool}
                                                    </span>
                                                  ))}
                                                </div>
                                                {task.tips && (
                                                  <div className="mt-2 p-2 bg-yellow-500/10 rounded text-yellow-200 text-xs">
                                                    💡 {task.tips}
                                                  </div>
                                                )}
                                              </div>
                                            </div>
                                          </div>
                                        ))}
                                      </div>
                                    </div>
                                  ))}

                                  {/* KPI */}
                                  {manual.success_metrics && manual.success_metrics.length > 0 && (
                                    <div className="p-4 bg-white/5 rounded-lg">
                                      <h4 className="font-semibold text-white mb-2">成功指標（KPI）</h4>
                                      <ul className="space-y-1">
                                        {manual.success_metrics.map((metric, idx) => (
                                          <li key={idx} className="flex items-center gap-2 text-slate-300 text-sm">
                                            <CheckCircle className="w-4 h-4 text-emerald-400" />
                                            {metric}
                                          </li>
                                        ))}
                                      </ul>
                                    </div>
                                  )}

                                  {/* 備考 */}
                                  {manual.notes && (
                                    <div className="p-4 bg-white/5 rounded-lg">
                                      <h4 className="font-semibold text-white mb-2">備考・注意点</h4>
                                      <p className="text-slate-300 text-sm whitespace-pre-wrap">{manual.notes}</p>
                                    </div>
                                  )}
                                </div>
                              );
                            })()}
                          </div>
                        ) : (
                          <>
                            {/* チャットメッセージ一覧 */}
                            <div className="h-80 overflow-y-auto p-4 space-y-4">
                              {chatMessages.map((msg) => (
                                <div
                                  key={msg.id}
                                  className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                                >
                                  <div
                                    className={`max-w-[80%] p-3 rounded-lg ${
                                      msg.role === "user"
                                        ? "bg-gradient-to-r from-purple-500/30 to-cyan-500/30 text-white"
                                        : "bg-white/10 text-slate-200"
                                    }`}
                                  >
                                    <p className="whitespace-pre-wrap text-sm">{msg.content}</p>
                                  </div>
                                </div>
                              ))}
                              {chatLoading && (
                                <div className="flex justify-start">
                                  <div className="bg-white/10 p-3 rounded-lg">
                                    <Loader2 className="w-5 h-5 animate-spin text-slate-400" />
                                  </div>
                                </div>
                              )}
                              <div ref={chatEndRef} />
                            </div>

                            {/* マニュアル生成ボタン */}
                            {(isReadyForManual || chatMessages.length >= 4) && operationManual?.status !== "completed" && (
                              <div className="px-4 py-3 bg-emerald-500/10 border-t border-emerald-500/20">
                                <div className="flex items-center justify-between">
                                  <p className="text-emerald-300 text-sm">
                                    {isReadyForManual 
                                      ? "✨ マニュアルを生成する準備ができました！"
                                      : "💡 ヒント: まだ質問に答えることで、より良いマニュアルが生成されます"}
                                  </p>
                                  <button
                                    onClick={handleGenerateManual}
                                    disabled={generatingManual}
                                    className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-emerald-500 to-teal-500 text-white rounded-lg hover:from-emerald-600 hover:to-teal-600 transition-all font-medium disabled:opacity-50"
                                  >
                                    {generatingManual ? (
                                      <>
                                        <Loader2 className="w-4 h-4 animate-spin" />
                                        生成中...
                                      </>
                                    ) : (
                                      <>
                                        <Sparkles className="w-4 h-4" />
                                        マニュアルを生成
                                      </>
                                    )}
                                  </button>
                                </div>
                              </div>
                            )}

                            {/* 入力エリア */}
                            {operationManual?.status !== "completed" && (
                              <div className="p-4 border-t border-white/10">
                                <div className="flex gap-2">
                                  <input
                                    type="text"
                                    value={chatInput}
                                    onChange={(e) => setChatInput(e.target.value)}
                                    onKeyPress={(e) => e.key === "Enter" && !e.shiftKey && handleSendMessage()}
                                    placeholder="メッセージを入力..."
                                    className="flex-1 bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
                                    disabled={chatLoading}
                                  />
                                  <button
                                    onClick={handleSendMessage}
                                    disabled={chatLoading || !chatInput.trim()}
                                    className="px-4 py-2 bg-emerald-500 text-white rounded-lg hover:bg-emerald-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                  >
                                    <Send className="w-5 h-5" />
                                  </button>
                                </div>
                              </div>
                            )}
                          </>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ) : (
              <div className="glass-card p-8 flex flex-col items-center justify-center h-full min-h-[400px]">
                <FileText className="w-16 h-16 text-slate-500 mb-4" />
                <p className="text-slate-400">左側のリストからプランを選択してください</p>
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  );
}


