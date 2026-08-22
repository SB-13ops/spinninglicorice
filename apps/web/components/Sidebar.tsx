const links = [
  ["HOME", "/"],
  ["COLLECTION", "/collection"],
  ["HUNTER", "/hunter"],
  ["SCOUT", "/scout"],
  ["DNA", "/dna"],
  ["PROFILE", "/profile"],
];

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="logo">BURNT JACKET</div>
      <div className="tagline">Your collection. Your hunt. Your music.</div>
      <nav className="nav">
        {links.map(([label, href]) => (
          <a key={href} href={href}>{label}</a>
        ))}
      </nav>
    </aside>
  );
}
