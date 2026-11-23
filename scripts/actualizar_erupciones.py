#!/usr/bin/env python3
"""
Descarga las erupciones en curso del Global Volcanism Program (Smithsonian Institution)
y escribe data/erupciones.json para el mapa «Volcanes del mundo».

Fuente: servicio WFS del GVP (capas E3WebApp_Eruptions1960 y Smithsonian_VOTW_Holocene_Volcanoes),
los mismos datos que alimentan https://volcano.si.edu/gvp_currenteruptions.cfm

Solo usa la biblioteca estándar de Python. Uso:  python3 scripts/actualizar_erupciones.py
"""
import json, os, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone

WFS = "https://webservices.volcano.si.edu/geoserver/GVP-VOTW/ows"
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "erupciones.json")

PAISES = {
    "Indonesia": "Indonesia", "Japan": "Japón", "United States": "Estados Unidos", "Russia": "Rusia",
    "Italy": "Italia", "Iceland": "Islandia", "Ecuador": "Ecuador", "Colombia": "Colombia", "Mexico": "México",
    "Guatemala": "Guatemala", "Nicaragua": "Nicaragua", "Costa Rica": "Costa Rica", "El Salvador": "El Salvador",
    "Chile": "Chile", "Argentina": "Argentina", "Peru": "Perú", "Bolivia": "Bolivia",
    "Papua New Guinea": "Papúa Nueva Guinea", "Vanuatu": "Vanuatu", "Philippines": "Filipinas", "Tonga": "Tonga",
    "New Zealand": "Nueva Zelanda", "DR Congo": "R. D. del Congo", "Ethiopia": "Etiopía", "Tanzania": "Tanzania",
    "France": "Francia", "Antarctica": "Antártida", "Australia": "Australia", "Solomon Islands": "Islas Salomón",
    "India": "India", "Spain": "España", "Portugal": "Portugal", "Greece": "Grecia", "Turkey": "Turquía",
    "Eritrea": "Eritrea", "Cameroon": "Camerún", "Comoros": "Comoras", "United Kingdom": "Reino Unido",
    "Canada": "Canadá", "China": "China", "North Korea": "Corea del Norte", "South Korea": "Corea del Sur",
    "Saudi Arabia": "Arabia Saudita", "Yemen": "Yemen", "Kenya": "Kenia", "Uganda": "Uganda", "Rwanda": "Ruanda",
    "Cape Verde": "Cabo Verde", "Norway": "Noruega", "Montserrat": "Montserrat", "Saint Vincent and the Grenadines": "San Vicente",
    "Grenada": "Granada", "Panama": "Panamá", "Honduras": "Honduras", "Iran": "Irán", "Armenia": "Armenia", "Georgia": "Georgia",
    "Taiwan": "Taiwán", "Fiji": "Fiyi", "Samoa": "Samoa", "Undersea Features": "Fondo marino",
}
TIPOS = {
    "Stratovolcano": "Estratovolcán", "Stratovolcano(es)": "Estratovolcán", "Shield": "Volcán en escudo",
    "Shield(s)": "Volcán en escudo", "Shield(pyroclastic)": "Escudo piroclástico", "Caldera": "Caldera",
    "Caldera(s)": "Caldera", "Complex": "Complejo volcánico", "Compound": "Volcán compuesto",
    "Volcanic field": "Campo volcánico", "Lava dome(s)": "Domo de lava", "Lava dome": "Domo de lava",
    "Pyroclastic cone(s)": "Cono de escoria", "Pyroclastic cone": "Cono de escoria", "Fissure vent(s)": "Fisura",
    "Fissure vent": "Fisura", "Crater rows": "Fila de cráteres", "Lava cone": "Cono de lava", "Lava cone(s)": "Cono de lava",
    "Submarine": "Volcán submarino", "Explosion crater(s)": "Cráter de explosión", "Maar(s)": "Maar", "Cone": "Cono",
    "Tuff cone(s)": "Cono de toba", "Tuff ring(s)": "Anillo de toba",
}

