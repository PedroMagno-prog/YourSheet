import re
from random import randint


class DiceEngine:
    def __init__(self):
        pass

    def _roll_single_die(self, faces):
        return randint(1, faces)

    def _explode(self, current_value, faces, threshold):
        extra_val = 0
        if current_value >= threshold:
            new_roll = self._roll_single_die(faces)
            extra_val = new_roll + self._explode(new_roll, faces, threshold)
        return extra_val

    def apply_custom_rules(self, rolagens: list, sides: int, active_rules: list) -> tuple[list, int, str]:
        """
        Aplica regras condicionais (ex: Rolar novamente se der 1).
        Retorna: (Lista de Dados Modificada, Bonus Extra Numérico, Log de Texto)
        """
        log_rules = ""
        bonus_total = 0

        # Iteramos sobre uma cópia para poder modificar a original com segurança
        for i, val in enumerate(rolagens):
            # Para cada dado, verificamos todas as regras ativas
            for rule in active_rules:

                # 1. Checa o Escopo (Primeiro Dado ou Qualquer Dado)
                is_target = False
                if rule["scope"] == "any":
                    is_target = True
                elif rule["scope"] == "first" and i == 0:
                    is_target = True

                # 2. Checa o Gatilho (Valor do dado == Valor da regra)
                if is_target and val == int(rule["trigger_val"]):

                    # 3. Aplica o Efeito
                    if rule["effect"] == "reroll":
                        new_val = self._roll_single_die(sides)
                        log_rules += f"[Regra '{rule['name']}': {val}->{new_val}] "
                        rolagens[i] = new_val  # Substitui o valor
                        val = new_val  # Atualiza para próximas checagens

                    elif rule["effect"] == "add":
                        bonus = int(rule["effect_param"])
                        bonus_total += bonus
                        log_rules += f"[Regra '{rule['name']}': +{bonus}] "

                    elif rule["effect"] == "explode":
                        # Rola um novo dado e soma ao TOTAL (não substitui o atual)
                        extra = self._roll_single_die(sides)
                        bonus_total += extra
                        log_rules += f"[Regra '{rule['name']}': Explodiu +{extra}] "

        return rolagens, bonus_total, log_rules

    def parse_and_roll(self, formula: str, context: dict, active_rules: list = []) -> tuple[int, str]:
        """
        Agora aceita active_rules: lista de dicionários com as regras selecionadas.
        """
        formula = formula.lower().replace(" ", "")

        for attr_name, attr_val in context.items():
            if attr_name.lower() in formula:
                formula = formula.replace(attr_name.lower(), str(attr_val))

        try:
            parts = re.split(r'([+-])', formula)
            if parts[0] != '-' and parts[0] != '+':
                parts.insert(0, '+')

            total_geral = 0
            log_detalhado = []

            for i in range(0, len(parts), 2):
                operator = parts[i]
                chunk = parts[i + 1]
                if not chunk: continue

                valor_parcial = 0
                detalhe_parcial = ""

                if 'd' in chunk:
                    match = re.search(r'(\d+)d(\d+)(.*)', chunk)
                    if match:
                        qtd = int(match.group(1))
                        lados = int(match.group(2))
                        mods = match.group(3)

                        # 1. Rolagem Inicial
                        rolagens = [self._roll_single_die(lados) for _ in range(qtd)]

                        # 2. APLICAR REGRAS CUSTOMIZADAS (NOVIDADE)
                        # Elas acontecem antes de ordenar ou dropar
                        rolagens, rules_bonus, rules_log = self.apply_custom_rules(rolagens, lados, active_rules)

                        # Preparar string de log
                        log_dados = f"[{','.join(map(str, rolagens))}]"
                        if rules_log:
                            log_dados += f" {rules_log}"

                        # 3. Lógica padrão (Drop/Keep/Explode Nativo)
                        rolagens.sort()

                        if 'dl' in mods:
                            drop_n = int(re.search(r'dl(\d+)', mods).group(1))
                            rolagens = rolagens[drop_n:]
                            log_dados += f"->dl{drop_n}->[{','.join(map(str, rolagens))}]"

                        if 'dh' in mods:
                            drop_n = int(re.search(r'dh(\d+)', mods).group(1))
                            rolagens = rolagens[:-drop_n] if drop_n < len(rolagens) else []
                            log_dados += f"->dh{drop_n}->[{','.join(map(str, rolagens))}]"

                        soma_dados = sum(rolagens)

                        # Explode nativo (e)
                        if 'e' in mods:
                            explode_target = int(re.search(r'e(\d+)', mods).group(1))
                            explosao_acumulada = 0
                            for r in rolagens:
                                if r >= explode_target:
                                    explosao_acumulada += self._explode(r, lados, explode_target)
                            if explosao_acumulada > 0:
                                log_dados += f"+Exp({explosao_acumulada})"
                                soma_dados += explosao_acumulada

                        valor_parcial = soma_dados + rules_bonus
                        detalhe_parcial = f"{qtd}d{lados}{mods}: {log_dados}"
                else:
                    valor_parcial = int(chunk)
                    detalhe_parcial = str(valor_parcial)

                if operator == '+':
                    total_geral += valor_parcial
                    log_detalhado.append(f"+ {detalhe_parcial}")
                else:
                    total_geral -= valor_parcial
                    log_detalhado.append(f"- {detalhe_parcial}")

            return total_geral, " ".join(log_detalhado)

        except Exception as e:
            return 0, f"Erro na fórmula: {str(e)}"