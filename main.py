import flet as ft
import json
import os
from dice_engine import DiceEngine

FILE_NAME = "rpg_data.json"

class RPGApp:
    def __init__(self):
        self.data = self.load_data()
        self.engine = DiceEngine()
        self.current_char_index = None

    def load_data(self):
        if not os.path.exists(FILE_NAME):
            return {"characters": []}
        try:
            with open(FILE_NAME, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {"characters": []}

    def save_data(self):
        with open(FILE_NAME, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)

    def get_context(self, char_idx):
        """Cria o dicionário de variáveis (atributos) para rolagens"""
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


def main(page: ft.Page):
    page.title = "RPG Maker Pocket"
    page.theme_mode = ft.ThemeMode.DARK
    page.scroll = ft.ScrollMode.AUTO

    app = RPGApp()

    # --- Elementos de UI Globais ---

    log_view = ft.Column(scroll=ft.ScrollMode.ALWAYS, height=150)

    def get_data_file_path(filename):
        # Combina o caminho base com o nome do seu arquivo
        return os.path.join(app_data_path, filename)

    def add_log(text, color="white"):
        log_view.controls.insert(0, ft.Text(text, color=color, selectable=True))
        page.update()

    # --- Lógica de Exclusão de Personagem ---

    pending_delete_idx = [-1]

    def confirm_delete_click(e):
        if delete_input.value == "DELETAR":
            idx = pending_delete_idx[0]
            if 0 <= idx < len(app.data["characters"]):
                deleted_name = app.data["characters"][idx]["name"]
                app.data["characters"].pop(idx)
                app.save_data()

                if app.current_char_index == idx:
                    app.current_char_index = None
                elif app.current_char_index is not None and app.current_char_index > idx:
                    app.current_char_index -= 1

                add_log(f"Personagem '{deleted_name}' apagado.", "red")
                update_view()
            page.close(delete_dialog)
        else:
            delete_input.error_text = "Digite DELETAR corretamente."
            delete_input.update()

    delete_input = ft.TextField(label="Digite DELETAR", color="red", border_color="red")

    delete_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("⚠ Excluir Personagem"),
        content=ft.Column([
            ft.Text("Essa ação não pode ser desfeita!"),
            ft.Text("Para confirmar, digite DELETAR abaixo:"),
            delete_input
        ], tight=True, width=300),
        actions=[
            ft.TextButton("Cancelar", on_click=lambda e: page.close(delete_dialog)),
            ft.ElevatedButton("Apagar Definitivamente", on_click=confirm_delete_click, bgcolor="red", color="white"),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    def request_delete(e, idx):
        pending_delete_idx[0] = idx
        delete_input.value = ""
        delete_input.error_text = None
        page.open(delete_dialog)

    # --- Funções do Motor de Dados ---

    def run_action(e, formula, char_idx):
        if not formula: return
        context = app.get_context(char_idx)
        total, detalhes = app.engine.parse_and_roll(formula, context)

        add_log(f"🎲 Rolou: {formula}", color="cyan")
        add_log(f"➤ Detalhes: {detalhes}", color="grey")
        add_log(f"★ RESULTADO: {total}", color="green" if total > 0 else "red")
        add_log("-" * 30)

    # --- Construção da Ficha ---

    def build_character_view(char_idx):
        char = app.data["characters"][char_idx]

        name_field = ft.TextField(label="Nome do Personagem", value=char["name"], expand=True, text_size=20,
                                  on_change=lambda e: update_char_name(e, char_idx))

        segments_col = ft.Column()

        for seg_idx, seg in enumerate(char["segments"]):
            fields_col = ft.Column()

            for field_idx, field in enumerate(seg["fields"]):
                field_container = ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

                if field["type"] == "Texto":
                    inp = ft.TextField(label=field["name"], value=field["value"], expand=True, multiline=True,
                                       on_change=lambda e, s=seg_idx, f=field_idx: update_field_val(e, char_idx, s, f))
                    field_container.controls.append(inp)

                elif field["type"] == "Atributo":
                    inp_name = ft.TextField(value=field["name"], label="Variável", width=120,
                                            on_change=lambda e, s=seg_idx, f=field_idx: update_field_name(e, char_idx,
                                                                                                          s, f))
                    inp_val = ft.TextField(value=str(field["value"]), label="Valor", width=80,
                                           keyboard_type=ft.KeyboardType.NUMBER,
                                           on_change=lambda e, s=seg_idx, f=field_idx: update_field_val(e, char_idx, s,
                                                                                                        f))
                    field_container.controls.extend([inp_name, inp_val])

                elif field["type"] == "Ação":
                    inp_name = ft.TextField(value=field["name"], label="Ação", expand=True,
                                            on_change=lambda e, s=seg_idx, f=field_idx: update_field_name(e, char_idx,
                                                                                                          s, f))
                    inp_roll = ft.TextField(value=field["value"], label="Fórmula", expand=True,
                                            on_change=lambda e, s=seg_idx, f=field_idx: update_field_val(e, char_idx, s,
                                                                                                         f))

                    btn_roll = ft.IconButton(
                        icon=ft.Icons.CASINO,
                        icon_color="pink",
                        tooltip="Rolar Dados",
                        on_click=lambda e, f=field["value"], c=char_idx: run_action(e, inp_roll.value, c)
                    )
                    field_container.controls.extend([inp_name, inp_roll, btn_roll])

                btn_del_field = ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_size=16, tooltip="Remover Campo",
                                              on_click=lambda e, s=seg_idx, f=field_idx: delete_field(e, char_idx, s,
                                                                                                      f))
                field_container.controls.append(btn_del_field)
                fields_col.controls.append(field_container)

            add_btns = ft.Row([
                ft.ElevatedButton("+ Texto", on_click=lambda e, s=seg_idx: add_field(char_idx, s, "Texto")),
                ft.ElevatedButton("+ Atributo", on_click=lambda e, s=seg_idx: add_field(char_idx, s, "Atributo")),
                ft.ElevatedButton("+ Ação", on_click=lambda e, s=seg_idx: add_field(char_idx, s, "Ação")),
                ft.IconButton(ft.Icons.DELETE_FOREVER, icon_color="red", tooltip="Apagar Segmento",
                              on_click=lambda e, s=seg_idx: delete_segment(char_idx, s))
            ])

            # --- MODIFICAÇÃO AQUI: Título do Segmento Editável ---
            segment_title_input = ft.TextField(
                value=seg["name"],
                text_style=ft.TextStyle(weight=ft.FontWeight.BOLD),
                label="Título do Segmento",
                border=ft.InputBorder.UNDERLINE,
                on_change=lambda e, s=seg_idx: update_segment_name(e, char_idx, s),
                expand=True
            )

            segments_col.controls.append(
                ft.ExpansionTile(
                    title=segment_title_input,
                    controls=[fields_col, add_btns, ft.Divider()],
                    initially_expanded=True,
                    maintain_state=True
                )
            )

        btn_new_seg = ft.ElevatedButton("Novo Segmento", on_click=lambda e: add_segment(char_idx))

        return ft.Column([name_field, segments_col, btn_new_seg])

    # --- Atualização de Views e Dados ---

    def update_view():
        char_list.controls.clear()

        for idx, char in enumerate(app.data["characters"]):
            btn = ft.ListTile(
                title=ft.Text(char["name"]),
                leading=ft.Icon(ft.Icons.PERSON),
                trailing=ft.IconButton(
                    ft.Icons.DELETE_FOREVER,
                    icon_color="red",
                    tooltip="Excluir Personagem",
                    on_click=lambda e, i=idx: request_delete(e, i)
                ),
                on_click=lambda e, i=idx: select_char(i),
                selected=(idx == app.current_char_index)
            )
            char_list.controls.append(btn)

        btn_add = ft.ListTile(title=ft.Text("Criar Novo Personagem +"), on_click=create_char)
        char_list.controls.append(btn_add)

        main_area.content = ft.Text("Selecione um personagem para editar")
        if app.current_char_index is not None and app.current_char_index < len(app.data["characters"]):
            main_area.content = build_character_view(app.current_char_index)

        page.update()

    def select_char(idx):
        app.current_char_index = idx
        update_view()

    def create_char(e):
        app.data["characters"].append({"name": "Novo Heroi", "segments": []})
        app.save_data()
        select_char(len(app.data["characters"]) - 1)

    def update_char_name(e, idx):
        app.data["characters"][idx]["name"] = e.control.value
        app.save_data()

    def add_segment(char_idx):
        app.data["characters"][char_idx]["segments"].append({"name": "Novo Segmento", "fields": []})
        app.save_data()
        update_view()

    # --- NOVA FUNÇÃO: Atualizar Nome do Segmento ---
    def update_segment_name(e, char_idx, seg_idx):
        app.data["characters"][char_idx]["segments"][seg_idx]["name"] = e.control.value
        app.save_data()
        # Não chamamos update_view aqui para não perder o foco do teclado

    def delete_segment(char_idx, seg_idx):
        app.data["characters"][char_idx]["segments"].pop(seg_idx)
        app.save_data()
        update_view()

    def add_field(char_idx, seg_idx, type_):
        default_val = ""
        name = "Novo Campo"
        if type_ == "Atributo":
            default_val = 0
            name = "att"
        if type_ == "Ação":
            default_val = "1d20"
            name = "Atacar"

        new_field = {"type": type_, "name": name, "value": default_val}
        app.data["characters"][char_idx]["segments"][seg_idx]["fields"].append(new_field)
        app.save_data()
        update_view()

    def update_field_val(e, char_idx, seg_idx, field_idx):
        app.data["characters"][char_idx]["segments"][seg_idx]["fields"][field_idx]["value"] = e.control.value
        app.save_data()

    def update_field_name(e, char_idx, seg_idx, field_idx):
        app.data["characters"][char_idx]["segments"][seg_idx]["fields"][field_idx]["name"] = e.control.value
        app.save_data()

    def delete_field(e, char_idx, seg_idx, field_idx):
        app.data["characters"][char_idx]["segments"][seg_idx]["fields"].pop(field_idx)
        app.save_data()
        update_view()

    # --- Layout Principal ---

    char_list = ft.ListView(width=250, spacing=10)
    main_area = ft.Container(expand=True, padding=20)

    layout = ft.Row([
        ft.Column([
            ft.Text("Personagens", size=20, weight="bold"),
            char_list,
            ft.Divider(),
            ft.Text("Log Rolagens:"),
            log_view
        ], width=300),
        ft.VerticalDivider(),
        main_area
    ], expand=True)

    page.add(layout)
    update_view()


ft.app(target=main)