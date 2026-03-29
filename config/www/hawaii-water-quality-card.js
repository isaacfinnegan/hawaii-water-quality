class HawaiiWaterQualityCard extends HTMLElement {
  set hass(hass) {
    this._hass = hass;
    if (!this.content) {
      this.innerHTML = `
        <ha-card header="${this.config.title || 'Hawaii Water Quality'}">
          <div id="map" style="height: 400px; width: 100%; z-index: 0;"></div>
          <style>
            #map { background: #f8f9fa; }
            .leaflet-container { font-family: var(--paper-font-body1_-_font-family); }
          </style>
        </ha-card>
      `;
      this.content = this.querySelector('#map');
      this._initMap();
    }
    this._updateMap();
  }

  setConfig(config) {
    if (!config.entity) {
      throw new Error('You need to define an entity');
    }
    this.config = config;
  }

  _initMap() {
    if (this.map) return;

    // Load Leaflet CSS
    if (!document.getElementById('leaflet-css')) {
      const link = document.createElement('link');
      link.id = 'leaflet-css';
      link.rel = 'stylesheet';
      link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
      document.head.appendChild(link);
    }

    // Load Leaflet JS
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
    this.map = L.map(this.content).setView([21.3069, -157.8583], 9);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap contributors'
    }).addTo(this.map);
    this._updateMap();
  }

  _updateMap() {
    if (!this.map || !this._hass) return;

    const state = this._hass.states[this.config.entity];
    if (!state || !state.attributes.geojson) return;

    const geojson = state.attributes.geojson;

    // Clear old layers
    if (this.geoJsonLayer) {
      this.map.removeLayer(this.geoJsonLayer);
    }

    this.geoJsonLayer = L.geoJSON(geojson, {
      style: function(feature) {
        return {
          color: "#8B4513", // SaddleBrown
          weight: 2,
          opacity: 0.8,
          fillColor: "#D2B48C", // Tan
          fillOpacity: 0.4
        };
      },
      onEachFeature: (feature, layer) => {
        layer.bindPopup(`
          <strong>${feature.properties.name}</strong><br>
          Type: ${feature.properties.type}<br>
          Status: ${feature.properties.status}<br>
          Posted: ${new Date(feature.properties.posted_date).toLocaleDateString()}
        `);
      },
      pointToLayer: (feature, latlng) => {
        return L.circleMarker(latlng, {
          radius: 8,
          fillColor: "#8B4513",
          color: "#000",
          weight: 1,
          opacity: 1,
          fillOpacity: 0.8
        });
      }
    }).addTo(this.map);

    // Zoom to fit if requested or first load
    if (geojson.features.length > 0 && (!this._zoomed || this.config.auto_zoom)) {
      this.map.fitBounds(this.geoJsonLayer.getBounds(), { padding: [20, 20] });
      this._zoomed = true;
    }
  }

  getCardSize() {
    return 4;
  }
}

customElements.define('hawaii-water-quality-card', HawaiiWaterQualityCard);
