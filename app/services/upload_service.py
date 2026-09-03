"""
Upload Service - Import JSON routes to Supabase.
"""
import json
from typing import Any
from app.supabase_client import get_supabase


def importar_json_para_supabase(dados_json: dict) -> dict[str, Any]:
    """Import route JSON to Supabase - com upsert e fallback romaneio (igual ao app celular)."""
    supabase = get_supabase()
    try:
        rota_nome = str(dados_json.get('rota') or dados_json.get('route') or '').strip().upper()
        if not rota_nome:
            return {'success': False, 'message': 'JSON sem campo rota'}
        id_original = str(dados_json.get('id') or '').strip()
        total_paradas = dados_json.get('totalParadas') or len(dados_json.get('paradas') or [])
        total_pacotes = dados_json.get('totalPacotes') or sum(len(p.get('pacotes') or []) for p in dados_json.get('paradas') or [])

        # 1) busca rota existente da MESMA DATA (hoje) - mesmo nome em dias diferentes = nova rota
        from datetime import datetime
        hoje = datetime.now().strftime('%Y-%m-%d')
        rota_id = None
        # tenta por id_original + data de hoje
        if id_original:
            try:
                r = supabase.table('rotas').select('id,criado_em,created_at').eq('id_original', id_original).execute()
                for row in (r.data or []):
                    criado = (row.get('criado_em') or row.get('created_at') or '')[:10]
                    if criado == hoje:
                        rota_id = row['id']; break
            except: pass
        # tenta por nome + data de hoje
        if not rota_id:
            try:
                r = supabase.table('rotas').select('id,criado_em,created_at').eq('rota', rota_nome).execute()
                for row in (r.data or []):
                    criado = (row.get('criado_em') or row.get('created_at') or '')[:10]
                    if criado == hoje:
                        rota_id = row['id']; break
            except: pass

        if not rota_id:
            import uuid
            rota_id = str(uuid.uuid4())
            ins = supabase.table('rotas').insert({
                'id': rota_id,
                'rota': rota_nome,
                'id_original': id_original,
                'total_paradas': total_paradas,
                'total_pacotes': total_pacotes,
                'observacao': dados_json.get('observacao', ''),
                'cidade': dados_json.get('cidade', ''),
            }).execute()
            if ins.data: rota_id = ins.data[0]['id']
        else:
            try:
                supabase.table('rotas').update({
                    'total_paradas': total_paradas,
                    'total_pacotes': total_pacotes,
                    'atualizado_em': datetime.utcnow().isoformat()
                }).eq('id', rota_id).execute()
            except: pass

        importados = 0
        for idx, parada in enumerate(dados_json.get('paradas') or []):
            seq = str(parada.get('sequencia') or '').strip()
            if not seq or seq == '-' or not seq.isdigit():
                seq = str(idx + 1).zfill(2)
            else:
                seq = seq.zfill(2)
            endereco = str(parada.get('endereco') or '').strip()
            tipo = parada.get('tipo_endereco') or 'Residencial'

            parada_id = None
            try:
                rp = supabase.table('paradas').select('id').eq('rota_id', rota_id).eq('sequencia', seq).limit(1).execute()
                if rp.data: parada_id = rp.data[0]['id']
            except: pass
            if not parada_id:
                import uuid
                parada_id = str(uuid.uuid4())
                try:
                    ins = supabase.table('paradas').insert({
                        'id': parada_id,
                        'rota_id': rota_id,
                        'sequencia': seq,
                        'endereco': endereco,
                        'tipo_endereco': tipo,
                    }).execute()
                    if ins.data: parada_id = ins.data[0]['id']
                except Exception as e:
                    # RLS bloqueando paradas -> fallback para romaneio
                    if 'row-level security' in str(e).lower() or '42501' in str(e):
                        for code in parada.get('pacotes') or []:
                            c = str(code).strip().upper()
                            if not c: continue
                            try:
                                supabase.table('romaneio').upsert({
                                    'id': str(uuid.uuid4()),
                                    'route': rota_nome,
                                    'code': c,
                                    'sequence': int(seq) if seq.isdigit() else idx+1,
                                    'address': endereco,
                                    'neighborhood': tipo,
                                }, on_conflict='id').execute()
                                importados += 1
                            except: pass
                        continue
                    else:
                        continue

            for code in parada.get('pacotes') or []:
                c = str(code).strip().upper()
                if not c: continue
                try:
                    ex = supabase.table('pacotes').select('id').eq('parada_id', parada_id).eq('codigo_pacote', c).limit(1).execute()
                    if ex.data: continue
                except: pass
                try:
                    supabase.table('pacotes').insert({
                        'parada_id': parada_id,
                        'codigo_pacote': c,
                        'status': 'pendente',
                    }).execute()
                    importados += 1
                except Exception as e:
                    if 'row-level security' in str(e).lower() or '42501' in str(e):
                        try:
                            import uuid
                            supabase.table('romaneio').upsert({
                                'id': str(uuid.uuid4()),
                                'route': rota_nome,
                                'code': c,
                                'sequence': int(seq) if seq.isdigit() else idx+1,
                                'address': endereco,
                            }, on_conflict='id').execute()
                            importados += 1
                        except: pass

        return {'success': True, 'message': f"Rota {rota_nome} sincronizada: {importados} novos pacotes ({total_pacotes} no arquivo) em {len(dados_json.get('paradas') or [])} paradas"}

    except Exception as e:
        return {'success': False, 'message': f"Erro: {str(e)}"}