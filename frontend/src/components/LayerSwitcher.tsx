import { LayerGroup, LayersControl, TileLayer } from 'react-leaflet';

const ESRI_ATTRIBUTION =
  'Tiles &copy; <a href="https://www.esri.com/">Esri</a> &mdash; Source: Esri, Earthstar Geographics';
const OSM_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

export default function LayerSwitcher() {
  return (
    <LayersControl position="topright">
      <LayersControl.BaseLayer checked name="Dark streets">
        <TileLayer
          url="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}"
          maxZoom={16}
          attribution={ESRI_ATTRIBUTION}
        />
      </LayersControl.BaseLayer>

      <LayersControl.BaseLayer name="Street map">
        <TileLayer
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
          maxZoom={19}
          attribution={OSM_ATTRIBUTION}
        />
      </LayersControl.BaseLayer>

      <LayersControl.BaseLayer name="Satellite">
        <LayerGroup>
          <TileLayer
            url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
            maxZoom={19}
            attribution={ESRI_ATTRIBUTION}
          />
          <TileLayer
            url="https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}"
            maxZoom={19}
            pane="overlayPane"
          />
        </LayerGroup>
      </LayersControl.BaseLayer>
    </LayersControl>
  );
}
