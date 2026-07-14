export const REGIONS = [
  "Europe", "North America", "South America", "Asia",
  "Middle East", "Africa", "Oceania",
];

export function usd(n) {
  const num = Number(n) || 0;
  return num.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
}

export function usdPrecise(n) {
  const num = Number(n) || 0;
  return num.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 });
}

export function num(n) {
  return (Number(n) || 0).toLocaleString("en-US");
}
