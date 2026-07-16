// ISO 3166-1 alpha-2 → numeric-3 mapping for the countries in Independent Commerce inventory.
// Numeric codes are used by world-atlas topojson features (id field).
export const ISO2_TO_NUM = {
  GB: "826", DE: "276", FR: "250", IT: "380", ES: "724", NL: "528", SE: "752",
  NO: "578", DK: "208", FI: "246", PL: "616", PT: "620", CH: "756", AT: "040",
  BE: "056", IE: "372", GR: "300", CZ: "203", RO: "642", HU: "348",
  US: "840", CA: "124", MX: "484",
  BR: "076", AR: "032", CL: "152", CO: "170", PE: "604",
  JP: "392", CN: "156", IN: "356", KR: "410", SG: "702", TH: "764",
  ID: "360", MY: "458", VN: "704", PH: "608",
  AE: "784", SA: "682", IL: "376", TR: "792", QA: "634",
  ZA: "710", NG: "566", EG: "818", KE: "404", MA: "504",
  AU: "036", NZ: "554",
};

export const NUM_TO_ISO2 = Object.fromEntries(
  Object.entries(ISO2_TO_NUM).map(([iso, num]) => [num, iso])
);

// Also match by leading zero variants (topojson sometimes uses "40" instead of "040")
export function normalizeNumeric(id) {
  const s = String(id).padStart(3, "0");
  return s;
}
