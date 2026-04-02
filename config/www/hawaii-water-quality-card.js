console.log("Hawaii Water Quality Card: v2.2.1 Loading...");

const ISLAND_DEFAULTS = {
    "oahu": { default_lat: 21.4389, default_lon: -158.0001, default_zoom: 10 },
    "maui": { default_lat: 20.7984, default_lon: -156.3319, default_zoom: 10 },
    "hawaii": { default_lat: 19.5667, default_lon: -155.5230, default_zoom: 9 },
    "kauai": { default_lat: 22.0964, default_lon: -159.5261, default_zoom: 10 },
    "molokai": { default_lat: 21.1344, default_lon: -157.0226, default_zoom: 11 },
    "lanai": { default_lat: 20.8166, default_lon: -156.9273, default_zoom: 11 },
    "all": { default_lat: 20.5, default_lon: -157.5, default_zoom: 7 }
};

// 1. Editor Class
class HawaiiWaterQualityCardEditor extends HTMLElement {
  set hass(hass) {
    this._hass = hass;
    if (this._form) this._form.hass = hass;
  }

  setConfig(config) {
    this._config = config;
    if (this._form) {
        this._form.data = { ...config };
    }
  }

  connectedCallback() {
    this._render();
  }

  _render() {
    if (this._form) return;

    this.innerHTML = `
      <div id="form-container"></div>
      <div style="margin-top: 10px; font-size: 12px; opacity: 0.7; border-top: 1px solid var(--divider-color); padding-top: 10px;">
          <strong>Visual Editor:</strong> Use these fields to adjust the map. Click highlights on the map to see their exact coordinates.
      </div>
    `;

    const schema = [
      { name: "entity", selector: { entity: { domain: "sensor" } } },
      { name: "title", selector: { text: {} } },
      { name: "default_lat", label: "Center Lat", selector: { number: { mode: "box", step: 0.00001 } } },
      { name: "default_lon", label: "Center Lon", selector: { number: { mode: "box", step: 0.00001 } } },
      { name: "default_zoom", label: "Zoom", selector: { number: { mode: "box", min: 1, max: 20 } } },
      { name: "offset_lat", label: "Offset Lat", selector: { number: { mode: "box", step: 0.00001 } } },
      { name: "offset_lon", label: "Offset Lon", selector: { number: { mode: "box", step: 0.00001 } } }
    ];

    this._form = document.createElement("ha-form");
    this._form.schema = schema;
    this._form.computeLabel = (s) => s.label || s.name;
    this._form.hass = this._hass;
    this._form.data = { ...this._config };
    
    this._form.addEventListener("value-changed", (ev) => {
      const newConfig = ev.detail.value;
      const oldEntity = this._config?.entity;
      
      if (newConfig.entity && newConfig.entity !== oldEntity) {
          const entityId = newConfig.entity.toLowerCase();
          let islandKey = "all";
          for (const k of Object.keys(ISLAND_DEFAULTS)) {
              if (entityId.includes(k)) { islandKey = k; break; }
          }
          const d = ISLAND_DEFAULTS[islandKey];
          newConfig.default_lat = d.default_lat;
          newConfig.default_lon = d.default_lon;
          newConfig.default_zoom = d.default_zoom;
      }

      this.dispatchEvent(new CustomEvent("config-changed", {
        detail: { config: newConfig },
        bubbles: true,
        composed: true
      }));
    });

    this.querySelector("#form-container").appendChild(this._form);
  }
}

if (!customElements.get('hawaii-water-quality-card-editor')) {
    customElements.define('hawaii-water-quality-card-editor', HawaiiWaterQualityCardEditor);
}

