import "./globals.css";
import { AuthProvider } from "../lib/auth";
import AppShell from "../components/AppShell";
import Disclosure from "../components/Disclosure";

export const metadata = {
  title: "SpinningLicorice",
  description: "Your collection. Your hunt. Your music.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        {/* Loaded at runtime in the browser, not at Next.js build time — this
            keeps the build itself free of any dependency on reaching Google's
            font servers. */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Caprasimo&family=Figtree:wght@400;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        <AuthProvider>
          <AppShell>{children}</AppShell>
          <Disclosure />
        </AuthProvider>
      </body>
    </html>
  );
}
