"use client"

import { useEffect } from "react"
import { initializeAuth } from "@/stores/auth"

export function AuthInitializer() {
  useEffect(() => {
    initializeAuth()
  }, [])

  return null
}