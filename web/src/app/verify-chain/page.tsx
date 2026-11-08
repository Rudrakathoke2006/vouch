"use client";

import { useEffect, useState } from "react";
import { Terminal, ShieldCheck, CheckCircle2, AlertTriangle, RefreshCw, Hash } from "lucide-react";

export default function VerifyChainPage() {
  const [verification, setVerification] = useState<any>(null);
  const [entries, setEntries] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const runVerification = async () => {
    setLoading(true);
    try {
      const [vRes, eRes] = await Promise.all([
        fetch("http://localhost:8000/audit-log/verify"),
        fetch("http://localhost:8000/audit-log?limit=50"),
      ]);
      if (vRes.ok) setVerification(await vRes.json());
      if (eRes.ok) setEntries(await eRes.json());
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    runVerification();
  }, []);

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 flex items-center space-x-2">
            <Terminal className="w-6 h-6 text-paypal-blue" />
            <span>Tamper-Evident Audit Chain Verifier</span>
          </h1>
          <p className="text-sm text-slate-500">
            Cryptographic SHA-256 hash chain with PostgreSQL transaction advisory locking.
          </p>
        </div>
        <button
          onClick={runVerification}
          className="px-4 py-2 bg-slate-900 hover:bg-paypal-blue text-white rounded-xl text-xs font-bold transition-all shadow-sm flex items-center space-x-1.5"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          <span>Re-Verify Chain</span>
        </button>
      </div>

      {/* Verification Status Card */}
      {verification && (
        <div className={`p-6 rounded-3xl border shadow-sm flex items-center justify-between ${
          verification.valid
            ? "bg-emerald-50 border-emerald-200 text-emerald-950"
            : "bg-red-50 border-red-200 text-red-950"
        }`}>
          <div className="flex items-center space-x-4">
            <div className={`p-3 rounded-2xl ${verification.valid ? "bg-emerald-600 text-white" : "bg-red-600 text-white"}`}>
              {verification.valid ? <CheckCircle2 className="w-7 h-7" /> : <AlertTriangle className="w-7 h-7" />}
            </div>
            <div>
              <h2 className="text-lg font-black tracking-tight">
                {verification.valid ? "Cryptographic Chain Verified: 100% INTACT" : "INTEGRITY VIOLATION DETECTED"}
              </h2>
              <p className="text-xs opacity-80 font-medium">
                {verification.valid
                  ? `All ${verification.total_entries} blocks verified from genesis block (0000...) to head.`
                  : verification.error}
              </p>
            </div>
          </div>
          <div className="text-right hidden sm:block">
            <div className="text-[11px] font-bold uppercase opacity-70">Total Blocks</div>
            <div className="text-2xl font-black">{verification.total_entries}</div>
          </div>
        </div>
      )}

      {/* Hash Chain Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden space-y-4 p-6">
        <h3 className="font-extrabold text-slate-900 text-sm flex items-center space-x-2">
          <Hash className="w-4 h-4 text-paypal-blue" />
          <span>Recent Blocks (Chronological Order)</span>
        </h3>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-bold uppercase tracking-wider">
              <tr>
                <th className="px-3 py-2.5">Seq</th>
                <th className="px-3 py-2.5">Event Type</th>
                <th className="px-3 py-2.5">Previous Hash</th>
                <th className="px-3 py-2.5">Block Hash</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {entries.map((entry) => (
                <tr key={entry.seq} className="hover:bg-slate-50/80 transition-colors">
                  <td className="px-3 py-2.5 font-bold text-slate-900">#{entry.seq}</td>
                  <td className="px-3 py-2.5 font-sans font-bold text-slate-800">
                    <span className="px-2 py-0.5 bg-blue-50 text-paypal-blue rounded border border-blue-100 text-[11px]">
                      {entry.event_type}
                    </span>
                  </td>
                  <td className="px-3 py-2.5 text-slate-400 text-[11px]">
                    {entry.prev_hash.slice(0, 16)}...
                  </td>
                  <td className="px-3 py-2.5 font-bold text-emerald-600 text-[11px]">
                    {entry.hash.slice(0, 16)}...
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
