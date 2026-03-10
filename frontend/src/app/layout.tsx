import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'TradingAgents Dashboard',
  description: 'Multi-Agent LLM Financial Trading Framework',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <div className="min-h-screen bg-background">
          <header className="border-b">
            <div className="container flex h-16 items-center px-4">
              <a href="/" className="flex items-center space-x-2">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  className="h-6 w-6"
                >
                  <path d="M12 2L2 7l10 5 10-5-10-5z" />
                  <path d="M2 17l10 5 10-5" />
                  <path d="M2 12l10 5 10-5" />
                </svg>
                <span className="font-bold text-xl">TradingAgents</span>
              </a>
              <nav className="flex items-center space-x-4 ml-6">
                <a href="/" className="text-sm font-medium hover:text-primary">
                  Dashboard
                </a>
                <a href="/proposals" className="text-sm font-medium text-muted-foreground hover:text-primary">
                  Proposals
                </a>
                <a href="/positions" className="text-sm font-medium text-muted-foreground hover:text-primary">
                  Positions
                </a>
                <a href="/trades" className="text-sm font-medium text-muted-foreground hover:text-primary">
                  Trade History
                </a>
                <a href="/settings" className="text-sm font-medium text-muted-foreground hover:text-primary">
                  Settings
                </a>
              </nav>
            </div>
          </header>
          <main className="container px-4 py-6">
            {children}
          </main>
        </div>
      </body>
    </html>
  )
}