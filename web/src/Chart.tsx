import {useEffect,useRef} from 'react';
import * as echarts from 'echarts/core';
import {LineChart,BarChart,ScatterChart,TreemapChart} from 'echarts/charts';
import {GridComponent,TooltipComponent,LegendComponent,AriaComponent} from 'echarts/components';
import {SVGRenderer} from 'echarts/renderers';
import type {EChartsOption} from 'echarts';
import {Table2} from 'lucide-react';
echarts.use([LineChart,BarChart,ScatterChart,TreemapChart,GridComponent,TooltipComponent,LegendComponent,AriaComponent,SVGRenderer]);

export function Chart({title,description,option,columns,rows,tall=false}:{title:string;description?:string;option:EChartsOption;columns:string[];rows:(string|number)[][];tall?:boolean}){
 const root=useRef<HTMLDivElement>(null);
 useEffect(()=>{if(!root.current)return;const chart=echarts.init(root.current,undefined,{renderer:'svg'});chart.setOption({...option,tooltip:{...(option.tooltip as object||{}),renderMode:'richText'},animation:!matchMedia('(prefers-reduced-motion: reduce)').matches,animationDuration:300,textStyle:{fontFamily:'-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',color:'#4c6071'},aria:{enabled:true}});const observer=new ResizeObserver(()=>chart.resize());observer.observe(root.current);return()=>{observer.disconnect();chart.dispose();};},[option]);
 return <section className={'chart-panel'+(tall?' tall':'')}><div className="chart-heading"><h3>{title}</h3>{description&&<p>{description}</p>}</div>{rows.length?<div ref={root} className="chart" role="img" aria-label={title+'. Data table follows.'}/>:<div className="chart-empty">No matching sales in this selection.</div>}<details className="data-details"><summary><Table2 size={14}/> View data table</summary><div className="table-scroll"><table><caption>{title}</caption><thead><tr>{columns.map(c=><th key={c} scope="col">{c}</th>)}</tr></thead><tbody>{rows.map((r,i)=><tr key={i}>{r.map((c,j)=><td key={j}>{c}</td>)}</tr>)}</tbody></table></div></details></section>;
}

export function lineOption(labels:string[],values:(number|null)[],color:string,format:(v:number)=>string):EChartsOption{
 return {grid:{left:68,right:20,top:16,bottom:38},tooltip:{trigger:'axis',valueFormatter:value=>format(Number(value))},xAxis:{type:'category',data:labels,boundaryGap:false,axisLine:{lineStyle:{color:'#d8e1e8'}},axisTick:{show:false},axisLabel:{fontSize:11,hideOverlap:true}},yAxis:{type:'value',scale:true,splitNumber:4,axisLabel:{formatter:format,fontSize:11},splitLine:{lineStyle:{color:'#edf1f4'}}},series:[{type:'line',data:values,symbol:'circle',symbolSize:5,showSymbol:false,connectNulls:false,lineStyle:{color,width:2.5},itemStyle:{color},areaStyle:{color,opacity:0.06}}]};
}
