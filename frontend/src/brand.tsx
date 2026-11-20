export function Brand() {
  return <div className="brand">
    <svg viewBox="0 0 32 32" aria-hidden="true">
      <defs><linearGradient id="brand-gradient" x2="1" y2="1"><stop stopColor="#9fe0ff"/><stop offset="1" stopColor="#2f6bff"/></linearGradient></defs>
      <circle cx="16" cy="16" r="15" fill="url(#brand-gradient)"/>
      <path d="M16 7c1 5 3 7 8 9-5 2-7 4-8 9-1-5-3-7-8-9 5-2 7-4 8-9z" fill="#fff"/>
    </svg>
    CommandWise
  </div>
}

