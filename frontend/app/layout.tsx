import type { Metadata } from "next";
import "./style.css";
import "./product.css";
import "./research.css";
export const metadata: Metadata = { title:"SentinelX | Your Business Workspace",description:"Create campaigns, review product photos, design visuals and manage landing pages in one workspace." };
export default function RootLayout({children}:{children:React.ReactNode}){ return <html lang="en"><body>{children}</body></html>; }
