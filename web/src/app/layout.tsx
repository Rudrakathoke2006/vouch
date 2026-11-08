import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import { ShieldCheck, AlertCircle, Eye, Activity, Terminal } from "lucide-react";

export const metadata: Metadata = {
  title: "Vouch | Hold, Verify, Release",
  description: "Escrow-style donation platform running on PayPal rails with AI-powered evidence auditing.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="flex flex-col min-h-screen font-sans antialiased bg-slate-50 text-slate-900">
        {/* Prominent MOCK MODE Banner */}
        <div className="bg-amber-500 text-slate-950 font-semibold px-4 py-1.5 text-xs text-center flex items-center justify-center space-x-2 tracking-wide shadow-sm">
          <AlertCircle className="w-4 h-4 text-slate-950" />
          <span>
            <strong>MOCK MODE ENABLED:</strong> PayPal Sandbox Rails & AI Vision Auditor Emulated | Invariants Deterministically Enforced
          </span>
        </div>

        {/* Navigation Bar */}
        <header className="sticky top-0 z-50 bg-white/95 backdrop-blur border-b border-slate-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
            <Link href="/" className="flex items-center space-x-2.5">
              <div className="bg-paypal-blue text-white p-2 rounded-xl shadow-sm">
                <ShieldCheck className="w-6 h-6" />
              </div>
              <div>
                <span className="font-extrabold text-xl tracking-tight text-slate-900">
                  VOUCH
                </span>
                <span className="ml-1.5 text-xs font-semibold px-2 py-0.5 bg-blue-50 text-paypal-blue rounded-full border border-blue-200">
                  PayPal AI
                </span>
              </div>
            </Link>

            <nav className="flex items-center space-x-6 text-sm font-medium text-slate-600">
              <Link
                href="/"
                className="hover:text-paypal-blue transition-colors flex items-center space-x-1"
              >
                <span>Campaigns</span>
              </Link>
              <Link
                href="/reviewer"
                className="hover:text-paypal-blue transition-colors flex items-center space-x-1"
              >
                <Eye className="w-4 h-4" />
                <span>Reviewer Queue</span>
              </Link>
              <Link
                href="/attack-lab"
                className="hover:text-paypal-blue transition-colors flex items-center space-x-1"
              >
                <Activity className="w-4 h-4" />
                <span>Attack Lab</span>
              </Link>
              <Link
                href="/verify-chain"
                className="hover:text-paypal-blue transition-colors flex items-center space-x-1"
              >
                <Terminal className="w-4 h-4" />
                <span>Verify Chain</span>
              </Link>
            </nav>
          </div>
        </header>

        {/* Main Content */}
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {children}
        </main>

        {/* Footer */}
        <footer className="border-t border-slate-200 bg-white py-6 text-center text-xs text-slate-500">
          <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-4">
            <p>
              Vouch: Hold, Verify, Release &copy; 2026. Built with Google Antigravity for the PayPal AI Hackathon.
            </p>
            <div className="flex items-center space-x-4 font-medium text-slate-600">
              <span>Sandbox Only</span>
              <span>•</span>
              <span>Fictional Institutions</span>
              <span>•</span>
              <a href="https://github.com/vouch/vouch" target="_blank" rel="noreferrer" className="hover:underline">
                MIT License
              </a>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}

