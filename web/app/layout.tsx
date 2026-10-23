import type { Metadata } from "next"
import "./styles.css"

export const metadata: Metadata = { title: "Haven — a little room to breathe", description: "A private space for reflection and support." }

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>
}