// 2. Main Card Class
class HawaiiWaterQualityCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._lastGeoJsonStr = "";
  }

  set hass(hass) {
    this._hass = hass;
    if (!this.content) {
      this.shadowRoot.innerHTML = `
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <style>
          ha-card { height: 100%; overflow: hidden; display: flex; flex-direction: column; position: relative; }
          #map { height: 400px; width: 100%; background: #f8f9fa; position: relative; overflow: hidden; }
          .controls { position: absolute; top: 10px; right: 10px; z-index: 1000; display: flex; flex-direction: column; gap: 5px; align-items: flex-end; }
          .info-box { 
            background: rgba(255, 255, 255, 0.9); padding: 8px; border-radius: 4px; 
            font-family: var(--paper-font-body1_-_font-family); font-size: 12px; box-shadow: 0 2px 5px rgba(0,0,0,0.2);
            pointer-events: none; border-left: 4px solid #CD853F;
          }
          .leaflet-container { font-family: var(--paper-font-body1_-_font-family); }
        </style>
        <ha-card header="${this.config?.title || 'Hawaii Water Quality'}">
          <div class="controls">
            <div class="info-box" id="count-box">0 Active Areas</div>
          </div>
          <div id="map"></div>
        </ha-card>
      `;
      this.content = this.shadowRoot.getElementById('map');
      this._initMap();
    }
    this._updateMap();
  }

  setConfig(config) {
    if (!config.entity) {
      this.config = config;
      return;
    }

    const entityId = config.entity.toLowerCase();
    let islandKey = "all";
    for (const k of Object.keys(ISLAND_DEFAULTS)) {
        if (entityId.includes(k)) { islandKey = k; break; }
    }
    const d = ISLAND_DEFAULTS[islandKey];

    this.config = {
        title: "Hawaii Water Quality",
        default_lat: d.default_lat,
        default_lon: d.default_lon,
        default_zoom: d.default_zoom,
        ...config,
        offset_lon: parseFloat(config.offset_lon) || 0,
        offset_lat: parseFloat(config.offset_lat) || 0
    };

    // Ensure numeric types
    this.config.default_lat = parseFloat(this.config.default_lat);
    this.config.default_lon = parseFloat(this.config.default_lon);
    this.config.default_zoom = parseInt(this.config.default_zoom);

    if (this.map) {
        this.map.setView([this.config.default_lat, this.config.default_lon], this.config.default_zoom);
        this._updateMap(true);
    }
  }

  _initMap() {
    if (this.map) return;
    if (typeof L === 'undefined') {
      const script = document.createElement('script');
      script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
      script.onload = () => this._createMapInstance();
      document.head.appendChild(script);
    } else {
      this._createMapInstance();
    }
  }

  _createMapInstance() {
    if (!this.content || this.map) return;
    this.map = L.map(this.content).setView([this.config.default_lat, this.config.default_lon], this.config.default_zoom);
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png').addTo(this.map);
    new ResizeObserver(() => this.map?.invalidateSize()).observe(this.content);
    this._updateMap();
  }

  _updateMap(force = false) {
    if (!this.map || !this._hass || !this.config.entity) return;
    const state = this._hass.states[this.config.entity];
    if (!state) return;

    this.shadowRoot.getElementById('count-box').innerText = `${state.state} Active Areas`;
    
    const geojson = state.attributes.geojson;
    const geojsonStr = JSON.stringify(geojson) + JSON.stringify(this.config.offset_lon) + JSON.stringify(this.config.offset_lat);
    
    if (geojsonStr === this._lastGeoJsonStr && !force) return;
    this._lastGeoJsonStr = geojsonStr;

    if (!geojson) return;
    if (this.geoJsonLayer) this.map.removeLayer(this.geoJsonLayer);

    const offLon = parseFloat(this.config.offset_lon) || 0;
    const offLat = parseFloat(this.config.offset_lat) || 0;
    const cardGeoJson = JSON.parse(JSON.stringify(geojson));
    
    const shiftCoords = (coords) => {
        if (typeof coords[0] === 'number') return [coords[0] + offLon, coords[1] + offLat];
        return coords.map(c => shiftCoords(c));
    };
    cardGeoJson.features.forEach(f => {
        if (f.geometry?.coordinates) f.geometry.coordinates = shiftCoords(f.geometry.coordinates);
    });

    this.geoJsonLayer = L.geoJSON(cardGeoJson, {
      style: { color: "#CD853F", weight: 3, opacity: 0.8, fillColor: "#D2B48C", fillOpacity: 0.4 },
      pointToLayer: (f, ll) => L.circleMarker(ll, { radius: 12, fillColor: "#CD853F", color: "#000", weight: 1, opacity: 1, fillOpacity: 0.8 }),
      onEachFeature: (f, l) => {
        const postedDate = f.properties.posted_date ? new Date(f.properties.posted_date).toLocaleString() : "Unknown";
        const coords = f.geometry.type === 'Point' 
            ? `${f.geometry.coordinates[1].toFixed(5)}, ${f.geometry.coordinates[0].toFixed(5)}`
            : "Shape";
        l.bindPopup(`<strong>${f.properties.name}</strong><br>Type: ${f.properties.type}<br>Posted: ${postedDate}<br>Coords: ${coords}`);
      }
    }).addTo(this.map);
  }

  static getConfigElement() {
    return document.createElement("hawaii-water-quality-card-editor");
  }

  static getStubConfig(hass, entities, entitiesFallback) {
    const entity = entities.find(e => e.startsWith('sensor.hawaii_ocean_water_quality_')) || entitiesFallback[0];
    let islandKey = "all";
    if (entity) {
        const entityId = entity.toLowerCase();
        for (const k of Object.keys(ISLAND_DEFAULTS)) {
            if (entityId.includes(k)) { islandKey = k; break; }
        }
    }
    const d = ISLAND_DEFAULTS[islandKey];
    return { 
        entity: entity || "", 
        title: "Hawaii Water Quality", 
        offset_lon: 0, 
        offset_lat: 0, 
        default_lat: d.default_lat,
        default_lon: d.default_lon,
        default_zoom: d.default_zoom 
    };
  }

  getCardSize() { return 4; }
}

if (!customElements.get('hawaii-water-quality-card')) {
    customElements.define('hawaii-water-quality-card', HawaiiWaterQualityCard);
}

window.customCards = window.customCards || [];
window.customCards.push({
  type: "hawaii-water-quality-card",
  name: "Hawaii Water Quality Map",
  preview: true,
  description: "Manual configuration map card."
});
