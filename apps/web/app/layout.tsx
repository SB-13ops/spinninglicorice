import "./globals.css";
import { AuthProvider } from "../lib/auth";
import AppShell from "../components/AppShell";
import Disclosure from "../components/Disclosure";

export const metadata = {
  title: "Burnt Jacket",
  description: "Your collection. Your hunt. Your music.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>
          <AppShell>{children}</AppShell>
          <Disclosure />
        </AuthProvider>
      </body>
    </html>
  );
}