def wfs(layer, cql=None, props=None):
    q = {"service": "WFS", "version": "1.0.0", "request": "GetFeature",
         "typeName": layer, "outputFormat": "application/json"}
    if cql: q["CQL_FILTER"] = cql
    if props: q["propertyName"] = ",".join(props)
    url = WFS + "?" + urllib.parse.urlencode(q)
    last = None
    for intento in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "mapa-volcanes (eduardoluis.blog)"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return [f["properties"] for f in json.load(r)["features"]]
        except Exception as e:      # reintenta ante fallas pasajeras del servidor
            last = e; time.sleep(5 * (intento + 1))
    raise SystemExit(f"No se pudo consultar el GVP ({layer}): {last}")

def fecha(s):
    """'20261115' -> '2026-11-15'; '20260900' -> '2026-09'; vacío -> None"""
    s = (s or "").strip()
    if len(s) != 8 or not s.isdigit(): return None
    y, m, d = s[:4], s[4:6], s[6:]
    if m == "00": return y
    if d == "00": return f"{y}-{m}"
    return f"{y}-{m}-{d}"

def nombre(n):
    """'Lengai, Ol Doinyo' -> 'Ol Doinyo Lengai'"""
    if ", " in n:
        a, b = n.split(", ", 1)
        return f"{b} {a}"
    return n

def pais(p):
    return " / ".join(PAISES.get(x.strip(), x.strip()) for x in (p or "").split("-")) or "—"

def pais_en(p):
    return " / ".join(x.strip() for x in (p or "").split("-") if x.strip()) or "—"

def tipo_en(t):
    t = (t or "").replace("(es)", "").replace("(s)", "").replace("(pyroclastic)", " (pyroclastic)").strip()
    return {"Shield": "Shield volcano", "Complex": "Volcanic complex", "Compound": "Compound volcano",
            "Submarine": "Submarine volcano", "Fissure vent": "Fissure vent"}.get(t, t[:1].upper() + t[1:] if t else "—")

def main():
    erup = wfs("GVP-VOTW:E3WebApp_Eruptions1960", "ContinuingEruption='True'")
    if len(erup) < 5:
        raise SystemExit(f"Respuesta sospechosa del GVP: solo {len(erup)} erupciones en curso")
    nums = sorted({e["VolcanoNumber"] for e in erup})
    info = {}
    for i in range(0, len(nums), 60):
        lote = nums[i:i + 60]
        for v in wfs("GVP-VOTW:Smithsonian_VOTW_Holocene_Volcanoes",
                     f"Volcano_Number IN ({','.join(map(str, lote))})",
                     ["Volcano_Number", "Volcano_Name", "Country", "Primary_Volcano_Type", "Elevation", "Latitude", "Longitude"]):
            info[v["Volcano_Number"]] = v
    salida = []
    for e in erup:
        v = info.get(e["VolcanoNumber"], {})
        salida.append({
            "gvp": e["VolcanoNumber"],
            "nombre": nombre(v.get("Volcano_Name") or e["VolcanoName"]),
            "pais": pais(v.get("Country")),
            "tipo": TIPOS.get(v.get("Primary_Volcano_Type"), v.get("Primary_Volcano_Type") or "—"),
            "pais_en": pais_en(v.get("Country")),
            "tipo_en": tipo_en(v.get("Primary_Volcano_Type")),
            "altitud": v.get("Elevation"),
            "lat": v.get("Latitude", e.get("LatitudeDecimal")),
            "lon": v.get("Longitude", e.get("LongitudeDecimal")),
            "inicio": fecha(e.get("StartDate")),
            "ultima_actividad": fecha(e.get("EndDate")),
            "iev": e.get("ExplosivityIndexMax"),
        })
    salida.sort(key=lambda x: (x["ultima_actividad"] or "", x["inicio"] or ""), reverse=True)
    datos = {
        "fuente": "Global Volcanism Program, Smithsonian Institution",
        "fuente_url": "https://volcano.si.edu/gvp_currenteruptions.cfm",
        "consultado": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total": len(salida),
        "erupciones": salida,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(datos, fh, ensure_ascii=False, indent=1)
    print(f"Listo: {len(salida)} erupciones en curso -> {os.path.normpath(OUT)}")

if __name__ == "__main__":
    main()
