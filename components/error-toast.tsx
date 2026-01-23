"use client"

import type React from "react"

import { useState } from "react"
import { X } from "lucide-react"

interface ErrorToast {
  id: string
  message: string
}

export function ErrorToastProvider({ children }: { children: React.ReactNode }) {
  return <>{children}</>
}

export function useError() {
  const [errors, setErrors] = useState<ErrorToast[]>([])

  const addError = (message: string) => {
    const id = Math.random().toString(36)
    setErrors((prev) => [...prev, { id, message }])
    setTimeout(() => {
      setErrors((prev) => prev.filter((e) => e.id !== id))
    }, 4000)
  }

  return { errors, addError }
}

export function ErrorToastContainer({
  errors,
  removeError,
}: { errors: ErrorToast[]; removeError: (id: string) => void }) {
  return (
    <div className="fixed top-4 left-1/2 transform -translate-x-1/2 z-50 flex flex-col gap-2">
      {errors.map((error) => (
        <div
          key={error.id}
          className="bg-destructive/90 text-destructive-foreground px-4 py-3 rounded-full flex items-center gap-2 shadow-lg animate-in fade-in slide-in-from-top-2 duration-300"
        >
          <span className="text-sm font-medium">{error.message}</span>
          <button onClick={() => removeError(error.id)} className="ml-2 hover:opacity-70 transition-opacity">
            <X className="w-4 h-4" />
          </button>
        </div>
      ))}
    </div>
  )
}
