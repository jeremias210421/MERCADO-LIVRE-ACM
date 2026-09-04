import { createClient, SupabaseClient } from '@supabase/supabase-js';

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL || '';
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY || '';

let supabase: SupabaseClient | null = null;

if (SUPABASE_URL && SUPABASE_ANON_KEY) {
  supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
}

export function isSupabaseConfigured(): boolean {
  return supabase !== null;
}

export function getSupabase(): SupabaseClient | null {
  return supabase;
}

// --- Tipos ---

export interface RotaListItem {
  id: string;
  rota: string;
  total_paradas: number;
  total_pacotes: number;
  cidade: string;
}

export interface Motorista {
  id: string;
  nome: string;
  telefone: string;
}

export interface RotaDetalhes {
  rota: string;
  id: string;
  totalParadas: number;
  totalPacotes: number;
  paradas: Array<{
    sequencia: string;
    endereco: string;
    pacotes: string[];
    tipo_endereco: string;
    contatos?: Array<{ pacote: string; nome_comprador: string; telefone: string }>;
  }>;
  observacao?: string;
  cidade?: string;
}

// --- Funções Helper ---

/**
 * Busca todas as rotas cadastradas
 */
export async function fetchRotas(): Promise<RotaListItem[]> {
  if (!supabase) return [];
  const { data, error } = await supabase
    .from('rotas')
    .select('id, rota, total_paradas, total_pacotes, cidade')
    .order('rota');

  if (error) {
    console.error('Erro ao buscar rotas:', error);
    return [];
  }
  return data || [];
}

/**
 * Busca todos os motoristas cadastrados
 */
export async function fetchMotoristas(): Promise<Motorista[]> {
  if (!supabase) return [];
  const { data, error } = await supabase
    .from('motoristas')
    .select('id, nome, telefone')
    .order('nome');

  if (error) {
    console.error('Erro ao buscar motoristas:', error);
    return [];
  }
  return data || [];
}

/**
 * Busca detalhes completos de uma rota (paradas + pacotes)
 * Retorna no formato compatível com RouteData do app
 */
export async function fetchRotaDetalhes(rotaId: string): Promise<RotaDetalhes | null> {
  if (!supabase) return null;

  try {
    // Buscar rota
    const { data: rotaData, error: rotaError } = await supabase
      .from('rotas')
      .select('*')
      .eq('id', rotaId)
      .single();

    if (rotaError || !rotaData) return null;

    // Buscar paradas com pacotes
    const { data: paradasData, error: paradasError } = await supabase
      .from('paradas')
      .select('*, pacotes(*)')
      .eq('rota_id', rotaId)
      .order('sequencia');

    if (paradasError) return null;

    // Transformar para formato compatível com RouteData (com contatos)
    const paradas = (paradasData || []).map((parada: any) => ({
      sequencia: parada.sequencia || '',
      endereco: parada.endereco || '',
      pacotes: (parada.pacotes || []).map((p: any) => p.codigo_pacote),
      tipo_endereco: parada.tipo_endereco || 'Residencial',
      contatos: (parada.pacotes || []).map((p: any) => ({
        pacote: p.codigo_pacote,
        nome_comprador: p.nome_comprador || '',
        telefone: p.telefone || ''
      }))
    }));

    return {
      rota: rotaData.rota,
      id: rotaData.id,
      totalParadas: rotaData.total_paradas || paradas.length,
      totalPacotes: rotaData.total_pacotes || paradas.reduce((acc: number, p: any) => acc + p.pacotes.length, 0),
      paradas,
      observacao: rotaData.observacao || '',
      cidade: rotaData.cidade || ''
    };
  } catch (e) {
    console.error('Erro ao buscar detalhes da rota:', e);
    return null;
  }
}

/**
 * Envia scans para o Supabase (upload em lote)
 */
export async function uploadScans(scans: Array<{
  rota_id?: string;
  motorista_id?: string;
  codigo_pacote: string;
  formato?: string;
  endereco?: string;
  is_valid?: boolean;
  escaneado_em?: string;
}>): Promise<boolean> {
  if (!supabase || scans.length === 0) return false;

  try {
    const { error } = await supabase
      .from('scans')
      .insert(scans);

    if (error) {
      console.error('Erro ao enviar scans:', error);
      return false;
    }
    return true;
  } catch (e) {
    console.error('Erro ao enviar scans:', e);
    return false;
  }
}

/**
 * Verifica conectividade com o Supabase
 */
export async function checkConnectivity(): Promise<boolean> {
  if (!supabase) return false;
  try {
    const { error } = await supabase
      .from('rotas')
      .select('id')
      .limit(1);
    return !error;
  } catch {
    return false;
  }
}
