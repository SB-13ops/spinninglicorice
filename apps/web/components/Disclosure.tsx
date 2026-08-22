/**
 * Site-wide disclosure shown in small print at the bottom of every page.
 * Rendered in the root layout (outside AppShell) so it appears on the app,
 * the login/callback pages, and the anonymous public shared views alike.
 */
export default function Disclosure() {
  return (
    <div className="ai-disclosure" role="contentinfo">
      This site was created by AI. Information may be inaccurate — please do your
      own research before purchasing anything.
    </div>
  );
}
