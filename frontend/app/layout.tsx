import type { Metadata } from "next";
import "./style.css";
export const metadata: Metadata = { title:"SentinelX | Business Intelligence",description:"Autonomous AI business intelligence workspace" };
export default function RootLayout({children}:{children:React.ReactNode}){ return <html lang="en"><body>{children}</body></html>; }
