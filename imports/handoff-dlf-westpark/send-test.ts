/**
 * Test send — DLF Westpark v2
 * Copy into web/emails/ alongside dlf-westpark-v2.tsx, then:
 *
 *   RESEND_API_KEY=re_xxx npx tsx emails/send-test.ts
 *
 * Optional env:
 *   RESEND_FROM  — verified sender, e.g. "Padmini Jain <padmini@realdealhousing.com>"
 *                  (defaults to Resend's onboarding sender, which only delivers
 *                   to the email on your Resend account)
 *   TEST_TO      — recipient (defaults to hbanthiya@gmail.com)
 *   TEST_NAME    — first name for the greeting (omit to test the "Hello," fallback)
 */
import { Resend } from "resend";
import { render } from "@react-email/render";
import DlfWestparkEmail from "./dlf-westpark-v2";

const resend = new Resend(process.env.RESEND_API_KEY);

(async () => {
  if (!process.env.RESEND_API_KEY) {
    console.error("Set RESEND_API_KEY first.");
    process.exit(1);
  }

  let html = await render(
    DlfWestparkEmail({
      firstName: process.env.TEST_NAME,          // undefined -> "Hello,"
      unsubscribeUrl: "https://realdealhousing.com", // no merge tag in a test send
    })
  );

  const { data, error } = await resend.emails.send({
    from: process.env.RESEND_FROM ?? "Real Deal Housing <onboarding@resend.dev>",
    to: process.env.TEST_TO ?? "hbanthiya@gmail.com",
    subject: "[TEST] Phase 2 is open — DLF Westpark, Andheri West",
    html,
  });

  if (error) {
    console.error("Send failed:", error);
    process.exit(1);
  }
  console.log("Sent. id:", data?.id);
  console.log("Check hbanthiya@gmail.com — light AND dark mode, phone + desktop.");
})();
