console.log("Hawaii Water Quality Card: v1.9.3 Loading...");

const ISLAND_DEFAULTS = {
    "oahu": { lat: 21.4389, lon: -158.0001, zoom: 10 },
    "maui": { lat: 20.7984, lon: -156.3319, zoom: 10 },
    "hawaii": { lat: 19.5667, lon: -155.5230, zoom: 9 },
    "kauai": { lat: 22.0964, lon: -159.5261, zoom: 10 },
    "molokai": { lat: 21.1344, lon: -157.0226, zoom: 11 },
    "lanai": { lat: 20.8166, lon: -156.9273, zoom: 11 },
    "all": { lat: 20.5, lon: -157.5, zoom: 7 }
};

// 1. Editor Class
class HawaiiWaterQualityCardEditor extends HTMLElement {
  set hass(hass) {
    this._hass = hass;
    if (this._form) this._form.hass = hass;
  }

  setConfig(config) {
    this._config = config;
    if (this._form) this._form.data = config;
  }

  connectedCallback() {
    this._render();
  }

  _render() {
    if (this._form) return;

    this.innerHTML = `
      <div id="form-container"></div>
      <div style="margin-top: 10px; font-size: 12px; opacity: 0.7; border-top: 1px solid var(--divider-color); padding-top: 10px;">
          <strong>Visual Editor Active:</strong> Drag or zoom the map to auto-update center/zoom. Toggle "Drag to Align" to update offsets visually.
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

    const form = document.createElement("ha-form");
    form.schema = schema;
    form.computeLabel = (s) => s.label || s.name;
    form.hass = this._hass;
    form.data = this._config;
    
    form.addEventListener("value-changed", (ev) => {
      this.dispatchEvent(new CustomEvent("config-changed", {
        detail: { config: ev.detail.value },
        bubbles: true,
        composed: true
      }));
    });

    this.querySelector("#form-container").appendChild(form);
    this._form = form;
  }
}

if (!customElements.get('custom-hawaii-water-quality-card-editor')) {
    customElements.define('custom-hawaii-water-quality-card-editor', HawaiiWaterQualityCardEditor);
}

// 2. Main Card Class
class HawaiiWaterQualityCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._alignMode = false;
    this._isEditorMode = false;
    this._lastGeoJsonStr = "";
    this._isInternalUpdate = false;
    this._moveTimer = null;
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
          .editor-only { display: none; }
          mwc-button { --mdc-theme-primary: #CD853F; background: white; border-radius: 4px; }
          .leaflet-container { font-family: var(--paper-font-body1_-_font-family); }
        </style>
        <ha-card header="${this.config?.title || 'Hawaii Water Quality'}">
          <div class="controls">
            <div class="info-box" id="count-box">0 Active Areas</div>
            <div class="editor-only" id="editor-controls">
                <mwc-button raised id="align-btn">Drag to Align</mwc-button>
            </div>
          </div>
          <div id="map"></div>
        </ha-card>
      `;
      this.content = this.shadowRoot.getElementById('map');
      this.shadowRoot.getElementById('align-btn').onclick = (e) => {
        e.stopPropagation();
        this._toggleAlignMode();
      };
      this._initMap();
    }
    
    const isEditor = !!this.closest('hui-card-preview') || !!this.closest('hui-card-editor') || !!this.parentElement?.tagName.includes('HUI-CARD-PREVIEW');
    if (isEditor !== this._isEditorMode) {
        this._isEditorMode = isEditor;
        this.shadowRoot.getElementById('editor-controls').style.display = this._isEditorMode ? "flex" : "none";
    }

