"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  ShieldCheck,
  Building2,
  Clock,
  CheckCircle2,
  AlertTriangle,
  UploadCloud,
  ArrowRight,
  Receipt,
  DollarSign,
  FileText,
  Lock,
} from "lucide-react";

export default function CampaignDetailPage() {
  const params = useParams();
  const id = params.id as string;

  const [campaign, setCampaign] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  // Donation state
  const [donorName, setDonorName] = useState("Alex River");
  const [donorEmail, setDonorEmail] = useState("alex.donor@example.com");
  const [donateAmount, setDonateAmount] = useState(250);
  const [donating, setDonating] = useState(false);
  const [lastDonationId, setLastDonationId] = useState<string | null>(null);

  // Evidence upload state
  const [file, setFile] = useState<File | null>(null);
  const [reqAmount, setReqAmount] = useState(1500);
  const [uploading, setUploading] = useState(false);
  const [auditResult, setAuditResult] = useState<any>(null);

  const fetchCampaign = async () => {
    try {
      const res = await fetch(`http://localhost:8000/campaigns/${id}`);
      if (res.ok) {
        const data = await res.json();
        setCampaign(data);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCampaign();
  }, [id]);

  const handleDonate = async (e: React.FormEvent) => {
    e.preventDefault();
    setDonating(true);
    try {
      // 1. Create order
      const ordRes = await fetch(`http://localhost:8000/campaigns/${id}/donate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          donor_name: donorName,
          donor_email: donorEmail,
          amount: Number(donateAmount),
        }),
      });
      const ordData = await ordRes.json();

      // 2. Capture order (simulating PayPal sandbox approval)
      const capRes = await fetch(`http://localhost:8000/orders/${ordData.paypal_order_id}/capture`, {
        method: "POST",
      });
      const capData = await capRes.json();
      setLastDonationId(capData.id);

      await fetchCampaign();
    } catch (err) {
      console.error("Donation failed:", err);
    } finally {
      setDonating(false);
    }
  };

  const handleUploadEvidence = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;
    setUploading(true);
    setAuditResult(null);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("requested_amount", String(reqAmount));

    try {
      const res = await fetch(`http://localhost:8000/campaigns/${id}/evidence`, {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      setAuditResult(data);
      await fetchCampaign();
    } catch (err) {
      console.error("Evidence upload failed:", err);
    } finally {
      setUploading(false);
    }
  };

  if (loading) {
    return <div className="text-center py-16 text-slate-400">Loading campaign...</div>;
  }

  if (!campaign) {
    return <div className="text-center py-16 text-red-500 font-semibold">Campaign not found</div>;
  }

  const fin = campaign.financials || {};
  const payee = campaign.payee || {};

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      {/* Title & Payee Header */}
      <div className="bg-white rounded-3xl p-8 border border-slate-200 shadow-sm space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="space-y-1">
            <span className="text-xs font-bold px-2.5 py-1 bg-blue-50 text-paypal-blue rounded-md border border-blue-100 uppercase tracking-wide">
              {campaign.purpose_category}
            </span>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900">
              {campaign.title}
            </h1>
          </div>

          {/* Verified Payee Card */}
          <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-4 flex items-center space-x-3.5">
            <div className="p-2 bg-emerald-600 text-white rounded-xl">
              <Building2 className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-1.5">
                <span className="font-bold text-sm text-emerald-950">
                  {payee.legal_name || "Verified Institutional Payee"}
                </span>
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              </div>
              <div className="text-xs text-emerald-800">
                Reg ID: <code className="font-mono bg-emerald-100 px-1 py-0.5 rounded">{payee.registration_id}</code> | Category: {payee.category}
              </div>
            </div>
          </div>
        </div>

        <p className="text-slate-600 leading-relaxed text-sm sm:text-base">
          {campaign.story}
        </p>

        {/* Financial Ledger Breakdown */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-4 border-t border-slate-100 text-center">
          <div className="bg-slate-50 p-4 rounded-xl border border-slate-100">
            <div className="text-xs font-semibold text-slate-500 uppercase">Goal</div>
            <div className="text-lg font-bold text-slate-900">${campaign.goal.toLocaleString()}</div>
          </div>
          <div className="bg-blue-50 p-4 rounded-xl border border-blue-100">
            <div className="text-xs font-semibold text-blue-700 uppercase">Total Donated</div>
            <div className="text-lg font-bold text-paypal-blue">${fin.total_donations?.toLocaleString() || 0}</div>
          </div>
          <div className="bg-amber-50 p-4 rounded-xl border border-amber-200">
            <div className="text-xs font-semibold text-amber-800 uppercase">Held In Platform</div>
            <div className="text-lg font-bold text-amber-900">${fin.held_balance?.toLocaleString() || 0}</div>
          </div>
          <div className="bg-emerald-50 p-4 rounded-xl border border-emerald-200">
            <div className="text-xs font-semibold text-emerald-800 uppercase">Released to Payee</div>
            <div className="text-lg font-bold text-emerald-900">${fin.total_releases?.toLocaleString() || 0}</div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {/* Donor Action Card */}
        <div className="bg-white rounded-3xl p-6 border border-slate-200 shadow-sm space-y-5">
          <div className="flex items-center space-x-2">
            <DollarSign className="w-5 h-5 text-paypal-blue" />
            <h2 className="text-lg font-bold text-slate-900">Make a Donation</h2>
          </div>
          <p className="text-xs text-slate-500">
            Funds are captured to Vouch&apos;s platform ledger and released <strong>only</strong> after independent AI audit verification against the registered hospital/school.
          </p>

          <form onSubmit={handleDonate} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Your Name</label>
              <input
                type="text"
                value={donorName}
                onChange={(e) => setDonorName(e.target.value)}
                required
                className="w-full px-3.5 py-2 border border-slate-300 rounded-xl text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Your Email</label>
              <input
                type="email"
                value={donorEmail}
                onChange={(e) => setDonorEmail(e.target.value)}
                required
                className="w-full px-3.5 py-2 border border-slate-300 rounded-xl text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Donation Amount ($ USD)</label>
              <input
                type="number"
                min="1"
                value={donateAmount}
                onChange={(e) => setDonateAmount(Number(e.target.value))}
                required
                className="w-full px-3.5 py-2 border border-slate-300 rounded-xl text-sm font-bold text-slate-900"
              />
            </div>

            <button
              type="submit"
              disabled={donating}
              className="w-full py-3 bg-paypal-gold hover:bg-yellow-400 text-slate-950 font-extrabold rounded-xl text-sm transition-all shadow-md flex items-center justify-center space-x-2 disabled:opacity-50"
            >
              <span>{donating ? "Processing with PayPal Sandbox..." : `Donate $${donateAmount} with PayPal`}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>

          {lastDonationId && (
            <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl space-y-2">
              <div className="flex items-center space-x-2 text-emerald-800 font-semibold text-xs">
                <CheckCircle2 className="w-4 h-4" />
                <span>Donation Captured! Funds are securely HELD.</span>
              </div>
              <Link
                href={`/receipts/${lastDonationId}`}
                className="inline-flex items-center space-x-1.5 text-xs font-bold text-paypal-blue hover:underline"
              >
                <Receipt className="w-3.5 h-3.5" />
                <span>View Public Transparent Donor Receipt &rarr;</span>
              </Link>
            </div>
          )}
        </div>

        {/* Evidence Upload Card (Organizer) */}
        <div className="bg-white rounded-3xl p-6 border border-slate-200 shadow-sm space-y-5">
          <div className="flex items-center space-x-2">
            <UploadCloud className="w-5 h-5 text-indigo-600" />
            <h2 className="text-lg font-bold text-slate-900">Upload Spend Evidence</h2>
          </div>
          <p className="text-xs text-slate-500">
            Submit an invoice/bill addressed to the registered payee. The Multimodal Evidence Auditor will extract fields, verify arithmetic, benchmark prices, and check cross-campaign duplicate reuse.
          </p>

          <form onSubmit={handleUploadEvidence} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Invoice Document (PDF, PNG, JPG &le; 10MB)</label>
              <input
                type="file"
                accept=".pdf,.png,.jpg,.jpeg"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
                required
                className="w-full text-xs text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Requested Release Amount ($ USD)</label>
              <input
                type="number"
                min="1"
                value={reqAmount}
                onChange={(e) => setReqAmount(Number(e.target.value))}
                required
                className="w-full px-3.5 py-2 border border-slate-300 rounded-xl text-sm font-semibold"
              />
            </div>

            <button
              type="submit"
              disabled={uploading || !file}
              className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-xl text-sm transition-all shadow-md flex items-center justify-center space-x-2 disabled:opacity-50"
            >
              <span>{uploading ? "Auditing with Vision AI..." : "Submit for AI Evidence Audit"}</span>
              <FileText className="w-4 h-4" />
            </button>
          </form>

          {/* Live Audit Result */}
          {auditResult && (
            <div className={`p-4 rounded-2xl border space-y-3 ${
              auditResult.decision === "RELEASE"
                ? "bg-emerald-50 border-emerald-200"
                : auditResult.decision === "REJECT"
                ? "bg-red-50 border-red-200"
                : "bg-amber-50 border-amber-200"
            }`}>
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold uppercase tracking-wide">
                  Audit Verdict:{" "}
                  <span className={`px-2 py-0.5 rounded-full font-black ${
                    auditResult.decision === "RELEASE"
                      ? "bg-emerald-600 text-white"
                      : auditResult.decision === "REJECT"
                      ? "bg-red-600 text-white"
                      : "bg-amber-500 text-slate-950"
                  }`}>
                    {auditResult.decision}
                  </span>
                </span>
                <span className="font-semibold text-slate-700">
                  Risk Score: {auditResult.risk_score} / 100
                </span>
              </div>
              <p className="text-xs text-slate-700 leading-relaxed font-medium">
                {auditResult.explanation}
              </p>
              {auditResult.confirmation_token && (
                <div className="text-[11px] text-slate-500 pt-1 border-t border-slate-200/60">
                  (Add-On 1) Payee Confirmation Token: <code className="font-mono text-slate-800">{auditResult.confirmation_token.slice(0, 16)}...</code>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

