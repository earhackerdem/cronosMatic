import { createFileRoute, redirect } from "@tanstack/react-router"
import { z } from "zod"
import { persistGoogleToken } from "@/hooks/useAuth"

const searchSchema = z.object({
  access_token: z.string().optional(),
  error: z.string().optional(),
})

export const Route = createFileRoute("/auth/callback")({
  validateSearch: searchSchema,
  beforeLoad: ({ search, context }) => {
    if (search.access_token) {
      persistGoogleToken(search.access_token, context.queryClient)
      throw redirect({ to: "/" })
    }
    if (search.error) {
      throw redirect({ to: "/login", search: { authError: "google" } })
    }
    throw redirect({ to: "/login" })
  },
  component: () => null,
})
