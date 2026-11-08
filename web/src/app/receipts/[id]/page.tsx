"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  ShieldCheck,
  CheckCircle2,
  Building2,
  Hash,
  Terminal,
  ArrowLeft,
  Calendar,
  Lock,
} from "lucide-react";

export default function DonorReceiptPage() {
  const params = useParams();
  const id = params.id as string;

  const [receipt, setReceipt] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchReceipt = async () => {
      try {
        const res = await fetch(`http://localhost:8000/receipts/${id}`);
        if (res.ok) {
          const data = await res.json();
          setReceipt(data);
        }
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchReceipt();
  }, [id]);

  if (loading) {
    return <div className="text-center py-20 text-slate-400">Loading public receipt...</div>;
  }

  if (!receipt) {
    return <div className="text-center py-20 text-red-500 font-semibold">Receipt not found</div>;
  }

  const payee = receipt.verified_payee || {};

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <Link
        href="/"
        className="inline-flex items-center space-x-1.5 text-xs font-semibold text-slate-500 hover:text-slate-900 transition-colors"
      >
        <ArrowLeft className="w-3.5 h-3.5" />
        <span>Back to Campaigns</span>
      </Link>

      <div className="bg-white rounded-3xl p-8 border border-slate-200 shadow-lg space-y-6">
        {/* Receipt Header */}
        <div className="flex items-center justify-between pb-6 border-b border-slate-100">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 bg-paypal-blue text-white rounded-2xl shadow-sm">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-xl font-extrabold text-slate-900">Official Vouch Receipt</h1>
              <p className="text-xs text-slate-500">Public Verifiable Proof of Donation &amp; Release</p>
            </div>
          </div>
          <span className="px-3 py-1 bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-bold rounded-full uppercase tracking-wider flex items-center space-x-1">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>{receipt.status}</span>
          </span>
        </div>

        {/* Donation Details */}
        <div className="space-y-4">
          <div className="flex justify-between text-sm py-2 border-b border-slate-50">
            <span className="text-slate-500">Campaign</span>
            <span className="font-bold text-slate-900 text-right">{receipt.campaign_title}</span>
          </div>
          <div className="flex justify-between text-sm py-2 border-b border-slate-50">
            <span className="text-slate-500">Donor</span>
            <span className="font-medium text-slate-900">{receipt.donor_name}</span>
          </div>
          <div className="flex justify-between text-sm py-2 border-b border-slate-50">
            <span className="text-slate-500">Amount</span>
            <span className="font-extrabold text-lg text-emerald-600">
              ${receipt.amount?.toFixed(2)} {receipt.currency}
            </span>
          </div>
          <div className="flex justify-between text-sm py-2 border-b border-slate-50">
            <span className="text-slate-500">PayPal Capture ID</span>
            <code className="font-mono text-xs text-slate-700 bg-slate-100 px-2 py-0.5 rounded">
              {receipt.paypal_capture_id || "HELD_PLATFORM"}
            </code>
          </div>
        </div>

        {/* Verified Payee Destination */}
        <div className="bg-slate-50 p-4 rounded-2xl border border-slate-100 space-y-2">
          <div className="text-xs font-bold text-slate-500 uppercase tracking-wide flex items-center space-x-1.5">
            <Building2 className="w-4 h-4 text-paypal-blue" />
            <span>Guaranteed Destination Payee</span>
          </div>
          <div className="font-bold text-sm text-slate-900">{payee.name}</div>
          <div className="text-xs text-slate-600">
            Registration: <code className="font-mono bg-white px-1.5 py-0.5 rounded border border-slate-200">{payee.registration_id}</code> | Category: {payee.category}
          </div>
        </div>

        {/* Cryptographic Tamper-Proof Chain Head */}
        <div className="bg-slate-900 text-slate-200 p-4 rounded-2xl space-y-2 text-xs">
          <div className="flex items-center justify-between text-slate-400 font-semibold">
            <div className="flex items-center space-x-1.5">
              <Hash className="w-3.5 h-3.5 text-blue-400" />
              <span>Audit Chain Block Hash</span>
            </div>
            <Link
              href="/verify-chain"
              className="text-blue-400 hover:text-blue-300 font-bold flex items-center space-x-1"
            >
              <Terminal className="w-3 h-3" />
              <span>Verify Chain Integrity</span>
            </Link>
          </div>
          <code className="block font-mono text-[11px] text-emerald-400 break-all bg-slate-950/80 p-2 rounded-lg border border-slate-800">
            {receipt.tamper_proof_chain_head || "GENESIS_BLOCK"}
          </code>
        </div>
      </div>
    </div>
  );
}

