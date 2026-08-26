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
        {/* Applies a saved dark-mode choice before first paint, so there's no
            flash of the light theme for people who picked dark. */}
        <script
          dangerouslySetInnerHTML={{
            __html:
              "try{if(localStorage.getItem('spinninglicorice.theme')==='dark'){document.documentElement.setAttribute('data-theme','dark');}}catch(e){}",
          }}
        />
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
