import type { Metadata } from "next";
import "./style.css";
import "./product.css";
import "./research.css";
export const metadata: Metadata = { title:"SentinelX | Evidence to Action",description:"Research your business with traceable evidence, design AI-assisted improvements, approve changes, and verify published results." };
export default function RootLayout({children}:{children:React.ReactNode}){ return <html lang="en"><body>{children}</body></html>; }
