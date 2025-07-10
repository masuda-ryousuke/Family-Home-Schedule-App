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
            "item": None, # ドラッグ中のCanvasアイテムID
            "mode": None,  # "move", "resize_left", "resize_right"
            "start_x": 0, # ドラッグ開始時のX座標
            "original_schedule": None, # ドラッグ開始時の元のスケジュール (start, end)
            "member_name": None, # ドラッグ中のメンバー名
            "original_schedule_tuple_index": None, # 元のスケジュールリストでのインデックス
            "original_item_coords": None # ドラッグ開始時のアイテムの座標
        }

        # ウィンドウのリサイズイベントをバインド
        self.bind("<Configure>", self.on_resize)

    def on_resize(self, event):
        """
        Canvasのサイズが変更されたときに呼び出される。
        チャートを再描画して新しいサイズに合わせる。
        """
        # Canvasのサイズが極端に小さい場合（初期化時など）は無視
        if event.width > 1 and event.height > 1:
            self.update_gantt_chart()

    def get_chart_params(self):
        """
        チャート描画に必要な動的なパラメータ（時間あたりの幅など）を計算して返す。
        """
        current_chart_width = self.winfo_width()
        current_chart_height = self.winfo_height()

        # 左右のマージンを考慮した、チャート描画に利用可能な幅
        available_chart_drawing_width = current_chart_width - self.MARGIN_LEFT - self.RIGHT_MARGIN
        
        # 1時間あたりの最小ピクセル幅を保証
        if available_chart_drawing_width < 24 * 10: # 1時間あたり最低10pxを確保
            available_chart_drawing_width = 24 * 10 
        
        # 1時間あたりのピクセル幅を計算
        dynamic_hour_width = available_chart_drawing_width / 24 

        chart_start_x = self.MARGIN_LEFT
        chart_end_x = chart_start_x + 24 * dynamic_hour_width

        # メンバー数に応じたチャート全体の高さ計算（ここでは固定行高）
        # 必要に応じて、スクロールバーの導入や行高の動的調整を検討
        num_members = len(self.data_manager.family_members)
        min_chart_height_needed = self.MARGIN_TOP + (num_members + 1) * self.DYNAMIC_ROW_HEIGHT
        
        # Canvasの高さが足りない場合、描画がはみ出す可能性を許容
        if min_chart_height_needed > current_chart_height:
            pass 

        return {
            "hour_width": dynamic_hour_width,
            "row_height": self.DYNAMIC_ROW_HEIGHT,
            "chart_start_x": chart_start_x,
            "chart_end_x": chart_end_x,
            "chart_height": current_chart_height # Canvasの全高
        }


    def update_gantt_chart(self):
        """
        Canvas上のガントチャートを全てクリアし、現在のデータに基づいて再描画する。
        """
        self.delete("all") # Canvas上の全ての描画を削除

        params = self.get_chart_params()
        HOUR_WIDTH = params["hour_width"]
        ROW_HEIGHT = params["row_height"]
        CHART_START_X = params["chart_start_x"]
        CHART_END_X = params["chart_end_x"]
        
        # Canvasの幅や高さがまだ確定していない場合（初期起動時など）は再試行
        if self.winfo_width() < 10 or self.winfo_height() < 10:
            self.after(100, self.update_gantt_chart)
            return

        family_members = self.data_manager.family_members # DataManagerから最新のデータを取得

        if not family_members:
            self.create_text(
                self.winfo_width() / 2, self.winfo_height() / 2,
                text="まだ誰も登録されていません。", fill="gray", font=("Arial", 12),
                tags="info_text"
            )
            return

        # 時間軸の描画 (ヘッダー: 0時から24時まで)
        for h in range(25): 
            x_pos = CHART_START_X + h * HOUR_WIDTH
            if h % 2 == 0: # 偶数時間ごとにラベルを表示
                self.create_text(x_pos, self.MARGIN_TOP - 15, text=f"{h:02d}", anchor="n", font=("Arial", 8))
            # 縦のグリッド線
            self.create_line(x_pos, self.MARGIN_TOP, x_pos, self.MARGIN_TOP + (len(family_members) + 1) * ROW_HEIGHT, fill="lightgray")
        
        # 上の横線
        self.create_line(CHART_START_X, self.MARGIN_TOP, CHART_END_X, self.MARGIN_TOP, fill="black")

        # 各メンバーのスケジュールを描画
        y_offset = self.MARGIN_TOP
        for i, (name, member_data) in enumerate(family_members.items()):
            y_offset = self.MARGIN_TOP + (i + 1) * ROW_HEIGHT

            # メンバー名ラベル
            self.create_text(self.MARGIN_LEFT - 5, y_offset + ROW_HEIGHT / 2,
                                     text=name, anchor="e", font=("Arial", 10, "bold"))

            member_schedules = member_data['schedules']
            member_color = member_data['color']

            for j, (start, end) in enumerate(member_schedules):
                x1 = CHART_START_X + start * HOUR_WIDTH
                x2 = CHART_START_X + end * HOUR_WIDTH
                y1 = y_offset + 5
                y2 = y_offset + ROW_HEIGHT - 5
                
                # スケジュールバーとテキストにタグを付与
                # タグ形式: "schedule_bar_<メンバー名>_<開始時>_<終了時>_<元の配列インデックス>"
                bar_tag = f"schedule_bar_{name}_{start}_{end}_{j}" 
                text_tag = f"schedule_text_{name}_{start}_{end}_{j}"

                # レクタングルとテキストは同じタグセットを持つようにする
                self.create_rectangle(x1, y1, x2, y2, fill=member_color, outline="steelblue", width=1, tags=(bar_tag, text_tag, name))
                self.create_text((x1 + x2) / 2, (y1 + y2) / 2, text=f"{start}-{end}", fill="black", font=("Arial", 8), tags=(bar_tag, text_tag, name))

                # ドラッグイベントのバインド
                self.tag_bind(bar_tag, "<Button-1>", self.start_drag)
                self.tag_bind(bar_tag, "<B1-Motion>", self.drag_motion)
                self.tag_bind(bar_tag, "<ButtonRelease-1>", self.end_drag)
                
                # テキストにもドラッグイベントをバインド（バーと一体で操作できるように）
                self.tag_bind(text_tag, "<Button-1>", self.start_drag)
                self.tag_bind(text_tag, "<B1-Motion>", self.drag_motion)
                self.tag_bind(text_tag, "<ButtonRelease-1>", self.end_drag)
                
                # 右クリックイベントのバインド
                self.tag_bind(bar_tag, "<Button-3>", self.show_context_menu) # 右クリック
                self.tag_bind(text_tag, "<Button-3>", self.show_context_menu) # 右クリック
            
            # 各メンバーの行の区切り線
            self.create_line(CHART_START_X, y_offset + ROW_HEIGHT, CHART_END_X, y_offset + ROW_HEIGHT, fill="lightgray", dash=(2,2))


    def start_drag(self, event):
        """
        ドラッグ操作の開始時に呼び出される。
        ドラッグ中のアイテム、モード（移動/リサイズ）、開始位置などを設定する。
        """
        item = self.find_closest(event.x, event.y)[0] # クリックされた位置に最も近いアイテム
        tags = self.gettags(item) # アイテムに付与されたタグを取得
        
        # スケジュールバーまたはテキストアイテムに紐付けられたタグを探す
        found_bar_tag = None
        for tag in tags:
            if tag.startswith("schedule_bar_"):
                found_bar_tag = tag
                break
        
        if found_bar_tag:
            self.drag_data["item"] = item
            self.drag_data["start_x"] = event.x
            self.drag_data["original_item_coords"] = self.coords(item)

            parts = found_bar_tag.split('_')
            try:
                self.drag_data["member_name"] = parts[2]
                self.drag_data["original_schedule"] = (int(parts[3]), int(parts[4]))
                self.drag_data["original_schedule_tuple_index"] = int(parts[5]) # 元のインデックスも保存
                
                item_x1, _, item_x2, _ = self.drag_data["original_item_coords"]
                
                # クリック位置がリサイズハンドル範囲内か判定
                if abs(event.x - item_x1) < self.RESIZE_HANDLE_WIDTH:
                    self.drag_data["mode"] = "resize_left"
                    self.config(cursor="sb_h_double_arrow") # カーソルを変更
                elif abs(event.x - item_x2) < self.RESIZE_HANDLE_WIDTH:
                    self.drag_data["mode"] = "resize_right"
                    self.config(cursor="sb_h_double_arrow") # カーソルを変更
                else:
                    self.drag_data["mode"] = "move"
                    self.config(cursor="hand2") # カーソルを変更
            except (ValueError, IndexError):
                # タグの解析に失敗した場合
                self.drag_data["item"] = None
                self.config(cursor="")
        else:
            self.config(cursor="")


    def drag_motion(self, event):
        """
        ドラッグ中に呼び出される。
        アイテムを移動またはリサイズする。
        """
        if self.drag_data["item"] and self.drag_data["mode"]:
            dx = event.x - self.drag_data["start_x"]
            current_coords = list(self.coords(self.drag_data["item"]))
            
            params = self.get_chart_params()
            HOUR_WIDTH = params["hour_width"]
            CHART_START_X = params["chart_start_x"]
            CHART_END_X = params["chart_end_x"]

            if self.drag_data["mode"] == "move":
                # バーとテキストの両方を移動させる
                self.move(self.drag_data["item"], dx, 0)
                
                # 関連するテキストアイテムも移動
                tags = self.gettags(self.drag_data["item"])
                text_tag = None
                for tag in tags:
                    if tag.startswith("schedule_text_"):
                        text_tag = tag
                        break
                if text_tag:
                    self.move(text_tag, dx, 0)

            elif self.drag_data["mode"] == "resize_left":
                new_x1 = max(CHART_START_X, current_coords[0] + dx)
                # 最小幅は1時間分 (HOUR_WIDTH)
                new_x1 = min(new_x1, current_coords[2] - HOUR_WIDTH)

                self.coords(self.drag_data["item"], new_x1, current_coords[1], current_coords[2], current_coords[3])
                self.update_text_pos_and_content(self.drag_data["item"]) # テキストも更新

            elif self.drag_data["mode"] == "resize_right":
                new_x2 = min(CHART_END_X, current_coords[2] + dx)
                # 最小幅は1時間分 (HOUR_WIDTH)
                new_x2 = max(new_x2, current_coords[0] + HOUR_WIDTH)

                self.coords(self.drag_data["item"], current_coords[0], current_coords[1], new_x2, current_coords[3])
                self.update_text_pos_and_content(self.drag_data["item"]) # テキストも更新

            self.drag_data["start_x"] = event.x # 次の移動のための開始点を更新

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
            CHART_END_X = params["chart_end_x"] # クランプ範囲のため追加

            current_start_px = max(CHART_START_X, min(CHART_END_X, x1))
            current_end_px = max(CHART_START_X, min(CHART_END_X, x2))

            current_start_hour = (current_start_px - CHART_START_X) / HOUR_WIDTH
            current_end_hour = (current_end_px - CHART_START_X) / HOUR_WIDTH
            
            # 最小1時間の幅を維持
            if current_end_hour - current_start_hour < 1.0:
                if self.drag_data["mode"] == "resize_left":
                    current_start_hour = current_end_hour - 1.0
                elif self.drag_data["mode"] == "resize_right":
                    current_end_hour = current_start_hour + 1.0
                else: # moveの場合
                    # 移動中に幅が1時間を下回る場合、開始・終了を調整
                    if current_start_hour > current_end_hour - 1.0:
                        current_end_hour = current_start_hour + 1.0

            self.itemconfig(text_tag, text=f"{current_start_hour:.1f}-{current_end_hour:.1f}")
            self.coords(text_tag, (x1 + x2) / 2, (y1 + y2) / 2)


    def end_drag(self, event):
        """
        ドラッグ操作の終了時に呼び出される。
        新しいスケジュール時間を確定し、DataManagerを更新する。
        """
        if self.drag_data["item"] and self.drag_data["mode"]:
            coords = self.coords(self.drag_data["item"])
            
            params = self.get_chart_params()
            HOUR_WIDTH = params["hour_width"]
            CHART_START_X = params["chart_start_x"]
            CHART_END_X = params["chart_end_x"]

            # ピクセル座標を時間に変換（最も近い整数に丸める）
            new_start_hour = int(round((coords[0] - CHART_START_X) / HOUR_WIDTH))
            new_end_hour = int(round((coords[2] - CHART_START_X) / HOUR_WIDTH))

            # 時間範囲を0-24にクランプ
            new_start_hour = max(0, new_start_hour)
            new_end_hour = min(24, new_end_hour)
            
            # 開始時間 >= 終了時間の場合の調整（最小1時間幅を保証）
            if new_start_hour >= new_end_hour:
                if self.drag_data["mode"] == "resize_left":
                    new_start_hour = new_end_hour - 1
                else: # move or resize_right
                    new_end_hour = new_start_hour + 1
                
                # 再度クランプ
                new_start_hour = max(0, new_start_hour)
                new_end_hour = min(24, new_end_hour)

            # 変更がなければDataManagerの更新は行わない（無駄な保存・再描画を避ける）
            if (new_start_hour, new_end_hour) == self.drag_data["original_schedule"]:
                print("Schedule not changed, no update needed.")
                self.update_gantt_chart() # 変更がなければ再描画で元に戻す（.1f表示を整数に戻すため）
            else:
                # DataManagerを介してスケジュールを更新
                success, message = self.data_manager.update_schedule(
                    self.drag_data["member_name"], 
                    self.drag_data["original_schedule"], 
                    self.drag_data["original_schedule_tuple_index"], 
                    (new_start_hour, new_end_hour)
                )
                if not success:
                    messagebox.showerror("エラー", message, parent=self)
                # DataManagerのupdate_scheduleメソッドがsave_dataとupdate_gantt_chartを呼び出すため、ここでは不要

            # ドラッグ状態をリセット
            self.drag_data = { 
                "item": None, "mode": None, "start_x": 0, 
                "original_schedule": None, "member_name": None, 
                "original_schedule_tuple_index": None, "original_item_coords": None
            }
            self.config(cursor="") # カーソルをデフォルトに戻す


    def show_context_menu(self, event):
        """
        右クリック時にコンテキストメニューを表示する。
        「スケジュールを編集」と「このスケジュールを削除」のオプションを提供する。
        """
        item = self.find_closest(event.x, event.y)[0] # クリックされたアイテム
        tags = self.gettags(item) # アイテムに付与されたタグ

        found_bar_tag = None
        for tag in tags:
            if tag.startswith("schedule_bar_"):
                found_bar_tag = tag
                break
        
        if found_bar_tag:
            # タグからスケジュール情報を抽出
            parts = found_bar_tag.split('_')
            try:
                member_name = parts[2]
                start_hour = int(parts[3])
                end_hour = int(parts[4])
                original_index = int(parts[5])
                
                context_menu = tk.Menu(self, tearoff=0) # コンテキストメニューを作成
                
                # 「スケジュールを編集」オプション
                context_menu.add_command(
                    label=f"スケジュールを編集 ({start_hour}-{end_hour})",
                    command=lambda: self.edit_schedule_dialog(
                        member_name, (start_hour, end_hour), original_index
                    )
                )
                
                # 「このスケジュールを削除」オプション
                context_menu.add_command(
                    label=f"このスケジュールを削除 ({start_hour}-{end_hour})",
                    command=lambda: self.delete_schedule_from_chart(
                        member_name, (start_hour, end_hour), original_index
                    )
                )
                context_menu.post(event.x_root, event.y_root) # マウスの現在位置にメニューを表示

            except (ValueError, IndexError) as e:
                print(f"Error parsing schedule tag: {e}")
                pass # タグ解析エラーの場合はメニューを表示しない

    def edit_schedule_dialog(self, member_name, old_schedule, original_index):
        """
        スケジュール編集用のダイアログを表示し、ユーザーからの入力を受け付ける。
        """
        # ダイアログウィンドウの作成
        dialog = tk.Toplevel(self) # 親をChartCanvasのインスタンスにする
        dialog.title(f"{member_name} のスケジュールを編集")
        dialog.transient(self.master) # 親ウィンドウ（ScheduleAppのルート）のアイコン表示
        dialog.grab_set() # モーダルにする (親ウィンドウを操作できないようにする)
        dialog.focus_set() # フォーカスをダイアログに設定

        # ダイアログ内のフレーム
        dialog_frame = ttk.Frame(dialog, padding="15")
        dialog_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(dialog_frame, text=f"メンバー: {member_name}").grid(row=0, column=0, columnspan=2, pady=5)
        
        ttk.Label(dialog_frame, text="開始時間 (0-23):").grid(row=1, column=0, sticky="w", pady=2)
        start_entry = ttk.Entry(dialog_frame, width=5)
        start_entry.insert(0, str(old_schedule[0])) # 現在の開始時間を表示
        start_entry.grid(row=1, column=1, sticky="ew", pady=2)

        ttk.Label(dialog_frame, text="終了時間 (1-24):").grid(row=2, column=0, sticky="w", pady=2)
        end_entry = ttk.Entry(dialog_frame, width=5)
        end_entry.insert(0, str(old_schedule[1])) # 現在の終了時間を表示
        end_entry.grid(row=2, column=1, sticky="ew", pady=2)

        def on_ok():
            """「変更」ボタンが押されたときの処理。入力値を検証し、スケジュールを更新する。"""
            try:
                new_start = int(start_entry.get())
                new_end = int(end_entry.get())

                if not (0 <= new_start <= 23 and 0 <= new_end <= 24 and new_start < new_end):
                    messagebox.showwarning("入力エラー", "時間は0から24の整数で、開始時間は終了時間より小さくしてください。", parent=dialog)
                    return
                
                new_schedule_tuple = (new_start, new_end)

                if new_schedule_tuple == old_schedule:
                    messagebox.showinfo("情報", "スケジュールは変更されていません。", parent=dialog)
                    dialog.destroy()
                    return

                # DataManagerを介してスケジュールを更新
                success, message = self.data_manager.update_schedule(member_name, old_schedule, original_index, new_schedule_tuple)
                if success:
                    dialog.destroy() # 成功したらダイアログを閉じる
                else:
                    messagebox.showerror("エラー", message, parent=dialog)
                
            except ValueError:
                messagebox.showwarning("入力エラー", "開始時間と終了時間は数字で入力してください。", parent=dialog)
            except Exception as e:
                messagebox.showerror("エラー", f"スケジュールの更新中にエラーが発生しました: {e}", parent=dialog)

        def on_cancel():
            """「キャンセル」ボタンが押されたときの処理。ダイアログを閉じる。"""
            dialog.destroy()

        button_frame = ttk.Frame(dialog_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=10)

        ok_button = ttk.Button(button_frame, text="変更", command=on_ok)
        ok_button.pack(side=tk.LEFT, padx=5)

        cancel_button = ttk.Button(button_frame, text="キャンセル", command=on_cancel)
        cancel_button.pack(side=tk.LEFT, padx=5)

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
                messagebox.showinfo("削除完了", message, parent=self)
            else:
                messagebox.showerror("エラー", message, parent=self)
            # DataManagerのdelete_scheduleメソッドがsave_dataとupdate_gantt_chartを呼び出すため、ここでは不要
