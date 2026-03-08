import type { Metadata } from "next";
import "./globals.css";
import Sidebar from "@/components/sidebar";

export const metadata: Metadata = {
  title: "AgentLedger - AI Expense Management",
  description: "Track, analyze, and optimize your AI spend across providers, models, and teams.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        <div className="flex min-h-screen">
          <Sidebar />
          <main className="ml-60 flex-1 p-6 lg:p-8">{children}</main>
        </div>
      </body>
    </html>
  );
}
