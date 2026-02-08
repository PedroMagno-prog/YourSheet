import flet as ft
import json
import os
import uuid
from dice_engine import DiceEngine

FILE_NAME = "rpg_data.json"


class RPGApp:
    def __init__(self):
        self.data = self.load_data()
        self.engine = DiceEngine()
        self.current_char_index = None

    def load_data(self):
        default = {"characters": [], "global_rules": []}
        if not os.path.exists(FILE_NAME):
            return default
        try:
            with open(FILE_NAME, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                # Garante que chaves novas existam em arquivos antigos
                if "global_rules" not in loaded: loaded["global_rules"] = []
                return loaded
        except:
            return default

    def save_data(self):
        with open(FILE_NAME, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)

    def get_context(self, char_idx):
        if char_idx is None or char_idx >= len(self.data["characters"]):
            return {}
        char = self.data["characters"][char_idx]
        context = {}
        for seg in char["segments"]:
            for field in seg["fields"]:
                if field["type"] == "Atributo":
                    try:
                        val = int(field["value"])
                        context[field["name"]] = val
                    except:
                        pass
        return context

    def get_rules_by_ids(self, rule_ids):
        """Retorna os objetos de regra completos baseados na lista de IDs salvos na ação"""
        if not rule_ids: return []
        active = []
        for r in self.data["global_rules"]:
            if r["id"] in rule_ids:
                active.append(r)
        return active


def main(page: ft.Page):
    page.title = "RPG Maker Pocket"
    page.theme_mode = ft.ThemeMode.DARK
    page.scroll = ft.ScrollMode.AUTO

    app = RPGApp()

    # --- Elementos de UI Globais ---
    log_view = ft.Column(scroll=ft.ScrollMode.ALWAYS, height=150)

    def add_log(text, color="white"):
        log_view.controls.insert(0, ft.Text(text, color=color, selectable=True))
        page.update()

    # ==============================================================================
    #                      GERENCIADOR DE CONDICIONAIS (NOVO)
    # ==============================================================================

    def open_rules_manager(e):
        # Campos do Formulário
        txt_name = ft.TextField(label="Nome da Regra (ex: Sorte de Halfling)", expand=True)
        txt_trigger = ft.TextField(label="Valor Gatilho [1]", value="1", width=100,
                                   keyboard_type=ft.KeyboardType.NUMBER)

        dd_scope = ft.Dropdown(
            label="Onde [2]",
            width=200,
            options=[
                ft.dropdown.Option("any", "Em Qualquer Dado"),
                ft.dropdown.Option("first", "No Primeiro Dado"),
            ],
            value="any"
        )

        dd_effect = ft.Dropdown(
            label="Fazer o que [3]",
            expand=True,
            options=[
                ft.dropdown.Option("reroll", "Rolar Novamente (Substitui)"),
                ft.dropdown.Option("add", "Somar Valor Extra"),
                ft.dropdown.Option("explode", "Explodir (Rola outro e soma)"),
            ],
            value="reroll",
            on_change=lambda e: toggle_param_visibility(e)
        )

        txt_param = ft.TextField(label="Valor Extra", value="0", visible=False, width=100)

        def toggle_param_visibility(e):
            txt_param.visible = (dd_effect.value == "add")
            rules_dialog.update()

        def add_rule_click(e):
            if not txt_name.value: return

            new_rule = {
                "id": str(uuid.uuid4()),
                "name": txt_name.value,
                "trigger_val": int(txt_trigger.value),
                "scope": dd_scope.value,
                "effect": dd_effect.value,
                "effect_param": int(txt_param.value)
            }
            app.data["global_rules"].append(new_rule)
            app.save_data()
            refresh_rules_list()
            txt_name.value = ""
            rules_dialog.update()

        def delete_rule_click(e, rule_id):
            app.data["global_rules"] = [r for r in app.data["global_rules"] if r["id"] != rule_id]
            app.save_data()
            refresh_rules_list()
            rules_dialog.update()

        rules_list_col = ft.Column()

        def refresh_rules_list():
            rules_list_col.controls.clear()
            for r in app.data["global_rules"]:
                desc = f"Se sair {r['trigger_val']} ({r['scope']}) -> {r['effect']}"
                if r['effect'] == 'add': desc += f" +{r['effect_param']}"

                rules_list_col.controls.append(
                    ft.ListTile(
                        title=ft.Text(r["name"], weight="bold"),
                        subtitle=ft.Text(desc),
                        trailing=ft.IconButton(ft.Icons.DELETE, icon_color="red",
                                               on_click=lambda e, rid=r["id"]: delete_rule_click(e, rid))
                    )
                )

        refresh_rules_list()

        rules_dialog = ft.AlertDialog(
            title=ft.Text("Criador de Condicionais"),
            content=ft.Container(
                width=600,
                content=ft.Column([
                    ft.Text("Defina regras globais que podem ser ativadas nas ações."),
                    ft.Divider(),
                    ft.Row([txt_name]),
                    ft.Row([
                        ft.Text("Quando sair"), txt_trigger,
                        ft.Text("em"), dd_scope
                    ], alignment=ft.MainAxisAlignment.START),
                    ft.Row([
                        ft.Text("Deve-se"), dd_effect, txt_param
                    ]),
                    ft.ElevatedButton("Save Rule", on_click=add_rule_click),
                    ft.Divider(),
                    ft.Text("Rules:", weight="bold"),
                    ft.Container(rules_list_col, height=200, border=ft.border.all(1, "grey"), border_radius=5)
                ])
            ),
        )
        page.open(rules_dialog)

    # ==============================================================================
    #                      VINCULAR REGRAS NA AÇÃO
    # ==============================================================================

    def open_action_settings(e, char_idx, seg_idx, field_idx):
        field = app.data["characters"][char_idx]["segments"][seg_idx]["fields"][field_idx]
        if "active_rules" not in field:
            field["active_rules"] = []

        selected_rules = field["active_rules"]

        def on_checkbox_change(e, rule_id):
            if e.control.value:  # Checked
                if rule_id not in selected_rules: selected_rules.append(rule_id)
            else:  # Unchecked
                if rule_id in selected_rules: selected_rules.remove(rule_id)

            app.data["characters"][char_idx]["segments"][seg_idx]["fields"][field_idx]["active_rules"] = selected_rules
            app.save_data()

        checks_col = ft.Column()
        if not app.data["global_rules"]:
            checks_col.controls.append(ft.Text("Nenhuma regra global criada."))

        for rule in app.data["global_rules"]:
            checks_col.controls.append(
                ft.Checkbox(
                    label=f"{rule['name']} (Se {rule['trigger_val']} -> {rule['effect']})",
                    value=(rule["id"] in selected_rules),
                    on_change=lambda e, rid=rule["id"]: on_checkbox_change(e, rid)
                )
            )

        dlg = ft.AlertDialog(
            title=ft.Text(f"Action Config: {field['name']}"),
            content=ft.Column([
                ft.Text("Select the active conditions to this roll:"),
                checks_col
            ], tight=True)
        )
        page.open(dlg)

    # --- Motor de Rolagem ---
    def run_action(e, formula, char_idx, active_rules_ids=None):
        if not formula: return
        context = app.get_context(char_idx)

        # Recupera os objetos de regra completos baseados nos IDs salvos no campo
        rules_objects = app.get_rules_by_ids(active_rules_ids)

        total, detalhes = app.engine.parse_and_roll(formula, context, rules_objects)

        add_log(f"🎲 Rolou: {formula}", color="cyan")
        add_log(f"➤ Detalhes: {detalhes}", color="grey")
        add_log(f"★ RESULTADO: {total}", color="green" if total > 0 else "red")
        add_log("-" * 30)

    # --- UI Principal ---

    # ... (Lógica de Delete Igual ao Anterior) ...
    delete_input = ft.TextField(label="Digite DELETAR", color="red", border_color="red")
    pending_delete_idx = [-1]

    def confirm_delete_click(e):
        # ... (Mesma lógica de antes) ...
        if delete_input.value == "DELETAR":
            idx = pending_delete_idx[0]
            if 0 <= idx < len(app.data["characters"]):
                app.data["characters"].pop(idx)
                app.save_data()
                if app.current_char_index == idx:
                    app.current_char_index = None
                elif app.current_char_index is not None and app.current_char_index > idx:
                    app.current_char_index -= 1
                update_view()
            page.close(delete_dialog)

    delete_dialog = ft.AlertDialog(
        modal=True, title=ft.Text("⚠ DELETE Character"),
        content=ft.Column([ft.Text("Type DELETE:"), delete_input], tight=True),
        actions=[ft.TextButton("Return", on_click=lambda e: page.close(delete_dialog)),
                 ft.ElevatedButton("DELETE", on_click=confirm_delete_click, bgcolor="red")]
    )

    def request_delete(e, idx):
        pending_delete_idx[0] = idx
        delete_input.value = ""
        page.open(delete_dialog)

    # --- Construção da Ficha ---

    def build_character_view(char_idx):
        char = app.data["characters"][char_idx]
        name_field = ft.TextField(label="Nome", value=char["name"], on_change=lambda e: update_char_name(e, char_idx))
        segments_col = ft.Column()

        for seg_idx, seg in enumerate(char["segments"]):
            fields_col = ft.Column()
            for field_idx, field in enumerate(seg["fields"]):

                # Container da Linha
                row = ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

                if field["type"] == "Texto":
                    row.controls.append(
                        ft.TextField(label=field["name"], value=field["value"], expand=True, multiline=True,
                                     on_change=lambda e, s=seg_idx, f=field_idx: update_field_val(e, char_idx, s, f)))

                elif field["type"] == "Atributo":
                    row.controls.extend([
                        ft.TextField(value=field["name"], label="Var", width=100,
                                     on_change=lambda e, s=seg_idx, f=field_idx: update_field_name(e, char_idx, s, f)),
                        ft.TextField(value=str(field["value"]), label="Val", width=80,
                                     keyboard_type=ft.KeyboardType.NUMBER,
                                     on_change=lambda e, s=seg_idx, f=field_idx: update_field_val(e, char_idx, s, f))
                    ])

                elif field["type"] == "Ação":
                    # Recupera regras salvas no JSON, se houver
                    active_rules = field.get("active_rules", [])

                    row.controls.extend([
                        ft.TextField(value=field["name"], label="Ação", expand=True,
                                     on_change=lambda e, s=seg_idx, f=field_idx: update_field_name(e, char_idx, s, f)),
                        ft.TextField(value=field["value"], label="Fórmula", expand=True,
                                     on_change=lambda e, s=seg_idx, f=field_idx: update_field_val(e, char_idx, s, f)),

                        # Botão Configurar Regras (Engrenagem)
                        ft.IconButton(ft.Icons.SETTINGS, icon_color="blue", tooltip="Condicionais",
                                      on_click=lambda e, s=seg_idx, f=field_idx: open_action_settings(e, char_idx, s,
                                                                                                      f)),

                        # Botão Rolar (Passa active_rules)
                        ft.IconButton(ft.Icons.CASINO, icon_color="pink",
                                      on_click=lambda e, f=field["value"], r=active_rules: run_action(e, f, char_idx,
                                                                                                      r))
                    ])

                # Botão Deletar Campo
                row.controls.append(ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_size=16,
                                                  on_click=lambda e, s=seg_idx, f=field_idx: delete_field(e, char_idx,
                                                                                                          s, f)))
                fields_col.controls.append(row)

            # Botões do Segmento
            add_btns = ft.Row([
                ft.ElevatedButton("+ Txt", on_click=lambda e, s=seg_idx: add_field(char_idx, s, "Texto")),
                ft.ElevatedButton("+ Att", on_click=lambda e, s=seg_idx: add_field(char_idx, s, "Atributo")),
                ft.ElevatedButton("+ Act", on_click=lambda e, s=seg_idx: add_field(char_idx, s, "Ação")),
                ft.IconButton(ft.Icons.DELETE_FOREVER, icon_color="red",
                              on_click=lambda e, s=seg_idx: delete_segment(char_idx, s))
            ])

            # Título Editável
            seg_title = ft.TextField(value=seg["name"], text_style=ft.TextStyle(weight="bold"),
                                     border=ft.InputBorder.UNDERLINE,
                                     on_change=lambda e, s=seg_idx: update_segment_name(e, char_idx, s), expand=True)

            segments_col.controls.append(
                ft.ExpansionTile(title=seg_title, controls=[fields_col, add_btns, ft.Divider()],
                                 initially_expanded=True))

        return ft.Column(
            [name_field, segments_col, ft.ElevatedButton("Novo Segmento", on_click=lambda e: add_segment(char_idx))])

    # --- CRUD Básico (Simplificado para caber) ---
    def update_view():
        char_list.controls.clear()

        # Botão Global de Regras
        char_list.controls.append(ft.ElevatedButton("⚙ Condicionais", on_click=open_rules_manager, width=200))
        char_list.controls.append(ft.Divider())

        for idx, char in enumerate(app.data["characters"]):
            char_list.controls.append(ft.ListTile(
                title=ft.Text(char["name"]), leading=ft.Icon(ft.Icons.PERSON),
                trailing=ft.IconButton(ft.Icons.DELETE_FOREVER, icon_color="red",
                                       on_click=lambda e, i=idx: request_delete(e, i)),
                on_click=lambda e, i=idx: select_char(i), selected=(idx == app.current_char_index)
            ))
        char_list.controls.append(ft.ListTile(title=ft.Text("New Character +"), on_click=create_char))

        if app.current_char_index is not None and app.current_char_index < len(app.data["characters"]):
            main_area.content = build_character_view(app.current_char_index)
        else:
            main_area.content = ft.Text("Select a Character")
        page.update()

    def select_char(idx):
        app.current_char_index = idx; update_view()

    def create_char(e):
        app.data["characters"].append({"name": "Novo", "segments": []}); app.save_data(); select_char(
            len(app.data["characters"]) - 1)

    def update_char_name(e, idx):
        app.data["characters"][idx]["name"] = e.control.value; app.save_data()

    def add_segment(idx):
        app.data["characters"][idx]["segments"].append(
            {"name": "Novo Seg", "fields": []}); app.save_data(); update_view()

    def update_segment_name(e, c_idx, s_idx):
        app.data["characters"][c_idx]["segments"][s_idx]["name"] = e.control.value; app.save_data()

    def delete_segment(c, s):
        app.data["characters"][c]["segments"].pop(s); app.save_data(); update_view()

    def add_field(c, s, t):
        app.data["characters"][c]["segments"][s]["fields"].append(
            {"type": t, "name": "Novo", "value": ""}); app.save_data(); update_view()

    def update_field_val(e, c, s, f):
        app.data["characters"][c]["segments"][s]["fields"][f]["value"] = e.control.value; app.save_data()

    def update_field_name(e, c, s, f):
        app.data["characters"][c]["segments"][s]["fields"][f]["name"] = e.control.value; app.save_data()

    def delete_field(e, c, s, f):
        app.data["characters"][c]["segments"][s]["fields"].pop(f); app.save_data(); update_view()

    char_list = ft.ListView(width=260, spacing=10)
    main_area = ft.Container(expand=True, padding=20)
    page.add(ft.Row(
        [ft.Column([ft.Text("RPG Maker", size=20, weight="bold"), char_list, ft.Divider(), log_view], width=320),
         ft.VerticalDivider(), main_area], expand=True))
    update_view()


ft.app(target=main)