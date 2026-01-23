"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { Home, MessageSquare, ClipboardList, User, Settings } from "lucide-react"

export function AdultTabNav() {
  const pathname = usePathname()

  const tabs = [
    { href: "/adult-listings", icon: Home, label: "Listings" },
    { href: "/adult-messages", icon: MessageSquare, label: "Messages" },
    { href: "/create-quest", icon: ClipboardList, label: "Create" },
    { href: "/adult-profile", icon: User, label: "Profile" },
    { href: "/adult-settings", icon: Settings, label: "Settings" },
  ]

  return (
    <div className="fixed bottom-0 left-1/2 transform -translate-x-1/2 w-full max-w-md border-t bg-background z-50">
      <div className="flex justify-around items-center">
        {tabs.map((tab, index) => {
          const isActive = pathname === tab.href || pathname.startsWith(tab.href + "/")
          return (
            <Link
              key={tab.href}
              href={tab.href}
              className={`flex-1 flex flex-col items-center gap-1 py-3 ${
                index < tabs.length - 1 ? "border-r" : ""
              } ${isActive ? "text-primary" : "text-muted-foreground hover:bg-muted/50"}`}
            >
              <tab.icon className="w-6 h-6" />
              <span className="text-xs font-medium">{tab.label}</span>
            </Link>
          )
        })}
      </div>
    </div>
  )
}
