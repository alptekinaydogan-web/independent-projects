import { useMemo, useState } from "react";
import { ComposableMap, Geographies, Geography, ZoomableGroup } from "react-simple-maps";
import { ISO2_TO_NUM, normalizeNumeric } from "@/lib/countryCodes";

const WORLD_TOPO = "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json";

/**
 * Interactive 2D world map for country selection.
 * Only inventory countries are clickable; other countries are muted/disabled.
 *
 * props:
 *   inventoryCodes: string[] of ISO-2 codes available for targeting
 *   selected: Set<string> of currently-selected ISO-2 codes
 *   onToggle: (iso2) => void
 */
export default function WorldMap({ inventoryCodes, selected, onToggle }) {
  const [hover, setHover] = useState(null);
  const inventoryNumeric = useMemo(() => {
    const set = new Set();
    for (const iso of inventoryCodes) {
      const num = ISO2_TO_NUM[iso];
      if (num) set.add(normalizeNumeric(num));
    }
    return set;
  }, [inventoryCodes]);

  const numToIso = useMemo(() => {
    const m = {};
    for (const iso of inventoryCodes) {
      const num = ISO2_TO_NUM[iso];
      if (num) m[normalizeNumeric(num)] = iso;
    }
    return m;
  }, [inventoryCodes]);

  return (
    <div className="relative w-full imh-card" data-testid="world-map">
      <div className="absolute top-3 left-3 z-10 imh-eyebrow">Global targeting</div>
      <div className="absolute top-3 right-3 z-10 text-[11px] text-[#52525B] font-mono-imh">
        {selected.size} selected · {hover?.name || "—"}
      </div>
      <ComposableMap
        projection="geoEqualEarth"
        projectionConfig={{ scale: 155 }}
        width={980} height={440}
        style={{ background: "#F9F9F6", width: "100%", height: "auto" }}
      >
        <ZoomableGroup center={[10, 10]} zoom={1} minZoom={1} maxZoom={4}>
          <Geographies geography={WORLD_TOPO}>
            {({ geographies }) =>
              geographies.map((geo) => {
                const num = normalizeNumeric(geo.id);
                const iso = numToIso[num];
                const isInInventory = inventoryNumeric.has(num);
                const isSelected = iso && selected.has(iso);
                const isHover = hover?.iso === iso;

                let fill = "#EBEBE6";      // out of inventory
                let stroke = "#D4D4D0";
                if (isInInventory) fill = isSelected ? "#0033A0" : isHover ? "#B7C3E4" : "#FFFFFF";
                if (isInInventory) stroke = "#0A0A0A";

                return (
                  <Geography
                    key={geo.rsmKey}
                    geography={geo}
                    onMouseEnter={() => isInInventory && setHover({ iso, name: geo.properties.name })}
                    onMouseLeave={() => setHover(null)}
                    onClick={() => isInInventory && onToggle(iso)}
                    style={{
                      default: { fill, stroke, strokeWidth: 0.6, outline: "none", cursor: isInInventory ? "pointer" : "not-allowed", transition: "fill 120ms ease" },
                      hover:   { fill, stroke, strokeWidth: 0.6, outline: "none" },
                      pressed: { fill, stroke, strokeWidth: 0.6, outline: "none" },
                    }}
                  />
                );
              })
            }
          </Geographies>
        </ZoomableGroup>
      </ComposableMap>
      <div className="px-4 py-2 border-t border-[#E4E4E1] flex items-center gap-6 text-[11px] text-[#52525B]">
        <span className="flex items-center gap-2"><span className="inline-block w-3 h-3 border border-[#0A0A0A] bg-white" /> Available</span>
        <span className="flex items-center gap-2"><span className="inline-block w-3 h-3 bg-[#0033A0]" /> Selected</span>
        <span className="flex items-center gap-2"><span className="inline-block w-3 h-3 bg-[#EBEBE6] border border-[#D4D4D0]" /> Not in network</span>
      </div>
    </div>
  );
}
