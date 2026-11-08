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
  ShieldCheck,
  Search,
  ExternalLink,
  DollarSign,
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

interface PriceReference {
  id: number;
  item_key: string;
  description: string;
  hcpcs: string | null;
  low: number;
  median: number;
  high: number;
  source: string;
  source_url: string;
  effective_date: string;
}

export default function ReviewerQueuePage() {
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedAudit, setSelectedAudit] = useState<QueueItem | null>(null);
  const [reviewAction, setReviewAction] = useState<"APPROVE" | "REJECT" | "REQUEST_MORE">("APPROVE");
  const [reviewReason, setReviewReason] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // Live Registry Verification Tool State
  const [verifyType, setVerifyType] = useState<"NONPROFIT_IRS" | "HEALTHCARE_NPI">("NONPROFIT_IRS");
  const [einInput, setEinInput] = useState("");
  const [nameInput, setNameInput] = useState("");
  const [npiInput, setNpiInput] = useState("");
  const [verifyLoading, setVerifyLoading] = useState(false);
  const [verifyResult, setVerifyResult] = useState<any>(null);

  // Price References Drawer State
  const [showPriceSchedule, setShowPriceSchedule] = useState(false);
  const [prices, setPrices] = useState<PriceReference[]>([]);

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

  const fetchPrices = async () => {
    try {
      const res = await fetch("http://localhost:8000/reference-prices");
      if (res.ok) {
        const data = await res.json();
        setPrices(data);
      }
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchQueue();
    fetchPrices();
  }, []);

  const handleRunVerify = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setVerifyLoading(true);
    setVerifyResult(null);
    try {
      const res = await fetch("http://localhost:8000/payees/verify-external", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          verification_type: verifyType,
          ein: einInput,
          npi: npiInput,
          claimed_name: nameInput,
          state: "TN",
        }),
      });
      const data = await res.json();
      setVerifyResult(data);
    } catch (err) {
      console.error(err);
    } finally {
      setVerifyLoading(false);
    }
  };

  const loadPreset = (type: "red_cross" | "fake_ein" | "mercy_hospital") => {
    if (type === "red_cross") {
      setVerifyType("NONPROFIT_IRS");
      setEinInput("53-0196605");
      setNameInput("American National Red Cross");
      setNpiInput("");
    } else if (type === "fake_ein") {
      setVerifyType("NONPROFIT_IRS");
      setEinInput("00-0000000");
      setNameInput("Fake Humanitarian Fund");
      setNpiInput("");
    } else if (type === "mercy_hospital") {
      setVerifyType("HEALTHCARE_NPI");
      setNpiInput("1790757657");
      setNameInput("Mercy Hospital St. Louis");
      setEinInput("");
    }
  };

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
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-extrabold text-slate-900 flex items-center space-x-2 tracking-tight">
            <Eye className="w-7 h-7 text-paypal-blue" />
            <span>Human Reviewer & Compliance Queue</span>
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Audit flagged evidence, verify institutional payees against live government registries, and inspect CMS DMEPOS fee ceilings.
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={() => setShowPriceSchedule(!showPriceSchedule)}
            className="px-3.5 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold rounded-xl text-xs transition-colors flex items-center space-x-1.5"
          >
            <DollarSign className="w-3.5 h-3.5" />
            <span>{showPriceSchedule ? "Hide Price Schedule" : "CMS Price Schedule"}</span>
          </button>
          <button
            onClick={fetchQueue}
            className="p-2.5 text-slate-500 hover:text-slate-900 rounded-xl hover:bg-slate-100 transition-colors border border-slate-200"
            title="Refresh Queue"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Real-World Payee Verification Sandbox Widget */}
      <div className="bg-white rounded-3xl p-6 border border-slate-200 shadow-sm space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center space-x-2">
            <ShieldCheck className="w-5 h-5 text-paypal-blue" />
            <h2 className="text-base font-bold text-slate-900">Live Government &amp; Healthcare Registry Verification</h2>
          </div>
          <div className="flex items-center space-x-1.5 text-xs text-slate-500">
            <span>Quick Presets:</span>
            <button
              onClick={() => loadPreset("red_cross")}
              className="px-2 py-0.5 rounded-lg bg-emerald-50 text-emerald-700 font-bold hover:bg-emerald-100 border border-emerald-200"
            >
              Real 501(c)(3) (Pass)
            </button>
            <button
              onClick={() => loadPreset("fake_ein")}
              className="px-2 py-0.5 rounded-lg bg-red-50 text-red-700 font-bold hover:bg-red-100 border border-red-200"
            >
              Fake EIN (Fail)
            </button>
            <button
              onClick={() => loadPreset("mercy_hospital")}
              className="px-2 py-0.5 rounded-lg bg-blue-50 text-blue-700 font-bold hover:bg-blue-100 border border-blue-200"
            >
              Hospital NPI (Pass)
            </button>
          </div>
        </div>

        <div className="bg-amber-50 border border-amber-200 text-amber-900 rounded-xl px-3 py-2 text-[11px] flex items-center space-x-2">
          <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
          <span>
            <strong>Registry Verification Demo Only:</strong> Real non-profit and healthcare queries (e.g. American Red Cross Form 990 via ProPublica API) demonstrate live API validation. Vouch does not claim affiliation with or endorsement by these entities, and national charities cannot be onboarded as sandbox campaign payout payees.
          </span>
        </div>

        <form onSubmit={handleRunVerify} className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <div>
            <label className="block text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-1">
              Registry Type
            </label>
            <select
              value={verifyType}
              onChange={(e) => setVerifyType(e.target.value as any)}
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold focus:outline-none focus:ring-2 focus:ring-paypal-blue/30"
            >
              <option value="NONPROFIT_IRS">ProPublica IRS 501(c)(3)</option>
              <option value="HEALTHCARE_NPI">CMS NPPES NPI Registry</option>
            </select>
          </div>

          <div>
            <label className="block text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-1">
              {verifyType === "NONPROFIT_IRS" ? "EIN (Tax ID)" : "NPI Number (10 Digits)"}
            </label>
            <input
              type="text"
              value={verifyType === "NONPROFIT_IRS" ? einInput : npiInput}
              onChange={(e) => verifyType === "NONPROFIT_IRS" ? setEinInput(e.target.value) : setNpiInput(e.target.value)}
              placeholder={verifyType === "NONPROFIT_IRS" ? "e.g., 53-0196605" : "e.g., 1790757657"}
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs focus:outline-none focus:ring-2 focus:ring-paypal-blue/30"
            />
          </div>

          <div>
            <label className="block text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-1">
              Claimed Organization Legal Name
            </label>
            <input
              type="text"
              value={nameInput}
              onChange={(e) => setNameInput(e.target.value)}
              placeholder="e.g., American National Red Cross"
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs focus:outline-none focus:ring-2 focus:ring-paypal-blue/30"
            />
          </div>

          <div className="flex items-end">
            <button
              type="submit"
              disabled={verifyLoading}
              className="w-full py-2 px-4 bg-paypal-blue hover:bg-blue-700 text-white font-bold rounded-xl text-xs transition-colors flex items-center justify-center space-x-1.5 shadow-sm"
            >
              <Search className="w-3.5 h-3.5" />
              <span>{verifyLoading ? "Verifying..." : "Verify Registry"}</span>
            </button>
          </div>
        </form>

        {/* Live Registry Output Card */}
        {verifyResult && (
          <div className={`p-4 rounded-2xl border text-xs space-y-2 ${
            verifyResult.ok ? "bg-emerald-50 border-emerald-200 text-emerald-950" : "bg-red-50 border-red-200 text-red-950"
          }`}>
            <div className="flex items-center justify-between font-bold">
              <span className="flex items-center space-x-1.5">
                {verifyResult.ok ? <CheckCircle className="w-4 h-4 text-emerald-600" /> : <XCircle className="w-4 h-4 text-red-600" />}
                <span>Status: {verifyResult.status}</span>
              </span>
              <span className="text-[10px] uppercase tracking-wider text-slate-500 font-mono">
                Source: {verifyResult.source}
              </span>
            </div>
            <div className="text-xs">
              {verifyResult.reason || verifyResult.note}
            </div>
            {verifyResult.irs_name && (
              <div className="pt-1 text-[11px] text-slate-600 flex items-center space-x-4">
                <span><strong>IRS Legal Name:</strong> {verifyResult.irs_name}</span>
                <span><strong>State:</strong> {verifyResult.state}</span>
                <span><strong>Recent Form 990:</strong> {verifyResult.last_filing_year || "Electronic Form 990-N"}</span>
              </div>
            )}
            {verifyResult.official_name && (
              <div className="pt-1 text-[11px] text-slate-600 flex items-center space-x-4">
                <span><strong>NPI Official Name:</strong> {verifyResult.official_name}</span>
                <span><strong>NPI Number:</strong> {verifyResult.npi}</span>
                <span><strong>Authorized Official:</strong> {verifyResult.authorized_official}</span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Real CMS Price Schedule Viewer */}
      {showPriceSchedule && (
        <div className="bg-white rounded-3xl p-6 border border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div>
              <h2 className="text-base font-bold text-slate-900">CMS DMEPOS &amp; Public Vendor Fee Ceilings</h2>
              <p className="text-xs text-slate-500">
                Official Medicare fee schedules and vendor catalogs used by the Evidence Auditor to detect price inflation.
              </p>
            </div>
            <span className="px-2.5 py-1 rounded-full text-[10px] font-bold bg-blue-50 text-paypal-blue border border-blue-200 uppercase">
              Provenanced Ceilings
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-bold uppercase tracking-wider">
                <tr>
                  <th className="px-3.5 py-2.5">Item &amp; Description</th>
                  <th className="px-3.5 py-2.5">HCPCS Code</th>
                  <th className="px-3.5 py-2.5">Low Rate</th>
                  <th className="px-3.5 py-2.5">Median Rate</th>
                  <th className="px-3.5 py-2.5">Medicare Ceiling</th>
                  <th className="px-3.5 py-2.5">Official Source &amp; Provenance</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {prices.map((p) => (
                  <tr key={p.id} className="hover:bg-slate-50">
                    <td className="px-3.5 py-2.5">
                      <div className="font-bold text-slate-900">{p.item_key.replace(/_/g, " ")}</div>
                      <div className="text-[11px] text-slate-500">{p.description}</div>
                    </td>
                    <td className="px-3.5 py-2.5 font-mono font-bold text-slate-700">
                      {p.hcpcs || "N/A (Catalog)"}
                    </td>
                    <td className="px-3.5 py-2.5 font-mono text-slate-600">${p.low.toLocaleString()}</td>
                    <td className="px-3.5 py-2.5 font-mono text-slate-600">${p.median.toLocaleString()}</td>
                    <td className="px-3.5 py-2.5 font-mono font-bold text-emerald-700">${p.high.toLocaleString()}</td>
                    <td className="px-3.5 py-2.5 text-[11px]">
                      <a
                        href={p.source_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-paypal-blue hover:underline font-semibold flex items-center space-x-1"
                      >
                        <span>{p.source}</span>
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Reviewer Queue Table */}
      {loading ? (
        <div className="text-center py-16 text-slate-400">Loading reviewer queue...</div>
      ) : queue.length === 0 ? (
        <div className="bg-white rounded-3xl border border-dashed border-slate-300 p-12 text-center space-y-3">
          <CheckCircle className="w-10 h-10 text-emerald-500 mx-auto" />
          <h3 className="font-bold text-slate-800 text-base">Queue is Clear!</h3>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">
            All spend evidence has passed automated hard checks with low risk scores, or has already been reviewed.
          </p>
        </div>
      ) : (
        <div className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-bold uppercase tracking-wider">
                <tr>
                  <th className="px-4 py-3.5">Campaign &amp; Payee</th>
                  <th className="px-4 py-3.5">Amount</th>
                  <th className="px-4 py-3.5">Risk Score</th>
                  <th className="px-4 py-3.5">Verdict</th>
                  <th className="px-4 py-3.5">Plain-Language Auditor Explanation</th>
                  <th className="px-4 py-3.5 text-right">Review Action</th>
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
                        item.risk_score <= 20
                          ? "bg-emerald-100 text-emerald-800"
                          : item.risk_score <= 60
                          ? "bg-amber-100 text-amber-800"
                          : "bg-red-100 text-red-800"
                      }`}>
                        {item.risk_score} / 100
                      </span>
                    </td>
                    <td className="px-4 py-3.5">
                      <span className="font-bold text-slate-700 uppercase">
                        {item.decision}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 text-slate-600 max-w-md line-clamp-2">
                      {item.explanation}
                    </td>
                    <td className="px-4 py-3.5 text-right">
                      {item.reviewed ? (
                        <span className="text-[11px] font-bold text-slate-400 uppercase">
                          Decided ({item.reviewer_action})
                        </span>
                      ) : (
                        <button
                          onClick={() => {
                            setSelectedAudit(item);
                            setReviewAction(item.decision === "REJECT" ? "REJECT" : "APPROVE");
                          }}
                          className="px-3 py-1.5 bg-slate-900 hover:bg-slate-800 text-white font-bold rounded-xl text-xs transition-colors"
                        >
                          Triage Case
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

      {/* Reviewer Triage Modal */}
      {selectedAudit && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-lg w-full p-6 shadow-2xl border border-slate-200 space-y-5 animate-in fade-in zoom-in-95 duration-200">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="font-extrabold text-slate-900 text-lg">Human Reviewer Triage</h3>
              <button
                onClick={() => setSelectedAudit(null)}
                className="text-slate-400 hover:text-slate-700 text-xl font-bold"
              >
                &times;
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="p-3 bg-slate-50 rounded-2xl border border-slate-100 space-y-1">
                <div className="text-slate-500"><strong>Campaign:</strong> {selectedAudit.campaign_title}</div>
                <div className="text-slate-500"><strong>Payee:</strong> {selectedAudit.payee_name}</div>
                <div className="text-slate-500"><strong>Requested Release:</strong> ${selectedAudit.requested_amount.toLocaleString()}</div>
                <div className="text-slate-500"><strong>AI Risk Score:</strong> {selectedAudit.risk_score} / 100</div>
              </div>

              <div className="p-3 bg-amber-50 rounded-2xl border border-amber-200 text-amber-900 space-y-1">
                <div className="font-bold flex items-center space-x-1">
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
                  <span>Auditor Reason:</span>
                </div>
                <p>{selectedAudit.explanation}</p>
              </div>
            </div>

            <form onSubmit={handleSubmitReview} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                  Reviewer Decision
                </label>
                <div className="grid grid-cols-3 gap-2">
                  <button
                    type="button"
                    onClick={() => setReviewAction("APPROVE")}
                    className={`py-2 text-xs font-bold rounded-xl border transition-all ${
                      reviewAction === "APPROVE"
                        ? "bg-emerald-600 text-white border-emerald-600 shadow-sm"
                        : "bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100"
                    }`}
                  >
                    Approve
                  </button>
                  <button
                    type="button"
                    onClick={() => setReviewAction("REQUEST_MORE")}
                    className={`py-2 text-xs font-bold rounded-xl border transition-all ${
                      reviewAction === "REQUEST_MORE"
                        ? "bg-amber-600 text-white border-amber-600 shadow-sm"
                        : "bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100"
                    }`}
                  >
                    Request Info
                  </button>
                  <button
                    type="button"
                    onClick={() => setReviewAction("REJECT")}
                    className={`py-2 text-xs font-bold rounded-xl border transition-all ${
                      reviewAction === "REJECT"
                        ? "bg-red-600 text-white border-red-600 shadow-sm"
                        : "bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100"
                    }`}
                  >
                    Reject
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                  Mandatory Compliance Justification
                </label>
                <textarea
                  value={reviewReason}
                  onChange={(e) => setReviewReason(e.target.value)}
                  placeholder="e.g., Verified invoice against hospital billing record and confirmed line item pricing within Medicare limits."
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs focus:bg-white focus:outline-none focus:ring-2 focus:ring-paypal-blue/30"
                  rows={3}
                  required
                />
              </div>

              <div className="flex items-center justify-end space-x-3 pt-2">
                <button
                  type="button"
                  onClick={() => setSelectedAudit(null)}
                  className="px-4 py-2 text-xs font-bold text-slate-500 hover:text-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting || !reviewReason}
                  className="px-5 py-2 bg-slate-900 hover:bg-black text-white font-bold rounded-xl text-xs shadow-sm transition-all disabled:opacity-50"
                >
                  {submitting ? "Signing Audit Block..." : "Commit Decision to Chain"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
