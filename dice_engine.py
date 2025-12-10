import re
from random import randint


class DiceEngine:
    def __init__(self):
        pass

    def _roll_single_die(self, faces):
        return randint(1, faces)

    def _explode(self, current_value, faces, threshold):
        """Recursividade para dados explosivos"""
        extra_val = 0
        if current_value >= threshold:
            new_roll = self._roll_single_die(faces)
            # Continua explodindo se o novo dado também for alto
            extra_val = new_roll + self._explode(new_roll, faces, threshold)
        return extra_val

    def parse_and_roll(self, formula: str, context: dict) -> tuple[int, str]:
        """
        Interpreta a fórmula, substitui variáveis e rola.
        Retorna: (Resultado Total, String de Detalhes)
        """
        # 1. Limpeza e Substituição de Variáveis
        formula = formula.lower().replace(" ", "")

        # Substitui nomes de atributos pelos seus valores
        # Ex: '1d20+forca' vira '1d20+3' (se forca for 3)
        for attr_name, attr_val in context.items():
            if attr_name.lower() in formula:
                formula = formula.replace(attr_name.lower(), str(attr_val))

        try:
            # 2. Identificar partes da soma (suporta '1d20 + 1d4 + 5')
            # Quebra nos sinais de + ou -
            parts = re.split(r'([+-])', formula)
            # O split gera algo como ['1d20', '+', '5', '-', '1d4']

            total_geral = 0
            log_detalhado = []

            # Normaliza a lista para processar: [sinal, valor, sinal, valor...]
            if parts[0] != '-' and parts[0] != '+':
                parts.insert(0, '+')

            # Processa em pares (Sinal, Conteúdo)
            for i in range(0, len(parts), 2):
                operator = parts[i]
                chunk = parts[i + 1]

                if not chunk: continue

                valor_parcial = 0
                detalhe_parcial = ""

                # Verifica se é dado (tem 'd') ou número fixo
                if 'd' in chunk:
                    # Regex para capturar: Qtd, Lados, Modificadores (dl, dh, e)
                    match = re.search(r'(\d+)d(\d+)(.*)', chunk)
                    if match:
                        qtd = int(match.group(1))
                        lados = int(match.group(2))
                        mods = match.group(3)  # ex: dl1e6

                        # Rolagem inicial
                        rolagens = [self._roll_single_die(lados) for _ in range(qtd)]
                        rolagens.sort()  # Ordena para facilitar o drop

                        log_dados = f"[{','.join(map(str, rolagens))}]"

                        # Processa Drop Low (dl)
                        if 'dl' in mods:
                            drop_n = int(re.search(r'dl(\d+)', mods).group(1))
                            # Remove os primeiros N (menores)
                            rolagens = rolagens[drop_n:]
                            log_dados += f"->dl{drop_n}->[{','.join(map(str, rolagens))}]"

                        # Processa Drop High (dh)
                        if 'dh' in mods:
                            drop_n = int(re.search(r'dh(\d+)', mods).group(1))
                            # Remove os últimos N (maiores)
                            rolagens = rolagens[:-drop_n] if drop_n < len(rolagens) else []
                            log_dados += f"->dh{drop_n}->[{','.join(map(str, rolagens))}]"

                        # Processa Explode (e) - Opção B: Só explode o que sobrou
                        soma_dados = sum(rolagens)
                        if 'e' in mods:
                            explode_target = int(re.search(r'e(\d+)', mods).group(1))
                            explosao_acumulada = 0
                            for r in rolagens:
                                if r >= explode_target:
                                    explosao_acumulada += self._explode(r, lados, explode_target)

                            if explosao_acumulada > 0:
                                log_dados += f"+Exp({explosao_acumulada})"
                                soma_dados += explosao_acumulada

                        valor_parcial = soma_dados
                        detalhe_parcial = f"{qtd}d{lados}{mods}: {log_dados}"
                else:
                    # É apenas um número estático (ex: 5)
                    valor_parcial = int(chunk)
                    detalhe_parcial = str(valor_parcial)

                # Aplica o operador no total geral
                if operator == '+':
                    total_geral += valor_parcial
                    log_detalhado.append(f"+ {detalhe_parcial}")
                else:
                    total_geral -= valor_parcial
                    log_detalhado.append(f"- {detalhe_parcial}")

            return total_geral, " ".join(log_detalhado)

        except Exception as e:
            return 0, f"Erro na fórmula: {str(e)}"


# Teste rápido se rodar direto
if __name__ == "__main__":
    eng = DiceEngine()
    # Teste complexo: 4d6, tira o menor, explode no 6, soma 3
    # Simula atributo forca = 3
    print(eng.parse_and_roll("4d6dl1e6 + forca", {"forca": 3}))