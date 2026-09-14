import {useQuery} from '@tanstack/react-query';
import type {components} from './api-types';
export type Meta=components['schemas']['Meta'];
export type Metrics=components['schemas']['Metrics'];
export type Entity=components['schemas']['Entity'];
export type MapData=components['schemas']['MapData'];
export type Selection=Record<string,string>;
export class ApiError extends Error {constructor(public status:number,public detail:{message?:string;nearest_month?:string;code?:string}){super(detail.message||'Unable to load market data.');}}
export async function get<T>(route:string,params:Selection={},signal?:AbortSignal):Promise<T>{
  const search=new URLSearchParams(Object.entries(params).filter(([,v])=>v));
  const response=await fetch(`/api/v1/${route}?${search}`,{signal});
  if(!response.ok){const error=await response.json().catch(()=>({detail:{}}));throw new ApiError(response.status,error.detail||{});}
  return response.json();
}
export function useMarket<K extends 'Summary'|'Trends'|'FilterOptions'|'MapData'|'Competitive'>(route:string,params:Selection,enabled:boolean){
 return useQuery({queryKey:[route,params],queryFn:({signal})=>get<components['schemas'][K]>(route,params,signal),enabled,retry:(count,error)=>!(error instanceof ApiError&&[409,416,422].includes(error.status))&&count<1});
}
export const number=(n:number|null|undefined)=>n==null?'—':new Intl.NumberFormat('en-US',{maximumFractionDigits:0}).format(n);
export const money=(n:number|null|undefined,compact=false)=>n==null?'—':new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',maximumFractionDigits:0,...(compact?{notation:'compact' as const,maximumFractionDigits:1}:{})}).format(n);
export const monthLabel=(m:string,short=false)=>new Date(m+'-01T12:00:00').toLocaleDateString('en-US',{month:short?'short':'long',year:'numeric'});
