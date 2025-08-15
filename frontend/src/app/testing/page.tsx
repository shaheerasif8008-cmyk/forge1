import { redirect } from "next/navigation";

export default function TestingIndex() {
	redirect("/testing/suites");
}