import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import ConfigureAmplifyClientSide from "@/components/ConfigureAmplify";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "AI Chat Assistant",
  description: "AI-powered chat assistant with AWS Bedrock",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="sk">
      <body className={inter.className}>
        <ConfigureAmplifyClientSide />
        {children}
      </body>
    </html>
  );
}
