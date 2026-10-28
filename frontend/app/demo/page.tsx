import { redirect } from "next/navigation";

/** Legacy public sample URL: direct visitors into the real owner workflow. */
export default function DemoRedirect() {
  redirect("/");
}
