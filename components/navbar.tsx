"use client"

import Link from "next/link"

export default function Navbar() {
  return (
    <nav className="sticky top-0 z-50 w-full bg-white border-b border-black">
      <div className="max-w-6xl mx-auto px-4 md:px-8 h-16 flex items-center justify-between">
        <Link href="/" className="text-2xl font-serif font-bold hover:opacity-70 transition-opacity">
          Farm One
        </Link>

        <div className="flex items-center gap-8">
          <Link
            href="/about"
            className="text-sm font-medium transition-colors hover:text-gray-700 underline-offset-4 hover:underline"
          >
            About
          </Link>
          <Link
            href="/farmbot"
            className="text-sm font-medium transition-colors hover:text-gray-700 underline-offset-4 hover:underline"
          >
            FarmBot
          </Link>
        </div>
      </div>
    </nav>
  )
}
