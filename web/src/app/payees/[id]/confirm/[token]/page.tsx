"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  ShieldCheck,
  AlertTriangle,
  Building2,
  FileCheck2,
  CheckCircle2,
  XCircle,
  Clock,
  ArrowRight,
} from "lucide-react";
import Link from "next/link";

export default function PayeeConfirmationPage() {
  const params = useParams();
  const payeeId = params.id as string;
  const token = params.token as string;

  const [loading, setLoading] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [denied, setDenied] = useState(false);
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);

  const handleConfirm = async (isApproved: boolean) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(
        `http://localhost:8000/payees/${payeeId}/confirm-evidence/${token}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            confirmed: isApproved,
            notes: notes || (isApproved ? "Confirmed genuine invoice by hospital billing." : "Unrecognized invoice by billing."),
          }),
        }
      );
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Confirmation failed");
      }
      if (isApproved) {
        setConfirmed(true);
      } else {
        setDenied(true);
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto py-10 space-y-6">
      <div className="text-center space-y-2">
        <div className="inline-flex items-center space-x-2 px-3 py-1 bg-blue-50 border border-blue-200 rounded-full text-paypal-blue text-xs font-semibold">
          <ShieldCheck className="w-3.5 h-3.5" />
          <span>Independent Payee Attestation Portal</span>
        </div>
        <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">
          Hospital / Institution Spend Verification
        </h1>
        <p className="text-sm text-slate-500 max-w-md mx-auto">
          An organizer has uploaded a medical or educational invoice claiming funds for this institution. Please attest whether this invoice was issued by your billing office.
        </p>
      </div>

      <div className="bg-white rounded-3xl p-8 border border-slate-200 shadow-sm space-y-6">
        <div className="flex items-center space-x-4 p-4 bg-slate-50 rounded-2xl border border-slate-100">
          <div className="p-3 bg-blue-100 rounded-xl text-paypal-blue">
            <Building2 className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">Target Institution</div>
            <div className="text-base font-bold text-slate-900">Registered Institutional Payee</div>
            <div className="text-xs text-slate-500 font-mono">Payee ID: {payeeId}</div>
          </div>
        </div>

        <div className="p-4 bg-amber-50 rounded-2xl border border-amber-200 text-xs text-amber-900 space-y-1">
          <div className="font-bold flex items-center space-x-1.5 text-amber-800">
            <AlertTriangle className="w-4 h-4" />
            <span>Why your confirmation is critical:</span>
          </div>
          <p>
            Vouch enforces the <strong>Payee-First</strong> standard. Organizers never receive funds directly. When you confirm, funds disburse from escrow straight to your institution’s registered PayPal account.
          </p>
        </div>

        {confirmed ? (
          <div className="p-6 bg-emerald-50 border border-emerald-200 rounded-2xl text-center space-y-3">
            <CheckCircle2 className="w-12 h-12 text-emerald-600 mx-auto" />
            <h3 className="text-lg font-bold text-emerald-900">Invoice Confirmed Genuine</h3>
            <p className="text-xs text-emerald-700 max-w-sm mx-auto">
              Your cryptographic attestation has been appended to the immutable audit log. Funds will now be cleared for institutional disbursement.
            </p>
            <Link
              href="/verify-chain"
              className="inline-flex items-center space-x-1.5 text-xs font-bold text-emerald-800 underline hover:text-emerald-900 pt-2"
            >
              <span>View Audit Block in Chain</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        ) : denied ? (
          <div className="p-6 bg-red-50 border border-red-200 rounded-2xl text-center space-y-3">
            <XCircle className="w-12 h-12 text-red-600 mx-auto" />
            <h3 className="text-lg font-bold text-red-900">Flagged as Unrecognized / Fraud</h3>
            <p className="text-xs text-red-700 max-w-sm mx-auto">
              You marked this invoice as unrecognized. The evidence has been immediately blocked from automated release and escalated to the compliance reviewer queue.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                Billing Office Notes / Reference (Optional)
              </label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="e.g., Verified in Hospital EHR Patient Account #89421. Ready for payment receipt."
                className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-2xl text-sm focus:bg-white focus:outline-none focus:ring-2 focus:ring-paypal-blue/30 focus:border-paypal-blue"
                rows={3}
              />
            </div>

            {error && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700">
                {error}
              </div>
            )}

            <div className="grid grid-cols-2 gap-4 pt-2">
              <button
                onClick={() => handleConfirm(false)}
                disabled={loading}
                className="w-full py-3 px-4 bg-slate-100 hover:bg-red-50 text-slate-700 hover:text-red-700 font-bold rounded-2xl text-sm transition-all border border-slate-200 hover:border-red-200 flex items-center justify-center space-x-2"
              >
                <XCircle className="w-4 h-4" />
                <span>Not Our Invoice</span>
              </button>
              <button
                onClick={() => handleConfirm(true)}
                disabled={loading}
                className="w-full py-3 px-4 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-2xl text-sm shadow-sm transition-all flex items-center justify-center space-x-2"
              >
                <FileCheck2 className="w-4 h-4" />
                <span>{loading ? "Confirming..." : "Confirm Invoice is Ours"}</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

