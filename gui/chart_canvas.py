# gui/chart_canvas.py
import tkinter as tk
from tkinter import ttk, messagebox
import math # round()のために必要

class ChartCanvas(tk.Canvas):
    """
    家族在宅スケジュールをガントチャート形式で表示・操作するCanvasウィジェット。
    ドラッグ＆ドロップによるスケジュール変更、右クリックメニューによる編集・削除機能を持つ。
    """
    # 定数 (クラス変数として定義)
    MARGIN_LEFT = 80
    MARGIN_TOP = 30
    RESIZE_HANDLE_WIDTH = 10
    RIGHT_MARGIN = 20 # 24時のラベルを表示するための右マージン
    DYNAMIC_ROW_HEIGHT = 40 # 各メンバーの行の高さ

    def __init__(self, master, data_manager, update_callback=None, **kwargs):
        """
        ChartCanvasのコンストラクタ。
        :param master: 親ウィジェット
        :param data_manager: DataManagerクラスのインスタンス（データ操作用）
        :param update_callback: チャート更新後に親に通知するためのコールバック関数
        :param kwargs: tk.Canvasに渡すその他の引数
        """
        super().__init__(master, bg="white", borderwidth=1, relief="solid", **kwargs)
        self.data_manager = data_manager # DataManagerインスタンスを保持
        self.update_callback = update_callback # 親のGUIを更新するためのコールバック

        # ドラッグ操作のための状態変数（インスタンス変数として定義）
        self.drag_data = {
            "item": None,           # ドラッグ中のアイテムID
            "mode": None,           # ドラッグモード ("move", "resize_left", "resize_right")
            "start_x": 0,           # ドラッグ開始時のマウスX座標
            "start_y": 0,           # ドラッグ開始時のマウスY座標
            "x_offset": 0,          # アイテムの左端とマウスポインタの相対位置 (moveモード用)
            "original_coords": None,# ドラッグ開始時のアイテムのオリジナル座標
            "member_name": None,    # ドラッグ中のメンバー名
            "original_schedule": None, # ドラッグ開始時の元のスケジュール (start_hour, end_hour)
            "original_index": -1    # DataManager内の元のスケジュールのインデックス
        }

        # ズームレベル (1.0がデフォルト、大きいほど拡大)
        self.zoom_level = 1.0

        # イベントバインディング
        self.bind("<Button-1>", self.drag_start)       # 左クリックでドラッグ開始
        self.bind("<B1-Motion>", self.drag_motion)      # ドラッグ中
        self.bind("<ButtonRelease-1>", self.end_drag)   # ドラッグ終了
        self.bind("<Button-3>", self.show_context_menu) # 右クリックでコンテキストメニュー表示
        self.bind("<Motion>", self.on_mouse_motion) # マウス移動時にカーソルを変更

        # ウィンドウサイズ変更イベントのバインド
        self.bind("<Configure>", self.on_canvas_configure)

    def on_canvas_configure(self, event):
        """
        Canvasのサイズが変更されたときにガントチャートを再描画する。
        """
        self.update_gantt_chart()

    def get_chart_params(self):
        """
        チャート描画に必要な動的なパラメータを計算して返す。
        """
        canvas_width = self.winfo_width()
        canvas_height = self.winfo_height()

        CHART_START_X = self.MARGIN_LEFT
        CHART_END_X = canvas_width - self.RIGHT_MARGIN
        CHART_WIDTH = CHART_END_X - CHART_START_X
        
        # 1時間あたりのピクセル数を計算 (ズームレベルを適用)
        HOUR_WIDTH = (CHART_WIDTH / 24) * self.zoom_level
        
        return {
            "canvas_width": canvas_width,
            "canvas_height": canvas_height,
            "chart_start_x": CHART_START_X,
            "chart_end_x": CHART_END_X,
            "chart_width": CHART_WIDTH,
            "hour_width": HOUR_WIDTH
        }

    def update_gantt_chart(self):
        """
        現在のデータに基づいてガントチャートを再描画する。
        """
        self.delete("all") # 既存の描画をすべてクリア

        params = self.get_chart_params()
        canvas_width = params["canvas_width"]
        canvas_height = params["canvas_height"]
        CHART_START_X = params["chart_start_x"]
        CHART_END_X = params["chart_end_x"]
        HOUR_WIDTH = params["hour_width"]

        # 時間軸の描画
        for i in range(25): # 0時から24時まで
            x = CHART_START_X + i * HOUR_WIDTH
            self.create_line(x, self.MARGIN_TOP, x, canvas_height, fill="lightgray")
            if i < 24: # 24時はラインのみ、ラベルは不要
                self.create_text(x, self.MARGIN_TOP - 10, text=f"{i}", anchor="n", font=("Arial", 9))
        
        # 0時から24時の範囲を示す上部の線
        self.create_line(CHART_START_X, self.MARGIN_TOP, CHART_END_X, self.MARGIN_TOP, fill="black", width=1)
        
        # 各メンバーのスケジュールを描画
        y_offset = self.MARGIN_TOP # 上部の時間軸の高さから開始
        member_names = list(self.data_manager.family_members.keys())
        
        for i, name in enumerate(member_names):
            y1 = y_offset + i * self.DYNAMIC_ROW_HEIGHT + 5 # 行の上部
            y2 = y1 + self.DYNAMIC_ROW_HEIGHT - 10 # バーの高さ (少しマージンを取る)

            # メンバー名の表示
            self.create_text(self.MARGIN_LEFT - 5, (y1 + y2) / 2,
                             text=name, anchor="e", font=("Arial", 10, "bold"))
            
            # 各メンバーのスケジュールバーを描画
            member_data = self.data_manager.family_members[name]
            schedules = member_data['schedules']
            color = member_data['color']

            for schedule_index, (start_hour, end_hour) in enumerate(schedules):
                x1 = CHART_START_X + start_hour * HOUR_WIDTH
                x2 = CHART_START_X + end_hour * HOUR_WIDTH
                
                # バーがチャート範囲外にはみ出さないようにクリップ
                x1 = max(CHART_START_X, x1)
                x2 = min(CHART_END_X, x2)

                # バーの描画
                item_id = self.create_rectangle(x1, y1, x2, y2,
                                                fill=color, outline="gray",
                                                tags=(f"schedule_bar_{name}_{schedule_index}", f"member_{name}", f"schedule_{schedule_index}"))
                
                # テキストの描画
                text_id = self.create_text((x1 + x2) / 2, (y1 + y2) / 2,
                                           text=f"{start_hour:.1f}-{end_hour:.1f}", # 初期表示は.1fで統一
                                           fill="black", font=("Arial", 8, "bold"),
                                           tags=(f"schedule_text_{name}_{schedule_index}", f"member_{name}", f"schedule_text_{schedule_index}"))
                
                # バーとテキストを関連付けるために、テキストアイテムにバーのタグを付与
                self.addtag_withtag(f"schedule_bar_{name}_{schedule_index}", text_id)

                # ★修正箇所1: リサイズハンドルの描画ロジックを改善
                # バーの幅が十分にある場合のみハンドルを描画
                if (x2 - x1) >= (self.RESIZE_HANDLE_WIDTH * 2): 
                    # 左ハンドル
                    self.create_rectangle(x1, y1, x1 + self.RESIZE_HANDLE_WIDTH, y2,
                                        fill="blue", outline="darkblue",
                                        tags=(f"resize_handle_left_{item_id}", f"member_{name}", f"schedule_handle_left_{schedule_index}"))
                    # 右ハンドル
                    self.create_rectangle(x2 - self.RESIZE_HANDLE_WIDTH, y1, x2, y2,
                                        fill="blue", outline="darkblue",
                                        tags=(f"resize_handle_right_{item_id}", f"member_{name}", f"schedule_handle_right_{schedule_index}"))
            
            # メンバーごとの水平線
            self.create_line(CHART_START_X, y2 + 5, CHART_END_X, y2 + 5, fill="lightgray", dash=(2, 2))

        # 最下部の水平線 (最後のメンバーの行の下)
        final_y = self.MARGIN_TOP + len(member_names) * self.DYNAMIC_ROW_HEIGHT + 5
        if member_names: # メンバーがいる場合のみ描画
             self.create_line(CHART_START_X, final_y, CHART_END_X, final_y, fill="black", width=1)


        # コールバックがあれば呼び出す (例: 親ウィンドウのリストボックス更新)
        if self.update_callback:
            self.update_callback()

    def on_mouse_motion(self, event):
        """
        マウスがCanvas上を移動したときにカーソルの形状を変更する。
        """
        params = self.get_chart_params()
        CHART_START_X = params["chart_start_x"]
        CHART_END_X = params["chart_end_x"]
        # HOUR_WIDTH = params["hour_width"] # 未使用

        # チャート範囲外ではデフォルトカーソル
        if not (CHART_START_X <= event.x <= CHART_END_X):
            self.config(cursor="") 
            return

        # マウス下のアイテムを特定
        item_ids = self.find_overlapping(event.x - 1, event.y - 1, event.x + 1, event.y + 1)
        
        current_cursor = ""
        for item_id in item_ids:
            tags = self.gettags(item_id)
            if f"resize_handle_left_{item_id}" in tags or f"resize_handle_right_{item_id}" in tags:
                current_cursor = "sb_h_double_arrow"
                break # ハンドルが見つかったら最優先
            elif any(tag.startswith("schedule_bar_") for tag in tags):
                current_cursor = "fleur" # バー本体

        self.config(cursor=current_cursor)


    def drag_start(self, event):
        """
        ドラッグ操作の開始を処理する。
        """
        item = self.find_closest(event.x, event.y)
        if not item: return

        # クリックされたアイテムのタグを取得
        tags = self.gettags(item)
        
        member_name = None
        schedule_index = -1
        
        # ★修正箇所2: クリックされたアイテムがハンドルかバー本体かを正確に判定
        is_handle_left = False
        is_handle_right = False
        is_bar = False

        for tag in tags:
            if tag.startswith("member_"):
                member_name = tag.split("_")[1]
            if tag.startswith("schedule_bar_"):
                is_bar = True
                try:
                    schedule_index = int(tag.split("_")[-1])
                except ValueError:
                    pass
            elif tag.startswith("resize_handle_left_"):
                is_handle_left = True
                # ハンドルがクリックされた場合、そのハンドルが関連付けられているバーのIDを取得
                try:
                    bar_item_id = int(tag.split("_")[3])
                    # バーのタグからmember_nameとschedule_indexを再取得
                    bar_tags = self.gettags(bar_item_id)
                    for bar_tag in bar_tags:
                        if bar_tag.startswith("member_"):
                            member_name = bar_tag.split("_")[1]
                        if bar_tag.startswith("schedule_"):
                            schedule_index = int(bar_tag.split("_")[-1])
                    item = bar_item_id # ドラッグ対象をバー自体に設定
                except (ValueError, IndexError):
                    return # 不正なタグ形式の場合は処理しない
            elif tag.startswith("resize_handle_right_"):
                is_handle_right = True
                try:
                    bar_item_id = int(tag.split("_")[3])
                    bar_tags = self.gettags(bar_item_id)
                    for bar_tag in bar_tags:
                        if bar_tag.startswith("member_"):
                            member_name = bar_tag.split("_")[1]
                        if bar_tag.startswith("schedule_"):
                            schedule_index = int(bar_tag.split("_")[-1])
                    item = bar_item_id # ドラッグ対象をバー自体に設定
                except (ValueError, IndexError):
                    return # 不正なタグ形式の場合は処理しない
        
        # スケジュールバーまたはそのハンドルがクリックされた場合のみ処理
        if not (is_bar or is_handle_left or is_handle_right):
            return

        if not member_name or schedule_index == -1:
            return

        original_schedules = self.data_manager.family_members[member_name]['schedules']
        if not (0 <= schedule_index < len(original_schedules)):
            return # インデックスが範囲外の場合はエラー

        original_schedule = original_schedules[schedule_index]
        
        x1, y1, x2, y2 = self.coords(item)
        
        self.drag_data["item"] = item
        self.drag_data["start_x"] = event.x
        self.drag_data["start_y"] = event.y
        self.drag_data["x_offset"] = event.x - x1 # マウスの位置とバーの左端のオフセット (moveモード用)
        self.drag_data["original_coords"] = (x1, y1, x2, y2)
        self.drag_data["member_name"] = member_name
        self.drag_data["original_schedule"] = original_schedule
        self.drag_data["original_index"] = schedule_index # DataManagerに渡すためのインデックス

        if is_handle_left:
            self.drag_data["mode"] = "resize_left"
            self.config(cursor="sb_h_double_arrow")
        elif is_handle_right:
            self.drag_data["mode"] = "resize_right"
            self.config(cursor="sb_h_double_arrow")
        elif is_bar: # バー本体のドラッグ
            self.drag_data["mode"] = "move"
            self.config(cursor="fleur")

    def drag_motion(self, event):
        """
        ドラッグ操作中の移動を処理する。
        """
        if self.drag_data["item"] is None:
            return

        params = self.get_chart_params()
        CHART_START_X = params["chart_start_x"]
        CHART_END_X = params["chart_end_x"]
        HOUR_WIDTH = params["hour_width"]
        
        current_x1, current_y1, current_x2, current_y2 = self.coords(self.drag_data["item"])
        
        snap_interval = 1.0 # スナップ間隔 (1.0で1時間単位、0.5で30分単位など)
        min_duration_hours = 1.0 # スケジュールの最小持続時間 (1時間)

        if self.drag_data["mode"] == "move":
            # マウスの現在のX座標から、バーの新しい開始X座標を計算
            new_x1_raw = event.x - self.drag_data["x_offset"]
            
            # ピクセル座標を時間に変換し、丸める
            new_start_hour_float = (new_x1_raw - CHART_START_X) / HOUR_WIDTH
            new_start_hour_snapped = round(new_start_hour_float / snap_interval) * snap_interval
            
            # バーの長さは維持
            duration = self.drag_data["original_schedule"][1] - self.drag_data["original_schedule"][0]
            
            # 新しい開始時間に基づいて新しい終了時間を計算
            new_end_hour_snapped = new_start_hour_snapped + duration

            # 範囲制限 (0時-24時の範囲に収める)
            new_start_hour_snapped = max(0.0, new_start_hour_snapped)
            new_end_hour_snapped = new_start_hour_snapped + duration # 開始時間調整後、終了時間を再計算
            
            # 24時を超えないように調整
            if new_end_hour_snapped > 24.0:
                new_end_hour_snapped = 24.0
                new_start_hour_snapped = new_end_hour_snapped - duration
                if new_start_hour_snapped < 0.0: # 0時より小さくなる場合は0時に固定
                    new_start_hour_snapped = 0.0
                    new_end_hour_snapped = new_start_hour_snapped + duration

            # ピクセル座標に戻す
            new_x1 = CHART_START_X + new_start_hour_snapped * HOUR_WIDTH
            new_x2 = CHART_START_X + new_end_hour_snapped * HOUR_WIDTH

            # バーとテキストの両方を移動させる
            self.coords(self.drag_data["item"], new_x1, current_y1, new_x2, current_y2)
            
            # 関連するテキストアイテムも移動
            tags = self.gettags(self.drag_data["item"])
            text_tag = None
            for tag in tags:
                if tag.startswith("schedule_text_"):
                    text_tag = tag
                    break
            if text_tag:
                self.coords(text_tag, (new_x1 + new_x2) / 2, current_y1 + (self.DYNAMIC_ROW_HEIGHT / 2) - 5)
                # テキストの内容もリアルタイムで更新
                self.itemconfig(text_tag, text=f"{new_start_hour_snapped:.1f}-{new_end_hour_snapped:.1f}")


        elif self.drag_data["mode"] == "resize_left":
            # ★修正箇所3: 左端のリサイズロジックを改善
            new_x1_raw = event.x
            new_start_hour_float = (new_x1_raw - CHART_START_X) / HOUR_WIDTH
            
            new_start_hour_snapped = round(new_start_hour_float / snap_interval) * snap_interval

            # 現在の終了時間を計算
            current_end_hour = (current_x2 - CHART_START_X) / HOUR_WIDTH

            # 最小幅の制約: 新しい開始時間が現在の終了時間から最小持続時間を引いた値より大きくならないように
            if new_start_hour_snapped >= current_end_hour - min_duration_hours:
                new_start_hour_snapped = current_end_hour - min_duration_hours
            
            # 0時より小さくならないように
            new_start_hour_snapped = max(0.0, new_start_hour_snapped)

            new_x1 = CHART_START_X + new_start_hour_snapped * HOUR_WIDTH
            
            # 描画の更新
            self.coords(self.drag_data["item"], new_x1, current_y1, current_x2, current_y2)
            self.update_text_pos_and_content(self.drag_data["item"]) # テキストも更新

        elif self.drag_data["mode"] == "resize_right":
            # ★修正箇所4: 右端のリサイズロジックを改善
            new_x2_raw = event.x
            new_end_hour_float = (new_x2_raw - CHART_START_X) / HOUR_WIDTH

            new_end_hour_snapped = round(new_end_hour_float / snap_interval) * snap_interval

            # 現在の開始時間を計算
            current_start_hour = (current_x1 - CHART_START_X) / HOUR_WIDTH

            # 最小幅の制約: 新しい終了時間が現在の開始時間から最小持続時間を足した値より小さくならないように
            if new_end_hour_snapped <= current_start_hour + min_duration_hours:
                new_end_hour_snapped = current_start_hour + min_duration_hours
            
            # 24時より大きくならないように
            new_end_hour_snapped = min(24.0, new_end_hour_snapped)
            
            new_x2 = CHART_START_X + new_end_hour_snapped * HOUR_WIDTH

            # 描画の更新
            self.coords(self.drag_data["item"], current_x1, current_y1, new_x2, current_y2)
            self.update_text_pos_and_content(self.drag_data["item"]) # テキストも更新


    def end_drag(self, event):
        """
        ドラッグ操作の終了を処理し、DataManagerを更新する。
        """
        if self.drag_data["item"] is None:
            self.config(cursor="") # カーソルをデフォルトに戻す
            return

        # 最終的なバーの座標を取得
        final_x1, final_y1, final_x2, final_y2 = self.coords(self.drag_data["item"])

        params = self.get_chart_params()
        CHART_START_X = params["chart_start_x"]
        HOUR_WIDTH = params["hour_width"]

        # ピクセル座標を時間に変換
        new_start_hour = (final_x1 - CHART_START_X) / HOUR_WIDTH
        new_end_hour = (final_x2 - CHART_START_X) / HOUR_WIDTH

        # 最終的な時間も丸める（表示と内部データの一貫性のため）
        # 丸めはここでは1時間単位で確定
        new_start_hour = round(new_start_hour)
        new_end_hour = round(new_end_hour)
        
        # 0-24時間の範囲に収める
        new_start_hour = max(0, new_start_hour)
        new_end_hour = min(24, new_end_hour)

        # 終了時間が開始時間よりも小さくならないように調整（最小1時間）
        if new_end_hour <= new_start_hour:
            new_end_hour = new_start_hour + 1
        
        # デバッグ出力
        print(f"DEBUG: Drag end. Original: {self.drag_data['original_schedule']} -> New: ({new_start_hour}, {new_end_hour})")

        # DataManagerを更新
        member_name = self.drag_data["member_name"]
        old_schedule = self.drag_data["original_schedule"]
        old_index = self.drag_data["original_index"]
        new_schedule = (new_start_hour, new_end_hour)

        if (new_start_hour, new_end_hour) == old_schedule:
            print("Schedule not changed, no update needed.")
            # 変更がなければ再描画で元に戻す（.1f表示を整数に戻すため）
        else:
            success, message = self.data_manager.update_schedule(
                member_name, old_schedule, old_index, new_schedule
            )
            if not success:
                messagebox.showerror("エラー", message, parent=self)
            
        # ドラッグ状態をリセット
        self.drag_data = {
            "item": None, "mode": None, "start_x": 0, "start_y": 0,
            "x_offset": 0, "original_coords": None, "member_name": None,
            "original_schedule": None, "original_index": -1
        }
        self.config(cursor="") # カーソルをデフォルトに戻す
        self.update_gantt_chart() # 無条件で再描画するように変更


    def show_context_menu(self, event):
        """
        右クリック時にコンテキストメニューを表示する。
        """
        item_id = self.find_closest(event.x, event.y)
        if not item_id: return

        tags = self.gettags(item_id)
        member_name = None
        schedule_index = -1
        
        for tag in tags:
            if tag.startswith("member_"):
                member_name = tag.split("_")[1]
            if tag.startswith("schedule_bar_"):
                try:
                    schedule_index = int(tag.split("_")[-1])
                except ValueError:
                    pass
        
        if member_name and schedule_index != -1:
            try:
                # DataManagerから最新のスケジュールデータを取得して確認
                schedules_for_member = self.data_manager.family_members.get(member_name, {}).get('schedules', [])
                
                if 0 <= schedule_index < len(schedules_for_member):
                    # オリジナルのスケジュールタプルをDataManagerから取得 (最新の状態)
                    original_schedule = schedules_for_member[schedule_index]

                    menu = tk.Menu(self, tearoff=0)
                    menu.add_command(label="スケジュールを編集",
                                    command=lambda: self.edit_schedule_dialog(member_name, original_schedule, schedule_index))
                    menu.add_command(label="スケジュールを削除",
                                    command=lambda: self.delete_schedule_from_chart(member_name, original_schedule, schedule_index))
                    
                    menu.post(event.x_root, event.y_root)
                else:
                    print(f"DEBUG: Context menu click: schedule_index {schedule_index} out of bounds for member {member_name}.")
            except KeyError:
                print(f"DEBUG: Context menu click: Member '{member_name}' not found in data_manager.")
            except Exception as e:
                print(f"DEBUG: Error getting schedule data for context menu: {e}")


    def update_text_pos_and_content(self, item_id):
        """
        スケジュールバーのリサイズに合わせて、その上のテキストの位置と内容を更新する。
        """
        coords = self.coords(item_id)
        if not coords: return

        x1, y1, x2, y2 = coords
        
        tags = self.gettags(item_id)
        text_tag = None
        for tag in tags:
            if tag.startswith("schedule_text_"):
                text_tag = tag
                break
        
        if text_tag:
            params = self.get_chart_params()
            HOUR_WIDTH = params["hour_width"]
            CHART_START_X = params["chart_start_x"]

            # 現在のピクセル座標から時間に変換
            current_start_hour_float = (x1 - CHART_START_X) / HOUR_WIDTH
            current_end_hour_float = (x2 - CHART_START_X) / HOUR_WIDTH
            
            # リサイズ中は、表示を小数点第一位まで更新
            self.itemconfig(text_tag, text=f"{current_start_hour_float:.1f}-{current_end_hour_float:.1f}")
            self.coords(text_tag, (x1 + x2) / 2, (y1 + y2) / 2)


    def edit_schedule_dialog(self, member_name, old_schedule, original_index):
        """
        スケジュール編集用のダイアログを表示する。
        :param member_name: スケジュールを編集するメンバーの名前
        :param old_schedule: 編集前のスケジュール (start_hour, end_hour) のタプル
        :param original_index: 元のスケジュールリストでのインデックス
        """
        dialog = tk.Toplevel(self)
        dialog.title("スケジュール編集")
        dialog.transient(self.master) # 親ウィンドウの上に表示
        dialog.grab_set() # 親ウィンドウの操作を無効化

        tk.Label(dialog, text=f"{member_name} のスケジュールを編集:").pack(pady=5)

        # 現在のスケジュールを表示
        tk.Label(dialog, text=f"現在の時間: {old_schedule[0]}時 - {old_schedule[1]}時").pack(pady=5)

        # 新しい開始時間の入力
        tk.Label(dialog, text="新しい開始時間 (0-23):").pack(pady=(10, 0))
        start_hour_entry = ttk.Entry(dialog)
        start_hour_entry.insert(0, str(int(old_schedule[0]))) # 整数として初期表示
        start_hour_entry.pack(pady=5)

        # 新しい終了時間の入力
        tk.Label(dialog, text="新しい終了時間 (1-24):").pack(pady=(10, 0))
        end_hour_entry = ttk.Entry(dialog)
        end_hour_entry.insert(0, str(int(old_schedule[1]))) # 整数として初期表示
        end_hour_entry.pack(pady=5)

        def on_ok():
            try:
                new_start = int(start_hour_entry.get())
                new_end = int(end_hour_entry.get())

                if not (0 <= new_start <= 23) or not (1 <= new_end <= 24):
                    messagebox.showwarning("入力エラー", "時間は0-23 (開始) または 1-24 (終了) の範囲で入力してください。", parent=dialog)
                    return
                if new_start >= new_end:
                    messagebox.showwarning("入力エラー", "開始時間は終了時間より前に設定してください。", parent=dialog)
                    return

                new_schedule = (new_start, new_end)
                success, message = self.data_manager.update_schedule(
                    member_name, old_schedule, original_index, new_schedule
                )
                if success:
                    self.update_gantt_chart()
                    dialog.destroy()
                else:
                    messagebox.showerror("エラー", message, parent=dialog)
                    dialog.destroy() # エラーでもダイアログを閉じる

            except ValueError:
                messagebox.showwarning("入力エラー", "開始時間と終了時間は数字で入力してください。", parent=dialog)
                dialog.destroy() # エラーでもダイアログを閉じる
            except Exception as e:
                messagebox.showerror("エラー", f"スケジュールの更新中にエラーが発生しました: {e}", parent=dialog)
                dialog.destroy() # エラーでもダイアログを閉じる

        def on_cancel():
            dialog.destroy()

        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)
        ttk.Button(button_frame, text="OK", command=on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="キャンセル", command=on_cancel).pack(side=tk.RIGHT, padx=5)

        # Enterキーでの確定、Escapeキーでのキャンセルをバインド
        dialog.bind("<Return>", lambda event: on_ok())
        dialog.bind("<Escape>", lambda event: on_cancel())

        # ダイアログの位置を親ウィンドウの中央に設定
        self.master.update_idletasks() # 親であるScheduleAppのルートウィンドウのサイズを更新
        dialog.update_idletasks() # ダイアログ自身のサイズを更新
        x = self.master.winfo_x() + (self.master.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.master.winfo_y() + (self.master.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        dialog.wait_window(dialog) # ダイアログが閉じられるまで親ウィンドウの処理を停止


    def delete_schedule_from_chart(self, member_name, schedule_to_delete, original_index):
        """
        ガントチャートからの右クリックでスケジュールを削除する。
        DataManagerを介してスケジュールを削除し、UIを更新する。
        :param member_name: スケジュールを削除するメンバーの名前
        :param schedule_to_delete: 削除するスケジュール (start_hour, end_hour) のタプル
        :param original_index: 元のスケジュールリストでのインデックス
        """
        if messagebox.askyesno("確認", f"'{member_name}' のスケジュール {schedule_to_delete[0]}時-{schedule_to_delete[1]}時 を削除しますか？", parent=self):
            success, message = self.data_manager.delete_schedule(member_name, schedule_to_delete, original_index)
            if success:
                messagebox.showinfo("成功", message, parent=self)
                self.update_gantt_chart() # チャートを再描画
            else:
                messagebox.showerror("エラー", message, parent=self)