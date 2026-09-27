<script 
    type="module" 
    src="https://ajax.googleapis.com/ajax/libs/model-viewer/4.0.0/model-viewer.min.js">
</script>
## 3D Models
### Populated
<fullscreen-container>
    <model-viewer
        src="/alidade/alidade-hw/3d/alidade.glb"
        alt="Interactive 3D view of the PCB"
        camera-controls
        environment-image="neutral"
        tone-mapping="agx"
        render-scale="1"
        exposure="0.45"
        shadow-intensity="0.3"
        shadow-softness="1"
        camera-orbit="0deg 60deg auto">
    </model-viewer>
</fullscreen-container>

## Layout
<fullscreen-container>
    <kicanvas-embed controls="full" theme="gruvbox" controlslist="nodownload">
        <kicanvas-source src="/alidade/alidade-hw/pcb/alidade.kicad_pcb"></kicanvas-source>
    </kicanvas-embed>
</fullscreen-container>
## PCB Statistics
<pcb-stats data-src="/alidade/alidade-hw/pcb/stats.json"></drc-table>
## DRC
<drc-table data-src="/alidade/alidade-hw/pcb/drc.json"></drc-table>
