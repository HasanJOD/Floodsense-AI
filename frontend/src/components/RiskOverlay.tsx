import { useEffect, useRef, useCallback } from 'react';
import { useMap } from 'react-leaflet';
import type { FloodGridResponse } from '../types';

const BAND_COLORS: Record<string, [number, number, number]> = {
  LOW: [34, 197, 94],
  MODERATE: [234, 179, 8],
  HIGH: [249, 115, 22],
  SEVERE: [239, 68, 68],
};

const PANE_NAME = 'riskOverlay';

export default function RiskOverlay({
  grid,
}: {
  grid: FloodGridResponse | null;
}) {
  const map = useMap();
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const offscreenRef = useRef<OffscreenCanvas | null>(null);

  const draw = useCallback(() => {
    if (!grid || !grid.cells.length || !map) return;

    const mapInstance = map;
    const bounds = grid.cells;
    const res = grid.res;

    // Ensure the pane exists at the right z-index.
    if (!mapInstance.getPanes()?.[PANE_NAME]) {
      mapInstance.createPane(PANE_NAME);
      const pane = mapInstance.getPanes()![PANE_NAME];
      pane.style.zIndex = '350';
      canvasRef.current = null;
      offscreenRef.current = null;
    }
    const pane = mapInstance.getPanes()![PANE_NAME];

    const size = mapInstance.getSize();
    const canvasWidth = size.x;
    const canvasHeight = size.y;

    if (!canvasRef.current) {
      canvasRef.current = document.createElement('canvas');
      pane.appendChild(canvasRef.current);
    }
    const canvas = canvasRef.current!;
    canvas.width = canvasWidth;
    canvas.height = canvasHeight;
    canvas.style.position = 'absolute';
    canvas.style.pointerEvents = 'none';

    // Offscreen buffer at half resolution for smoothing.
    const offW = Math.max(1, Math.floor(canvasWidth / 2));
    const offH = Math.max(1, Math.floor(canvasHeight / 2));
    if (!offscreenRef.current) {
      offscreenRef.current = new OffscreenCanvas(offW, offH);
    } else {
      offscreenRef.current.width = offW;
      offscreenRef.current.height = offH;
    }
    const off = offscreenRef.current!;
    const offCtx = off.getContext('2d');
    if (!offCtx) return;

    offCtx.clearRect(0, 0, offW, offH);
    offCtx.imageSmoothingEnabled = false;

    const scaleX = offW / canvasWidth;
    const scaleY = offH / canvasHeight;
    // Approximate cell spacing in container pixels.
    const cellSize = Math.max(
      1,
      Math.floor((canvasWidth / res) * scaleX),
    );

    for (let j = 0; j < res; j++) {
      for (let i = 0; i < res; i++) {
        const cell = bounds[j * res + i];
        if (cell?.flood_probability === null || cell?.flood_probability === undefined) {
          continue;
        }
        const band = (cell.risk_band ?? 'LOW') as string;
        const color = BAND_COLORS[band] ?? BAND_COLORS.LOW;
        offCtx.fillStyle = `rgba(${color[0]}, ${color[1]}, ${color[2]}, 0.55)`;

        const pt = mapInstance.latLngToContainerPoint([cell.lat, cell.lon]);
        const cx = Math.round(pt.x * scaleX);
        const cy = Math.round(pt.y * scaleY);
        const half = Math.max(1, Math.floor(cellSize / 2));
        offCtx.fillRect(cx - half, cy - half, half * 2, half * 2);
      }
    }

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, canvasWidth, canvasHeight);
    ctx.imageSmoothingEnabled = true;
    ctx.filter = 'blur(4px)';
    ctx.drawImage(
      off,
      0, 0, offW, offH,
      0, 0, canvasWidth, canvasHeight,
    );
    ctx.filter = 'none';
  }, [grid, map]);

  const onViewportChange = useCallback(() => {
    void draw();
  }, [draw]);

  useEffect(() => {
    void draw();
  }, [draw]);

  useEffect(() => {
    map.on('moveend', onViewportChange);
    map.on('zoomend', onViewportChange);
    map.on('resize', onViewportChange);
    return () => {
      map.off('moveend', onViewportChange);
      map.off('zoomend', onViewportChange);
      map.off('resize', onViewportChange);
    };
  }, [map, onViewportChange]);

  return null;
}
