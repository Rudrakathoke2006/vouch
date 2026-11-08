"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  ShieldCheck,
  Building2,
  Clock,
  Sparkles,
  ArrowRight,
  PlusCircle,
  RefreshCw,
  Lock,
} from "lucide-react";

interface Campaign {
  id: string;
  title: string;
  story: string;
  purpose_category: string;
  goal: number;
  currency: string;
  organizer: string;
  status: string;
  proof_deadline: string;
}

export default function HomePage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(true);
  const [seeding, setSeeding] = useState(false);

  const fetchCampaigns = async () => {
    try {
      const res = await fetch("http://localhost:8000/campaigns");
      if (res.ok) {
        const data = await res.json();
        setCampaigns(data);
      }
    } catch (err) {
      console.error("Error fetching campaigns:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleSeed = async () => {
    setSeeding(true);
    try {
      const res = await fetch("http://localhost:8000/sim/seed", { method: "POST" });
      if (res.ok) {
        await fetchCampaigns();
      }
    } catch (err) {
      console.error("Seed failed:", err);
    } finally {
      setSeeding(false);
    }
  };

  useEffect(() => {
    fetchCampaigns();
  }, []);

  return (
    <div className="space-y-10">
      {/* Hero Banner */}
      <div className="bg-gradient-to-br from-slate-900 via-blue-950 to-slate-900 text-white rounded-3xl p-8 sm:p-12 shadow-xl border border-slate-800 relative overflow-hidden">
        <div className="max-w-3xl space-y-4 relative z-10">
          <div className="inline-flex items-center space-x-2 px-3 py-1 bg-blue-500/10 border border-blue-400/30 rounded-full text-blue-300 text-xs font-medium">
            <Lock className="w-3.5 h-3.5" />
            <span>Payee-First Escrow on PayPal Rails</span>
          </div>
          <h1 className="text-3xl sm:text-5xl font-black tracking-tight leading-tight">
            Hold. Verify. Release.
          </h1>
          <p className="text-slate-300 text-base sm:text-lg leading-relaxed">
            Donors give through PayPal checkout. Money is held securely in the platform ledger, audited by multimodal AI against independent invoice evidence, and released <strong>only to the verified hospital, school, or vendor</strong>—never the organizer.
          </p>
          <div className="pt-2 flex flex-wrap gap-3">
            <button
              onClick={handleSeed}
              disabled={seeding}
              className="px-5 py-2.5 bg-paypal-gold text-slate-950 font-bold rounded-xl hover:bg-yellow-400 transition-colors shadow-md flex items-center space-x-2 text-sm disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${seeding ? "animate-spin" : ""}`} />
              <span>{seeding ? "Seeding Demo..." : "Seed Demo Environment"}</span>
            </button>
            <Link
              href="/attack-lab"
              className="px-5 py-2.5 bg-slate-800 hover:bg-slate-700 text-white font-semibold rounded-xl transition-colors border border-slate-700 flex items-center space-x-2 text-sm"
            >
              <Sparkles className="w-4 h-4 text-amber-400" />
              <span>Explore Attack Lab</span>
            </Link>
          </div>
        </div>
      </div>

      {/* Active Campaigns */}
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold tracking-tight text-slate-900">
              Active Campaigns
            </h2>
            <p className="text-sm text-slate-500">
              All campaigns require a verified institutional payee before accepting donations.
            </p>
          </div>
          <button
            onClick={fetchCampaigns}
            className="p-2 text-slate-500 hover:text-slate-900 transition-colors rounded-lg hover:bg-slate-100"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>

        {loading ? (
          <div className="text-center py-12 text-slate-400 font-medium text-sm">
            Loading campaigns from local PostgreSQL...
          </div>
        ) : campaigns.length === 0 ? (
          <div className="text-center py-16 bg-white rounded-2xl border border-dashed border-slate-300 p-8 space-y-4">
            <Building2 className="w-12 h-12 text-slate-300 mx-auto" />
            <div className="space-y-1">
              <h3 className="font-semibold text-slate-800">No campaigns found</h3>
              <p className="text-sm text-slate-500">
                Click &ldquo;Seed Demo Environment&rdquo; above to load verified hospitals and sample campaigns!
              </p>
            </div>
            <button
              onClick={handleSeed}
              className="px-4 py-2 bg-paypal-blue text-white font-semibold rounded-xl text-sm"
            >
              Seed Now
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {campaigns.map((camp) => (
              <div
                key={camp.id}
                className="bg-white rounded-2xl border border-slate-200/80 p-6 shadow-sm hover:shadow-md transition-all flex flex-col justify-between space-y-4 group"
              >
                <div className="space-y-3">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-bold px-2.5 py-1 bg-blue-50 text-paypal-blue rounded-md border border-blue-100 uppercase tracking-wide">
                      {camp.purpose_category}
                    </span>
                    <span className="flex items-center text-slate-500 space-x-1">
                      <Clock className="w-3.5 h-3.5 text-amber-500" />
                      <span>Proof Deadline: 3m</span>
                    </span>
                  </div>

                  <h3 className="font-bold text-lg text-slate-900 group-hover:text-paypal-blue transition-colors line-clamp-1">
                    {camp.title}
                  </h3>

                  <p className="text-sm text-slate-600 line-clamp-2 leading-relaxed">
                    {camp.story}
                  </p>
                </div>

                <div className="space-y-3 pt-2 border-t border-slate-100">
                  <div className="flex justify-between text-xs text-slate-500">
                    <span>Goal: ${camp.goal.toLocaleString()} {camp.currency}</span>
                    <span className="text-emerald-600 font-semibold">Funds Held Securely</span>
                  </div>

                  <Link
                    href={`/campaigns/${camp.id}`}
                    className="w-full py-2.5 px-4 bg-slate-900 hover:bg-paypal-blue text-white font-semibold rounded-xl text-sm transition-colors flex items-center justify-center space-x-1.5 shadow-sm"
                  >
                    <span>View &amp; Donate</span>
                    <ArrowRight className="w-4 h-4" />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
