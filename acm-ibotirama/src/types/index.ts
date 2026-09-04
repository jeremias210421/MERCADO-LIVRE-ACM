export interface PackageContact {
  pacote: string;
  nome_comprador: string;
  telefone: string;
}

export interface ScannedCode {
  id: string;
  code: string;
  format: string;
  timestamp: number;
  isValid?: boolean;
  address?: string;
  buyerName?: string;
  phone?: string;
}

export interface RouteFolder {
  id: string;
  route: string;
  driverName: string;
  date: string;
  scannedCodes: ScannedCode[];
  createdAt: number;
}

export interface RouteData {
  rota: string;
  id: string;
  totalParadas: number;
  totalPacotes: number;
  paradas: Array<{
    sequencia: string;
    endereco: string;
    pacotes: string[];
    tipo_endereco: string;
    contatos?: PackageContact[];
  }>;
  observacao?: string;
  cidade?: string;
}
