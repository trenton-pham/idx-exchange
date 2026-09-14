import {useEffect,useRef,useState} from 'react';
import * as maplibregl from 'maplibre-gl';
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url';
import type {FeatureCollection} from 'geojson';
import {LocateFixed,MapPin} from 'lucide-react';
import {money,number,type MapData} from './api';
import 'maplibre-gl/dist/maplibre-gl.css';
maplibregl.setWorkerUrl(workerUrl);

const bounds:maplibregl.LngLatBoundsLike=[[-124.5,32.45],[-114.05,42.05]];
const colors=['#dcecee','#b2d4d7','#78afb8','#488b9c','#2f687f','#23496b'];
export default function MarketMap({data,selected,onSelect}:{data?:MapData;selected:string;onSelect:(value:string)=>void}){
 const root=useRef<HTMLDivElement>(null); const map=useRef<maplibregl.Map|null>(null);const choose=useRef(onSelect);choose.current=onSelect;
 const [ready,setReady]=useState(false);const [loaded,setLoaded]=useState(false);const [error,setError]=useState(''); const [hover,setHover]=useState('');
 useEffect(()=>{if(!root.current)return;
  let instance:maplibregl.Map;
  try{instance=new maplibregl.Map({container:root.current,style:{version:8,sources:{},layers:[{id:'ground',type:'background',paint:{'background-color':'#edf3f6'}}]},bounds,fitBoundsOptions:{padding:28},attributionControl:false,dragRotate:false,touchPitch:false,scrollZoom:false});}catch{setError('Your browser cannot display the map. Use the area filters above to explore the same data.');return;}
  map.current=instance;instance.addControl(new maplibregl.NavigationControl({showCompass:false}),'top-right');instance.on('load',()=>setReady(true));
  instance.on('error',()=>setError('The map could not load. The area filters and data table remain available.'));
  const resize=new ResizeObserver(()=>instance.resize());resize.observe(root.current);
  return()=>{resize.disconnect();instance.remove();map.current=null;};
 },[]);
 useEffect(()=>{const instance=map.current;setLoaded(false);setHover('');if(!instance||!ready)return;
  if(!data){for(const id of ['density','outline','areas'])if(instance.getLayer(id))instance.setLayoutProperty(id,'visibility','none');return;}
  let cancelled=false;
  fetch(`/geo/${data.level==='county'?'counties':'zips'}.geojson`).then(r=>{if(!r.ok)throw Error();return r.json();}).then((geo:FeatureCollection)=>{
   if(cancelled)return;const lookup=new Map(data.areas.map(a=>[a.id,a]));const values=data.areas.map(a=>a.value).filter((n):n is number=>n!=null).sort((a,b)=>a-b);
   const stops=Array.from({length:5},(_,i)=>values[Math.floor(values.length*(i+1)/6)]??0);
   geo.features.forEach(f=>{const area=lookup.get(String(f.properties?.id));f.properties={...f.properties,value:area?.value??null,fill:area?.value==null?'#f8fafb':colors[stops.filter(s=>area.value!>=s).length],selected:String(f.properties?.id)===selected};});
   for(const id of ['density','outline','areas'])if(instance.getLayer(id))instance.removeLayer(id);
   for(const id of ['boundaries','cells'])if(instance.getSource(id))instance.removeSource(id);
   instance.addSource('boundaries',{type:'geojson',data:geo});
   instance.addLayer({id:'areas',type:'fill',source:'boundaries',paint:{'fill-color':data.metric==='concentration'?'#dce6ec':['get','fill'],'fill-opacity':1}});
   instance.addLayer({id:'outline',type:'line',source:'boundaries',paint:{'line-color':['case',['get','selected'],'#102e49','#ffffff'],'line-width':['case',['get','selected'],2.5,data.level==='zip'?0.5:1]}});
   if(data.metric==='concentration'){
    instance.addSource('cells',{type:'geojson',data:{type:'FeatureCollection',features:data.cells.map(c=>({type:'Feature',properties:{count:c.count},geometry:{type:'Point',coordinates:[c.longitude,c.latitude]}}))}});
    instance.addLayer({id:'density',type:'heatmap',source:'cells',paint:{'heatmap-weight':['interpolate',['linear'],['get','count'],0,0,Math.max(1,...data.cells.map(c=>c.count)),1],'heatmap-radius':28,'heatmap-intensity':1.5,'heatmap-opacity':0.85,'heatmap-color':['interpolate',['linear'],['heatmap-density'],0,'rgba(16,128,134,0)',0.2,'#b2d4d7',0.5,'#3e949d',0.8,'#2f687f',1,'#23496b']}});
   }
   setError('');instance.once('idle',()=>{if(!cancelled)setLoaded(true);});
  }).catch(()=>setError('Map boundaries are unavailable. Use the area filters or map data table.'));
  return()=>{cancelled=true;};
 },[data,ready,selected]);
 useEffect(()=>{const instance=map.current;if(!instance||!ready)return;
  const click=(e:maplibregl.MapMouseEvent)=>{if(!instance.getLayer('areas'))return;const feature=instance.queryRenderedFeatures(e.point,{layers:['areas']})[0];if(feature?.properties?.id)choose.current(String(feature.properties.id));};
  const move=(e:maplibregl.MapMouseEvent)=>{if(!instance.getLayer('areas'))return;const f=instance.queryRenderedFeatures(e.point,{layers:['areas']})[0];instance.getCanvas().style.cursor=f?'pointer':'';setHover(f?`${f.properties?.name} · ${f.properties?.value==null?'No data':data?.metric==='median_price'?money(Number(f.properties.value)):number(Number(f.properties?.value))+' sales'}`:'');};
  instance.on('click',click);instance.on('mousemove',move);return()=>{instance.off('click',click);instance.off('mousemove',move);};
 },[ready,data?.metric]);
 return <div className="map-frame" data-loaded={loaded}><div ref={root} className="map-canvas" aria-label="Interactive California market map"/>
  <div className="map-caption"><MapPin size={14}/>{selected||'California'}{data?.level==='county'&&selected?' County':''}</div>
  <button className="map-reset icon-button" aria-label="Reset map to California" onClick={()=>{choose.current('');map.current?.fitBounds(bounds,{padding:28,duration:matchMedia('(prefers-reduced-motion: reduce)').matches?0:450});}}><LocateFixed size={17}/></button>
  {error&&<div className="map-message" role="status">{error}</div>}{hover&&<div className="map-tooltip" role="status">{hover}</div>}
  <div className="map-legend"><span>{data?.metric==='median_price'?'Median close price':data?.metric==='concentration'?'Sales concentration':'Closed sales'}</span><div className="legend-ramp">{colors.map(c=><i key={c} style={{background:c}}/>)}</div><div className="legend-labels"><span>Lower</span><span>Higher</span></div><small>Unshaded areas: no matching data</small></div>
  <span className="map-attribution">US Census Bureau · {data?.level==='zip'?'2020 ZCTAs':'2024 counties'}</span>
 </div>;
}