    this._updateMap();
  }

  _toggleAlignMode() {
    this._alignMode = !this._alignMode;
    const btn = this.shadowRoot.getElementById('align-btn');
    btn.label = this._alignMode ? "STOP ALIGNING" : "Drag to Align";
    
    if (this._alignMode) {
        this._frozenCenter = this.map.getCenter();
        this._frozenOffsetLon = parseFloat(this.config.offset_lon) || 0;
        this._frozenOffsetLat = parseFloat(this.config.offset_lat) || 0;
        this._originalGeoJson = this._hass.states[this.config.entity]?.attributes.geojson;
    } else {
        this._updateMap(true); 
    }
  }

  setConfig(config) {
    const prevEntity = this.config?.entity;
    
    // Type Casting for Config Values
    this.config = {
        entity: config.entity || "",
        title: config.title || "Hawaii Water Quality",
        offset_lon: parseFloat(config.offset_lon) || 0,
        offset_lat: parseFloat(config.offset_lat) || 0,
        default_zoom: parseInt(config.default_zoom) || 9,
        default_lat: parseFloat(config.default_lat) || 21.3069,
        default_lon: parseFloat(config.default_lon) || -157.8583
    };

    // Auto-apply island defaults
    if (this.config.entity && this.config.entity !== prevEntity) {
        const islandKey = this.config.entity.split('_').pop();
        const defaults = ISLAND_DEFAULTS[islandKey] || ISLAND_DEFAULTS["all"];
        if (this.config.default_lat === 21.3069 && this.config.default_lon === -157.8583) {
            this.config.default_lat = defaults.lat;
            this.config.default_lon = defaults.lon;
            this.config.default_zoom = defaults.zoom;
            this._dispatchConfig(this.config);
        }
    }

    if (this.map && !this._isInternalUpdate) {
        const currentCenter = this.map.getCenter();
        const currentZoom = this.map.getZoom();
        
        const centerChanged = Math.abs(currentCenter.lat - this.config.default_lat) > 0.00001 || Math.abs(currentCenter.lng - this.config.default_lon) > 0.00001;
        const zoomChanged = currentZoom !== this.config.default_zoom;

        if (centerChanged || zoomChanged) {
            this.map.setView([this.config.default_lat, this.config.default_lon], this.config.default_zoom);
        }
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

    const onMove = () => {
        if (!this._isEditorMode || this._isInternalUpdate) return;

        const center = this.map.getCenter();
        const newConfig = { ...this.config };

        if (this._alignMode && this._frozenCenter) {
            const dLat = center.lat - this._frozenCenter.lat;
            const dLon = center.lng - this._frozenCenter.lng;
            newConfig.offset_lat = parseFloat((this._frozenOffsetLat + dLat).toFixed(5));
            newConfig.offset_lon = parseFloat((this._frozenOffsetLon + dLon).toFixed(5));
            this._updateAlignmentPreview(newConfig.offset_lon, newConfig.offset_lat);
        } else {
            newConfig.default_lat = parseFloat(center.lat.toFixed(5));
            newConfig.default_lon = parseFloat(center.lng.toFixed(5));
        }

        if (this._moveTimer) clearTimeout(this._moveTimer);
        this._moveTimer = setTimeout(() => this._dispatchConfig(newConfig), 50);
    };

    this.map.on('move', onMove);
    this.map.on('zoomend', () => {
        if (!this._isEditorMode || this._isInternalUpdate) return;
        const newConfig = { ...this.config, default_zoom: this.map.getZoom() };
        this._dispatchConfig(newConfig);
    });

    new ResizeObserver(() => this.map?.invalidateSize()).observe(this.content);
    this._updateMap();
  }

  _updateAlignmentPreview(offLon, offLat) {
    if (!this.geoJsonLayer || !this._hass.states[this.config.entity]?.attributes.geojson) return;
    this.map.removeLayer(this.geoJsonLayer);
    
    const previewGeoJson = JSON.parse(JSON.stringify(this._hass.states[this.config.entity].attributes.geojson));
    const shift = (coords) => {
        if (typeof coords[0] === 'number') return [coords[0] + offLon, coords[1] + offLat];
        return coords.map(c => shift(c));
    };
    previewGeoJson.features.forEach(f => { if (f.geometry?.coordinates) f.geometry.coordinates = shift(f.geometry.coordinates); });

    this.geoJsonLayer = L.geoJSON(previewGeoJson, {
      style: { color: "#CD853F", weight: 3, opacity: 0.8, fillColor: "#D2B48C", fillOpacity: 0.4 },
      pointToLayer: (f, ll) => L.circleMarker(ll, { radius: 12, fillColor: "#CD853F", color: "#000", weight: 1, opacity: 1, fillOpacity: 0.8 })
    }).addTo(this.map);
  }

  _dispatchConfig(newConfig) {
    this._isInternalUpdate = true;
    this.dispatchEvent(new CustomEvent("config-changed", { 
        detail: { config: newConfig },
        bubbles: true,
        composed: true
    }));
    setTimeout(() => { this._isInternalUpdate = false; }, 50);
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

    const offLon = this.config.offset_lon || 0;
    const offLat = this.config.offset_lat || 0;
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
        l.bindPopup(`<strong>${f.properties.name}</strong><br>Type: ${f.properties.type}<br>Posted: ${postedDate}`);
      }
    }).addTo(this.map);

    if (!this._zoomed || force) {
        this.map.setView([this.config.default_lat, this.config.default_lon], this.config.default_zoom);
        this._zoomed = true;
    }
  }

  static getConfigElement() {
    return document.createElement("custom-hawaii-water-quality-card-editor");
  }

  static getStubConfig(hass, entities, entitiesFallback) {
    const entity = entities.find(e => e.startsWith('sensor.hawaii_ocean_water_quality_')) || entitiesFallback[0];
    return { entity: entity || "", title: "Hawaii Water Quality", offset_lon: 0, offset_lat: 0, default_zoom: 9 };
  }

  getCardSize() { return 4; }
}

if (!customElements.get('custom-hawaii-water-quality-card')) {
    customElements.define('custom-hawaii-water-quality-card', HawaiiWaterQualityCard);
}

window.customCards = window.customCards || [];
window.customCards.push({
  type: "custom-hawaii-water-quality-card",
  name: "Hawaii Water Quality Map",
  preview: true,
  description: "Total bidirectional map config tool."
});
