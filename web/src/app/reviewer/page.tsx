"use client";

import { useEffect, useState } from "react";
import {
  Eye,
  AlertTriangle,
  CheckCircle,
  XCircle,
  HelpCircle,
  Building2,
  RefreshCw,
  FileText,
} from "lucide-react";

interface QueueItem {
  audit_id: string;
  campaign_id: string;
  campaign_title: string;
  payee_name: string;
  payee_registration_id: string;
  requested_amount: number;
  risk_score: number;
  decision: string;
  explanation: string;
  evidence_file_path: string;
  payee_confirmed: boolean;
  reviewed: boolean;
  reviewer_action: string | null;
  created_at: string;
}

export default function ReviewerQueuePage() {
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedAudit, setSelectedAudit] = useState<QueueItem | null>(null);
  const [reviewAction, setReviewAction] = useState<"APPROVE" | "REJECT" | "REQUEST_MORE">("APPROVE");
  const [reviewReason, setReviewReason] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const fetchQueue = async () => {
    try {
      const res = await fetch("http://localhost:8000/reviews/queue");
      if (res.ok) {
        const data = await res.json();
        setQueue(data);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQueue();
  }, []);

  const handleSubmitReview = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedAudit || !reviewReason) return;
    setSubmitting(true);
    try {
      const res = await fetch(`http://localhost:8000/reviews/${selectedAudit.audit_id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: reviewAction,
          reviewer: "human_admin_lead",
          reason: reviewReason,
        }),
      });
      if (res.ok) {
        setSelectedAudit(null);
        setReviewReason("");
        await fetchQueue();
      }
    } catch (err) {
      console.error(err);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 flex items-center space-x-2">
            <Eye className="w-6 h-6 text-paypal-blue" />
            <span>Human Reviewer Queue</span>
          </h1>
          <p className="text-sm text-slate-500">
            Cases flagged by the Evidence Auditor for elevated risk, price anomalies, or duplicate reuse.
          </p>
        </div>
        <button
          onClick={fetchQueue}
          className="p-2 text-slate-500 hover:text-slate-900 rounded-lg hover:bg-slate-100 transition-colors"
          title="Refresh"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {loading ? (
        <div className="text-center py-16 text-slate-400">Loading reviewer queue...</div>
      ) : queue.length === 0 ? (
        <div className="bg-white rounded-2xl border border-dashed border-slate-300 p-12 text-center space-y-3">
          <CheckCircle className="w-10 h-10 text-emerald-500 mx-auto" />
          <h3 className="font-bold text-slate-800">Queue is Clear!</h3>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">
            All evidence documents have been validated with low risk, or no cases currently require human triage.
          </p>
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-bold uppercase tracking-wider">
                <tr>
                  <th className="px-4 py-3.5">Campaign &amp; Payee</th>
                  <th className="px-4 py-3.5">Amount</th>
                  <th className="px-4 py-3.5">Risk Score</th>
                  <th className="px-4 py-3.5">Status</th>
                  <th className="px-4 py-3.5">Plain-Language Reason</th>
                  <th className="px-4 py-3.5 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {queue.map((item) => (
                  <tr key={item.audit_id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="px-4 py-3.5 space-y-0.5">
                      <div className="font-bold text-slate-900">{item.campaign_title}</div>
                      <div className="text-slate-500 flex items-center space-x-1">
                        <Building2 className="w-3 h-3 text-slate-400" />
                        <span>{item.payee_name}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3.5 font-bold text-slate-800">
                      ${item.requested_amount.toLocaleString()}
                    </td>
                    <td className="px-4 py-3.5">
                      <span className={`px-2 py-0.5 rounded-full font-bold text-[11px] ${
                        item.risk_score <= 25
                          ? "bg-emerald-100 text-emerald-800"
                          : item.risk_score <= 60
                          ? "bg-amber-100 text-amber-800"
                          : "bg-red-100 text-red-800"
                      }`}>
                        {item.risk_score} / 100
                      </span>
                    </td>
                    <td className="px-4 py-3.5">
                      <span className="font-semibold text-slate-700 uppercase">
                        {item.decision}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 text-slate-600 max-w-md line-clamp-2">
                      {item.explanation}
                    </td>
                    <td className="px-4 py-3.5 text-right">
                      {item.reviewed ? (
                        <span className="font-bold text-emerald-700">
                          {item.reviewer_action}
                        </span>
                      ) : (
                        <button
                          onClick={() => setSelectedAudit(item)}
                          className="px-3 py-1.5 bg-slate-900 hover:bg-paypal-blue text-white font-bold rounded-lg transition-colors text-xs shadow-sm"
                        >
                          Review Case
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Review Modal */}
      {selectedAudit && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-lg w-full p-6 shadow-2xl border border-slate-200 space-y-5 animate-in fade-in zoom-in-95 duration-150">
            <div>
              <span className="text-xs font-bold px-2 py-0.5 bg-slate-100 text-slate-700 rounded-md uppercase">
                Triage Case
              </span>
              <h2 className="text-lg font-extrabold text-slate-900 mt-1">
                {selectedAudit.campaign_title}
              </h2>
              <p className="text-xs text-slate-500">
                Requested Release: <strong>${selectedAudit.requested_amount.toLocaleString()}</strong> to {selectedAudit.payee_name}
              </p>
            </div>

            <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-100 space-y-1">
              <div className="text-[11px] font-bold text-slate-500 uppercase">AI Auditor Rationale:</div>
              <p className="text-xs text-slate-800 leading-relaxed font-medium">
                {selectedAudit.explanation}
              </p>
            </div>

            <form onSubmit={handleSubmitReview} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Select Human Disposition</label>
                <div className="grid grid-cols-3 gap-2">
                  <button
                    type="button"
                    onClick={() => setReviewAction("APPROVE")}
                    className={`py-2 text-xs font-bold rounded-xl border transition-all ${
                      reviewAction === "APPROVE"
                        ? "bg-emerald-600 text-white border-emerald-600 shadow-sm"
                        : "bg-white text-slate-700 border-slate-200 hover:bg-slate-50"
                    }`}
                  >
                    Approve
                  </button>
                  <button
                    type="button"
                    onClick={() => setReviewAction("REQUEST_MORE")}
                    className={`py-2 text-xs font-bold rounded-xl border transition-all ${
                      reviewAction === "REQUEST_MORE"
                        ? "bg-amber-500 text-slate-950 border-amber-500 shadow-sm"
                        : "bg-white text-slate-700 border-slate-200 hover:bg-slate-50"
                    }`}
                  >
                    Request More
                  </button>
                  <button
                    type="button"
                    onClick={() => setReviewAction("REJECT")}
                    className={`py-2 text-xs font-bold rounded-xl border transition-all ${
                      reviewAction === "REJECT"
                        ? "bg-red-600 text-white border-red-600 shadow-sm"
                        : "bg-white text-slate-700 border-slate-200 hover:bg-slate-50"
                    }`}
                  >
                    Reject
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  Mandatory Review Reason (Logged to Audit Trail)
                </label>
                <textarea
                  rows={3}
                  value={reviewReason}
                  onChange={(e) => setReviewReason(e.target.value)}
                  placeholder="e.g., Verified clinic licensing directly via state health department registry."
                  required
                  className="w-full px-3 py-2 border border-slate-300 rounded-xl text-xs focus:ring-2 focus:ring-paypal-blue"
                />
              </div>

              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setSelectedAudit(null)}
                  className="px-4 py-2 border border-slate-200 text-slate-600 hover:bg-slate-100 rounded-xl text-xs font-bold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting || !reviewReason}
                  className="px-5 py-2 bg-slate-900 hover:bg-paypal-blue text-white rounded-xl text-xs font-extrabold shadow-sm disabled:opacity-50"
                >
                  {submitting ? "Logging Decision..." : "Confirm Decision"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

